"""Train a Semantic Ranking model using ListMLE loss.

Aligns with "Efficient LLM Scheduling by Learning to Rank" (NeurIPS 2024):
- Sentence-Transformer encodes prompt semantics → 384-dim embedding
- MLP head maps embeddings to ranking scores
- ListMLE loss (vectorized, matching paper) trains the ranking

Usage:
  python scripts/train_ltr_model.py --download-sharegpt       # download real data
  python scripts/train_ltr_model.py                            # train on ShareGPT
  python scripts/train_ltr_model.py --generate-synthetic       # synthetic test data
  python scripts/train_ltr_model.py --epochs 20 -n 32         # custom params
"""
import argparse
import json
import random
import sys
from pathlib import Path

import torch
import torch.nn as nn

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gateway.app.predictor_ml import SemanticRankingModel, _ENCODER_NAME

_SHAREGPT_URL = "https://huggingface.co/datasets/anon8231489123/ShareGPT_Vicuna_unfiltered/resolve/main/ShareGPT_V3_unfiltered_cleaned_split.json"


# ── ListMLE loss (vectorized, matching paper) ──────────────────────────────


def list_mle_loss(scores: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    """Vectorized ListMLE loss matching the paper's allRank implementation.

    1. Random shuffle for tie resolution (paper: torch.randperm)
    2. Sort by targets descending
    3. Compute log-sum-exp chain (vectorized cumsum)
    """
    n = scores.shape[0]
    if n < 2:
        return torch.tensor(0.0, requires_grad=True)

    # Random shuffle for tie resolution (paper does this)
    perm = torch.randperm(n)
    scores = scores[perm]
    targets = targets[perm]

    # Sort by targets descending
    sorted_indices = torch.argsort(targets, descending=True)
    sorted_scores = scores[sorted_indices]

    # Numerical stability: subtract max
    max_score = sorted_scores.max()
    stabilized = sorted_scores - max_score

    # Vectorized: cumsum of exp from right to left
    exp_scores = stabilized.exp()
    cumsum = torch.cumsum(exp_scores.flip(0), dim=0).flip(0)

    # ListMLE: -sum(log(cumsum + eps) - stabilized)
    loss = (torch.log(cumsum + 1e-10) - stabilized).sum()
    return loss


# ── Data loading ────────────────────────────────────────────────────────────


def download_sharegpt(output_path: str, max_samples: int = 20000) -> None:
    """Download ShareGPT dataset and extract prompt + completion token counts."""
    print(f"Downloading ShareGPT dataset...")
    try:
        from datasets import load_dataset
        ds = load_dataset(
            "anon8231489123/ShareGPT_Vicuna_unfiltered",
            data_files="ShareGPT_V3_unfiltered_cleaned_split.json",
            split="train",
        )
    except Exception:
        # Fallback: direct download
        import urllib.request
        import json as _json
        print("Using direct download fallback...")
        tmp = "sharegpt_raw.json"
        urllib.request.urlretrieve(_SHAREGPT_URL, tmp)
        with open(tmp, encoding="utf-8") as f:
            raw = _json.load(f)
        records = []
        for conv in raw[:max_samples * 2]:
            if "conversations" not in conv:
                continue
            human_msgs = [t["value"] for t in conv["conversations"] if t.get("from") == "human"]
            gpt_msgs = [t["value"] for t in conv["conversations"] if t.get("from") == "gpt"]
            if human_msgs and gpt_msgs:
                prompt = human_msgs[-1]
                completion = gpt_msgs[-1]
                # Simple token count approximation (words * 1.3)
                comp_tokens = max(1, int(len(completion.split()) * 1.3))
                records.append({
                    "prompt": prompt,
                    "completion_tokens": comp_tokens,
                })
            if len(records) >= max_samples:
                break
        with open(output_path, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"Saved {len(records)} samples → {output_path}")
        return

    records = []
    for item in ds:
        conversations = item.get("conversations", [])
        human_msgs = [t["value"] for t in conversations if t.get("from") == "human"]
        gpt_msgs = [t["value"] for t in conversations if t.get("from") == "gpt"]
        if human_msgs and gpt_msgs:
            prompt = human_msgs[-1]
            completion = gpt_msgs[-1]
            comp_tokens = max(1, int(len(completion.split()) * 1.3))
            records.append({"prompt": prompt, "completion_tokens": comp_tokens})
        if len(records) >= max_samples:
            break

    with open(output_path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"Saved {len(records)} samples → {output_path}")


def generate_synthetic(path: str, n: int = 2000) -> None:
    """Generate synthetic data with realistic prompt texts."""
    rng = random.Random(42)
    short_prompts = [
        "Hi", "What is 2+2?", "Say hello", "Yes or no?", "Tell me a joke",
        "Define algorithm in one sentence", "What's the capital of France?",
        "Translate hello to French", "Give me three colors", "1+1=?",
    ]
    long_prompts = [
        "Write a comprehensive essay on the impact of artificial intelligence on modern society, covering economic, social, and ethical implications",
        "Provide a detailed comparison of Python, JavaScript, and Go as backend programming languages, including performance benchmarks and ecosystem",
        "Explain the complete lifecycle of a web request from browser to server and back, including DNS, TCP, TLS, HTTP, and response rendering",
        "Discuss the philosophical implications of consciousness in artificial systems and what it means for the future of AI",
    ]
    medium_prompts = [
        "Explain how neural networks work in a few paragraphs",
        "Compare REST and GraphQL APIs",
        "Describe the water cycle in detail",
        "What are the pros and cons of microservices?",
        "Summarize containerization in 200 words",
    ]
    records = []
    for i in range(n):
        r = rng.random()
        if r < 0.3:
            prompt = rng.choice(short_prompts)
            tokens = rng.randint(5, 50)
        elif r < 0.7:
            prompt = rng.choice(medium_prompts)
            tokens = rng.randint(50, 250)
        else:
            prompt = rng.choice(long_prompts)
            tokens = rng.randint(250, 800)
        records.append({"prompt": prompt, "completion_tokens": tokens})
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"Generated {n} synthetic samples → {path}")


