"""Training data collector for future LTR model training.

Records (prompt features, actual output length) pairs for each completed
request.  Data is buffered in memory and flushed to a JSONL file periodically.
"""
import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shared.utils import get_logger

from .config import settings

log = get_logger(__name__)


class DataCollector:
    """Collects request-level training data and writes it to JSONL."""

    def __init__(self) -> None:
        self._buffer: list[dict[str, Any]] = []
        self._flush_interval: float = 60.0
        self._path = Path(settings.LTR_TRAINING_DATA_PATH)

    def record(
        self,
        *,
        request_id: str,
        body: dict,
        actual_completion_tokens: int,
        latency_ms: float,
        model: str,
    ) -> None:
        """Append a training sample to the in-memory buffer."""
        messages = body.get("messages", [])
        all_text = " ".join(m.get("content", "") for m in messages)
        last_msg = messages[-1].get("content", "") if messages else ""

        self._buffer.append(
            {
                "request_id": request_id,
                "prompt_char_count": len(all_text),
                "prompt_word_count": len(all_text.split()),
                "max_tokens": body.get("max_tokens"),
                "message_count": len(messages),
                "last_message_length": len(last_msg),
                "actual_completion_tokens": actual_completion_tokens,
                "latency_ms": round(latency_ms, 2),
                "model": model,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    async def flush_loop(self) -> None:
        """Background task: flush buffer to disk periodically."""
        while True:
            await asyncio.sleep(self._flush_interval)
            self._flush()

    def _flush(self) -> None:
        if not self._buffer:
            return
        try:
            with self._path.open("a", encoding="utf-8") as f:
                for entry in self._buffer:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            log.info(f"Flushed {len(self._buffer)} training samples to {self._path}")
            self._buffer.clear()
        except Exception as exc:
            log.error(f"Failed to flush training data: {exc}")

    @property
    def pending_count(self) -> int:
        return len(self._buffer)


data_collector = DataCollector()
