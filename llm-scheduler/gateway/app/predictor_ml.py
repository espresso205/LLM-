"""ML-based output length predictor using a trained RankingMLP.

Implements the learning-to-rank approach from "Efficient LLM Scheduling by
Learning to Rank" (NeurIPS 2024) with a simplified architecture:

- Input features (5 dims): prompt stats + max_tokens
- Model: 3-layer MLP (5 → 32 → 16 → 1)
- Output: ranking score (lower = shorter output = higher priority)
"""
import json
from pathlib import Path

import torch
import torch.nn as nn

from shared.utils import get_logger

log = get_logger(__name__)


class RankingMLP(nn.Module):
    """Simple 3-layer MLP for output-length ranking."""

    def __init__(self) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(5, 32),
            nn.ReLU(),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x).squeeze(-1)


def _extract_features(body: dict) -> list[float]:
    """Extract 5 features from a request body (must match collector fields)."""
    messages = body.get("messages", [])
    all_text = " ".join(m.get("content", "") for m in messages)
    last_msg = messages[-1].get("content", "") if messages else ""
    return [
        float(len(all_text)),
        float(len(all_text.split())),
        float(body.get("max_tokens") or 512),
        float(len(messages)),
        float(len(last_msg)),
    ]


class LTRPredictor:
    """ML-based predictor backed by a pre-trained RankingMLP."""

    def __init__(self, model_path: str) -> None:
        path = Path(model_path)
        if not path.exists():
            raise FileNotFoundError(f"LTR model not found: {path}")

        data = torch.load(path, map_location="cpu", weights_only=False)
        state = data["model_state"]
        self._mean: list[float] = data["feat_mean"]
        self._std: list[float] = data["feat_std"]

        self._model = RankingMLP()
        self._model.load_state_dict(state)
        self._model.eval()
        log.info(f"LTRPredictor loaded from {path}")

    def predict(self, body: dict) -> float:
        """Return predicted output-length score (lower = shorter)."""
        features = _extract_features(body)
        x = torch.tensor([features], dtype=torch.float32)
        # Normalize with training stats
        mean = torch.tensor([self._mean], dtype=torch.float32)
        std = torch.tensor([self._std], dtype=torch.float32)
        std = torch.where(std == 0, torch.ones_like(std), std)
        x = (x - mean) / std

        with torch.no_grad():
            score = self._model(x)
        return float(score.item())