def load_data(path: str) -> tuple[list[str], list[int]]:
    """Load JSONL → (prompt_texts, completion_token_counts)."""
    texts: list[str] = []
    tokens: list[int] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line.strip())
            prompt = rec.get("prompt", "")
            if not prompt:
                continue
            texts.append(prompt)
            tokens.append(int(rec.get("completion_tokens", 100)))
    return texts, tokens


# ── Kendall's tau ──────────────────────────────────────────────────────────


def kendall_tau(predicted: list[float], actual: list[float]) -> float:
    """Compute Kendall's tau (O(n^2) pairwise)."""
    n = len(predicted)
    if n < 2:
        return 0.0
    concordant = 0
    total = 0
    for i in range(n):
        for j in range(i + 1, n):
            total += 1
            p = (predicted[i] > predicted[j]) - (predicted[i] < predicted[j])
            a = (actual[i] > actual[j]) - (actual[i] < actual[j])
            if p == a:
                concordant += 1
    return (2.0 * concordant / total) - 1.0


# ── Training ────────────────────────────────────────────────────────────────


def train(
    data_path: str,
    output_path: str,
    epochs: int,
    batch_size: int,
) -> None:
    texts, targets = load_data(data_path)
    n = len(texts)
    print(f"Loaded {n} samples from {data_path}")

    if n < batch_size:
        batch_size = n

    print(f"Pre-computing embeddings with {_ENCODER_NAME}...")
    model = SemanticRankingModel()
    # Pre-compute all embeddings in batches to avoid OOM
    emb_batches: list[torch.Tensor] = []
    encode_batch = 64
    for start in range(0, n, encode_batch):
        batch_texts = texts[start:start + encode_batch]
        emb_batches.append(model.encode(batch_texts))
        pct = min(100, int((start + encode_batch) / n * 100))
        if pct % 25 == 0:
            print(f"  Encoding: {pct}%")
    all_embeddings = torch.cat(emb_batches, dim=0)
    print(f"Embeddings shape: {all_embeddings.shape}")

    all_targets = torch.tensor(targets, dtype=torch.float32)

    # Split 90/10
    split = int(n * 0.9)
    indices = list(range(n))
    random.shuffle(indices)
    train_idx = indices[:split]
    val_idx = indices[split:]

    train_embs = all_embeddings[train_idx]
    train_targets = all_targets[train_idx]
    val_embs = all_embeddings[val_idx]
    val_targets_list = [targets[i] for i in val_idx]

    optimizer = torch.optim.Adam(model.mlp.parameters(), lr=1e-3)

    for epoch in range(1, epochs + 1):
        model.mlp.train()
        perm = torch.randperm(len(train_idx))
        epoch_loss = 0.0
        n_batches = 0

        for start in range(0, len(perm), batch_size):
            batch_perm = perm[start:start + batch_size]
            embs = train_embs[batch_perm]
            tgt = train_targets[batch_perm]

            scores = model.mlp(embs)
            loss = list_mle_loss(scores, tgt)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            epoch_loss += loss.item()
            n_batches += 1

        avg_loss = epoch_loss / max(n_batches, 1)
        if epoch % 5 == 0 or epoch == 1:
            print(f"Epoch {epoch:3d}/{epochs}  loss={avg_loss:.4f}")

    # Validate
    model.mlp.eval()
    with torch.no_grad():
        val_scores = model.mlp(val_embs).tolist()
    tau = kendall_tau(val_scores, val_targets_list)
    print(f"\nValidation Kendall's tau: {tau:.4f}")

    # Save (only MLP weights — encoder is re-loaded from HF at inference time)
    torch.save({
        "architecture": "semantic",
        "encoder_name": _ENCODER_NAME,
        "mlp_state": model.mlp.state_dict(),
    }, output_path)
    print(f"Model saved to {output_path}")


# ── CLI ────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Semantic LTR Model")
    parser.add_argument("--data", default="sharegpt_train.jsonl", help="JSONL training data")
    parser.add_argument("--output", default="ltr_model.pt", help="Output model path")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("-n", "--batch-size", type=int, default=32)
    parser.add_argument("--download-sharegpt", action="store_true",
                        help="Download ShareGPT dataset")
    parser.add_argument("--generate-synthetic", action="store_true",
                        help="Generate synthetic data for testing")
    parser.add_argument("--max-samples", type=int, default=20000,
                        help="Max samples to download from ShareGPT")
    args = parser.parse_args()

    if args.download_sharegpt:
        download_sharegpt(args.data, args.max_samples)
        return

    if args.generate_synthetic:
        generate_synthetic(args.data)
        return

    train(args.data, args.output, args.epochs, args.batch_size)


if __name__ == "__main__":
    main()
