"""Semantic output-length predictor using Sentence-Transformers + MLP.

Aligns with the paper "Efficient LLM Scheduling by Learning to Rank"
(NeurIPS 2024): a pre-trained encoder understands prompt semantics, and an
MLP head maps the semantic embedding to a ranking score.

Architecture:
  prompt text → SentenceTransformer (frozen, 384-dim) → MLP (384→128→64→1) → score

Lower score = shorter predicted output = higher scheduling priority.
"""
from pathlib import Path

import torch
import torch.nn as nn
from sentence_transformers import SentenceTransformer

from shared.utils import get_logger

log = get_logger(__name__)

_ENCODER_NAME = "all-MiniLM-L6-v2"
_EMBED_DIM = 384


class RankingMLP(nn.Module):
    """Legacy 5-feature MLP (kept for backward-compatible model loading)."""

    def __init__(self) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(5, 32), nn.ReLU(),
            nn.Linear(32, 16), nn.ReLU(),
            nn.Linear(16, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x).squeeze(-1)


class SemanticRankingModel(nn.Module):
    """Sentence-Transformer encoder (frozen) + trainable MLP ranking head."""

    def __init__(self, encoder_name: str = _ENCODER_NAME) -> None:
        super().__init__()
        self.encoder = SentenceTransformer(encoder_name)
        for p in self.encoder.parameters():
            p.requires_grad = False
        self.mlp = nn.Sequential(
            nn.Linear(_EMBED_DIM, 128), nn.ReLU(),
            nn.Linear(128, 64), nn.ReLU(),
            nn.Linear(64, 1),
        )

    def encode(self, texts: list[str]) -> torch.Tensor:
        """Return (B, 384) embeddings from prompt texts."""
        with torch.no_grad():
            import numpy as np
            embs = self.encoder.encode(
                texts, convert_to_numpy=True, show_progress_bar=False,
            )
            return torch.from_numpy(np.array(embs, dtype=np.float32))

    def forward(self, embeddings: torch.Tensor) -> torch.Tensor:
        """Return (B,) ranking scores from pre-computed embeddings."""
        return self.mlp(embeddings).squeeze(-1)


def _extract_prompt_text(body: dict) -> str:
    """Join all message contents into a single prompt string."""
    messages = body.get("messages", [])
    return " ".join(m.get("content", "") for m in messages)


class LTRPredictor:
    """ML-based predictor — auto-detects legacy or semantic model format."""

    def __init__(self, model_path: str) -> None:
        path = Path(model_path)
        if not path.exists():
            raise FileNotFoundError(f"LTR model not found: {path}")

        data = torch.load(path, map_location="cpu", weights_only=False)

        if data.get("architecture") == "semantic":
            self._semantic = True
            self._model = SemanticRankingModel(data.get("encoder_name", _ENCODER_NAME))
            self._model.mlp.load_state_dict(data["mlp_state"])
            self._model.eval()
            log.info(f"LTRPredictor (semantic) loaded from {path}")
        else:
            self._semantic = False
            self._model = RankingMLP()
            self._model.load_state_dict(data["model_state"])
            self._mean = data["feat_mean"]
            self._std = data["feat_std"]
            self._model.eval()
            log.info(f"LTRPredictor (legacy feature-based) loaded from {path}")

    def predict(self, body: dict) -> float:
        """Return predicted output-length score (lower = shorter)."""
        if self._semantic:
            text = _extract_prompt_text(body)
            emb = self._model.encode([text])
            with torch.no_grad():
                score = self._model.mlp(emb)
            return float(score.item())

        # Legacy path
        messages = body.get("messages", [])
        all_text = " ".join(m.get("content", "") for m in messages)
        last_msg = messages[-1].get("content", "") if messages else ""
        features = [
            float(len(all_text)),
            float(len(all_text.split())),
            float(body.get("max_tokens") or 512),
            float(len(messages)),
            float(len(last_msg)),
        ]
        x = torch.tensor([features], dtype=torch.float32)
        mean = torch.tensor([self._mean], dtype=torch.float32)
        std = torch.tensor([self._std], dtype=torch.float32)
        std = torch.where(std == 0, torch.ones_like(std), std)
        x = (x - mean) / std
        with torch.no_grad():
            score = self._model(x)
        return float(score.item())
