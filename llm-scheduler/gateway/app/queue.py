"""LTR-based priority request queue for SJF-approximate scheduling.

Implements the gateway-level analogue of the scheduling algorithm from
"Efficient LLM Scheduling by Learning to Rank" (NeurIPS 2024):

1. A predictor estimates output lengths for incoming requests.
2. Requests sit in a priority queue ordered by predicted length (shortest first).
3. A background dispatch loop sends the highest-priority request whenever a
   concurrency slot is available.
4. Starvation prevention: requests waiting beyond a threshold get their priority
   boosted exponentially so they are never indefinitely delayed.
"""
import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

from shared.utils import get_logger

from .collector import data_collector
from .config import settings
from .predictor import HeuristicPredictor, LengthPredictor, PassthroughPredictor
from .retry import forward_with_retry, forward_with_retry_stream

log = get_logger(__name__)


@dataclass
class QueueEntry:
    """A single request waiting in the priority queue."""

    request_id: str
    body: dict
    user: dict
    predicted_length: float
    enqueue_time: float
    is_stream: bool
    future: asyncio.Future | None = None

    def __post_init__(self) -> None:
        if self.future is None:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
            self.future = loop.create_future()


def _make_predictor() -> LengthPredictor:
    predictor_type = settings.LTR_PREDICTOR_TYPE
    if predictor_type == "heuristic":
        return HeuristicPredictor()
    if predictor_type == "passthrough":
        return PassthroughPredictor()
    if predictor_type == "ml":
        from .predictor_ml import LTRPredictor
        model_path = settings.LTR_ML_MODEL_PATH
        if not model_path:
            log.warning("LTR_ML_MODEL_PATH not set, falling back to heuristic")
            return HeuristicPredictor()
        return LTRPredictor(model_path)
    # Default to heuristic for unknown types
    log.warning(f"Unknown LTR_PREDICTOR_TYPE '{predictor_type}', falling back to heuristic")
    return HeuristicPredictor()


class RequestQueue:
    """In-memory priority queue with background dispatch and starvation prevention."""

    def __init__(self) -> None:
        self._entries: list[QueueEntry] = []
        self._lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(settings.LTR_MAX_CONCURRENT)
        self._predictor = _make_predictor()
        self._stopped = False

    # ── Public API ────────────────────────────────────────────────────────

    async def enqueue(
        self,
        request_id: str,
        body: dict,
        user: dict,
    ) -> Any:
        """Add a request to the priority queue and await its completion.

        Returns ``(response_data, node_id, actual_model)`` for non-streaming
        or ``(stream_generator, node_id, actual_model)`` for streaming —
        matching the return type of ``forward_with_retry`` /
        ``forward_with_retry_stream``.
        """
        is_stream = bool(body.get("stream"))
        predicted = self._predictor.predict(body)

        entry = QueueEntry(
            request_id=request_id,
            body=body,
            user=user,
            predicted_length=predicted,
            enqueue_time=time.monotonic(),
            is_stream=is_stream,
        )

        async with self._lock:
            if len(self._entries) >= settings.LTR_MAX_QUEUE_SIZE:
                log.warning(
                    f"LTR queue full ({len(self._entries)}), "
                    f"falling back to direct dispatch for {request_id}"
                )
                return await self._direct_dispatch(entry)
            self._entries.append(entry)

        from shared.metrics import LTR_QUEUE_SIZE
        LTR_QUEUE_SIZE.set(len(self._entries))

        return await entry.future

    async def dispatch_loop(self) -> None:
        """Background task: continuously dispatch the highest-priority request."""
        log.info("LTR dispatch loop started")
        while not self._stopped:
            try:
                await self._semaphore.acquire()
                entry = await self._pick_next()
                if entry is None:
                    self._semaphore.release()
                    await asyncio.sleep(0.05)
                    continue
                asyncio.create_task(self._dispatch_and_release(entry))
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                log.error(f"LTR dispatch loop error: {exc}")
                self._semaphore.release()
                await asyncio.sleep(0.1)

    def stop(self) -> None:
        self._stopped = True

    # ── Internal ──────────────────────────────────────────────────────────

    def _compute_priority(self, entry: QueueEntry) -> float:
        """Lower value = higher priority (dispatched sooner).

        Combines predicted output length with starvation-prevention aging.
        """
        priority = entry.predicted_length
        wait_time = time.monotonic() - entry.enqueue_time
        timeout = settings.LTR_STARVATION_TIMEOUT

        if wait_time > timeout:
            overshoot = wait_time - timeout
            boost = settings.LTR_STARVATION_BOOST ** (overshoot / timeout)
            priority *= boost
            from shared.metrics import LTR_STARVATION_BOOSTS
            LTR_STARVATION_BOOSTS.inc()

        return priority

    async def _pick_next(self) -> QueueEntry | None:
        """Remove and return the highest-priority entry (lowest score)."""
        async with self._lock:
            if not self._entries:
                return None
            # Find the entry with the lowest priority score
            best_idx = 0
            best_score = self._compute_priority(self._entries[0])
            for i in range(1, len(self._entries)):
                score = self._compute_priority(self._entries[i])
                if score < best_score:
                    best_score = score
                    best_idx = i
            return self._entries.pop(best_idx)

    async def _dispatch_and_release(self, entry: QueueEntry) -> None:
        """Dispatch a single request and release the semaphore when done."""
        wait_time = time.monotonic() - entry.enqueue_time
        from shared.metrics import LTR_QUEUE_WAIT_SECONDS
        LTR_QUEUE_WAIT_SECONDS.observe(wait_time)

        from shared.metrics import LTR_QUEUE_SIZE
        async with self._lock:
            LTR_QUEUE_SIZE.set(len(self._entries))

        try:
            if entry.is_stream:
                result = await forward_with_retry_stream(entry.request_id, entry.body)
            else:
                result = await forward_with_retry(entry.request_id, entry.body)

            if not entry.future.done():
                entry.future.set_result(result)

            # Collect training data
            self._record_training_data(entry, result)

        except Exception as exc:
            if not entry.future.done():
                entry.future.set_exception(exc)
        finally:
            self._semaphore.release()

    async def _direct_dispatch(self, entry: QueueEntry) -> Any:
        """Bypass the queue and dispatch immediately (FCFS fallback)."""
        if entry.is_stream:
            return await forward_with_retry_stream(entry.request_id, entry.body)
        return await forward_with_retry(entry.request_id, entry.body)

    def _record_training_data(self, entry: QueueEntry, result: Any) -> None:
        """Record completed request data for future model training."""
        try:
            if entry.is_stream:
                # Streaming responses don't have a simple result dict
                return
            response_data, _node_id, model = result
            completion_tokens = response_data.get("usage", {}).get("completion_tokens", 0)
            data_collector.record(
                request_id=entry.request_id,
                body=entry.body,
                actual_completion_tokens=completion_tokens,
                latency_ms=(time.monotonic() - entry.enqueue_time) * 1000,
                model=model or "unknown",
            )
        except Exception as exc:
            log.error(f"Failed to record training data for {entry.request_id}: {exc}")

    @property
    def size(self) -> int:
        return len(self._entries)


request_queue = RequestQueue()
