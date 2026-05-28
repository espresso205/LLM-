"""Train a RankingMLP model using ListMLE loss.

Reads training data (JSONL) collected by the gateway's DataCollector,
trains a 3-layer MLP to rank requests by predicted output length.

Usage:
    python scripts/train_ltr_model.py --generate-synthetic   # create test data
    python scripts/train_ltr_model.py                        # train on real data
    python scripts/train_ltr_model.py --epochs 100 -n 64     # custom params
"""
import argparse
import json
import random
import sys
from pathlib import Path

import torch
import torch.nn as nn

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gateway.app.predictor_ml import RankingMLP, _extract_features


# ── ListMLE loss ──────────────────────────────────────────────────────────


def list_mle_loss(scores: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    """ListMLE ranking loss (the paper's key contribution).

    Encourages the model to rank items in the same relative order as *targets*.
    """
    sorted_indices = torch.argsort(targets, descending=True)
    sorted_scores = scores[sorted_indices]

    n = sorted_scores.shape[0]
    log_probs: list[torch.Tensor] = []
    for i in range(n):
        remaining = sorted_scores[i:]
        log_softmax = torch.log_softmax(remaining, dim=0)
        log_probs.append(log_softmax[0])

    return -torch.stack(log_probs).sum()


# ── Synthetic data generation ─────────────────────────────────────────────


def generate_synthetic(path: str, n: int = 1000) -> None:
    """Create synthetic training data for pipeline testing."""
    rng = random.Random(42)
    records: list[dict] = []
    for i in range(n):
        char_count = rng.randint(10, 2000)
        word_count = max(1, char_count // 5 + rng.randint(-5, 5))
        max_tokens = rng.choice([64, 128, 256, 512, 1024])
        msg_count = rng.randint(1, 12)
        last_len = rng.randint(5, 500)
        # Correlated output: longer prompts & higher max_tokens → more output
        base = char_count * 0.05 + last_len * 0.1 + max_tokens * 0.3
        actual = max(5, int(base * rng.uniform(0.5, 1.5)))
        actual = min(actual, max_tokens)
        records.append({
            "request_id": f"syn-{i:04d}",
            "prompt_char_count": char_count,
            "prompt_word_count": word_count,
            "max_tokens": max_tokens,
            "message_count": msg_count,
            "last_message_length": last_len,
            "actual_completion_tokens": actual,
        })
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    print(f"Generated {n} synthetic samples → {path}")


# ── Training ──────────────────────────────────────────────────────────────


def load_data(path: str) -> tuple[list[list[float]], list[float]]:
    """Load JSONL training data → (features, targets)."""
    features: list[list[float]] = []
    targets: list[float] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line.strip())
            features.append([
                float(rec.get("prompt_char_count", 0)),
                float(rec.get("prompt_word_count", 0)),
                float(rec.get("max_tokens", 512)),
                float(rec.get("message_count", 1)),
                float(rec.get("last_message_length", 0)),
            ])
            targets.append(float(rec.get("actual_completion_tokens", 0)))
    return features, targets


def train(
    data_path: str,
    output_path: str,
    epochs: int,
    batch_size: int,
) -> None:
    features, targets = load_data(data_path)
    n = len(features)
    print(f"Loaded {n} samples from {data_path}")

    if n < batch_size:
        batch_size = n
        print(f"Reduced batch_size to {batch_size}")

    # Normalize features
    n_feats = len(features[0])
    feat_mean = [sum(f[d] for f in features) / n for d in range(n_feats)]
    feat_std = [
        (sum((f[d] - feat_mean[d]) ** 2 for f in features) / n) ** 0.5
        for d in range(n_feats)
    ]
    feat_std = [s if s > 0 else 1.0 for s in feat_std]
    features_norm = [
        [(f[d] - feat_mean[d]) / feat_std[d] for d in range(n_feats)]
        for f in features
    ]

    model = RankingMLP()
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)

    # Split 90/10
    split = int(n * 0.9)
    indices = list(range(n))
    random.shuffle(indices)
    train_idx = indices[:split]
    val_idx = indices[split:]

    for epoch in range(1, epochs + 1):
        model.train()
        random.shuffle(train_idx)
        epoch_loss = 0.0
        n_batches = 0

        for start in range(0, len(train_idx), batch_size):
            batch_idx = train_idx[start:start + batch_size]
            x = torch.tensor([features_norm[i] for i in batch_idx], dtype=torch.float32)
            y = torch.tensor([targets[i] for i in batch_idx], dtype=torch.float32)

            scores = model(x)
            loss = list_mle_loss(scores, y)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            epoch_loss += loss.item()
            n_batches += 1

        avg_loss = epoch_loss / max(n_batches, 1)
        if epoch % 10 == 0 or epoch == 1:
            print(f"Epoch {epoch:3d}/{epochs}  loss={avg_loss:.4f}")

    # Validate with Kendall's tau (concordant pairs / total pairs)
    model.eval()
    val_x = torch.tensor([features_norm[i] for i in val_idx], dtype=torch.float32)
    val_y = [targets[i] for i in val_idx]
    with torch.no_grad():
        val_scores = model(val_x).tolist()
    if len(val_y) > 1:
        n_concordant = 0
        n_total = 0
        for i in range(len(val_y)):
            for j in range(i + 1, len(val_y)):
                n_total += 1
                score_order = (val_scores[i] > val_scores[j]) - (val_scores[i] < val_scores[j])
                target_order = (val_y[i] > val_y[j]) - (val_y[i] < val_y[j])
                if score_order == target_order:
                    n_concordant += 1
        tau = (2.0 * n_concordant / n_total) - 1.0 if n_total > 0 else 0.0
        print(f"\nValidation Kendall's tau: {tau:.4f}")

    # Save
    torch.save({
        "model_state": model.state_dict(),
        "feat_mean": feat_mean,
        "feat_std": feat_std,
    }, output_path)
    print(f"Model saved to {output_path}")


# ── CLI ───────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="Train LTR RankingMLP")
    parser.add_argument("--data", default="training_data.jsonl", help="JSONL training data")
    parser.add_argument("--output", default="ltr_model.pt", help="Output model path")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("-n", "--batch-size", type=int, default=32)
    parser.add_argument("--generate-synthetic", action="store_true",
                        help="Generate synthetic training data for testing")
    args = parser.parse_args()

    if args.generate_synthetic:
        generate_synthetic(args.data)
        return

    train(args.data, args.output, args.epochs, args.batch_size)


if __name__ == "__main__":
    main()
