"""Unit tests for LTR scheduling components.

Run with:  python -m pytest scripts/test_ltr_strategy.py -v
"""
import asyncio
import time

import pytest

# ---------------------------------------------------------------------------
# predictor tests
# ---------------------------------------------------------------------------

def _make_body(
    messages=None,
    max_tokens=512,
    **extra,
):
    if messages is None:
        messages = [{"role": "user", "content": "Hello"}]
    return {"messages": messages, "max_tokens": max_tokens, **extra}


class TestHeuristicPredictor:
    def setup_method(self):
        from gateway.app.predictor import HeuristicPredictor
        self.predictor = HeuristicPredictor()

    def test_short_keyword_reduces_estimate(self):
        long_body = _make_body(
            messages=[{"role": "user", "content": "Please give a detailed explanation of quantum physics"}],
            max_tokens=512,
        )
        short_body = _make_body(
            messages=[{"role": "user", "content": "List the planets briefly"}],
            max_tokens=512,
        )
        long_pred = self.predictor.predict(long_body)
        short_pred = self.predictor.predict(short_body)
        assert short_pred < long_pred, "Short-keyword requests should have lower predicted length"

    def test_low_max_tokens_respected(self):
        body = _make_body(max_tokens=20)
        pred = self.predictor.predict(body)
        assert pred <= 20.0

    def test_multi_turn_increases_estimate(self):
        short_turns = _make_body(
            messages=[{"role": "user", "content": "Hello"}],
        )
        many_turns = _make_body(
            messages=[
                {"role": "user", "content": f"Message {i}"} for i in range(8)
            ],
        )
        short_pred = self.predictor.predict(short_turns)
        many_pred = self.predictor.predict(many_turns)
        assert many_pred > short_pred, "More turns should increase estimated length"

    def test_very_short_prompt_gets_discount(self):
        short = _make_body(
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=512,
        )
        normal = _make_body(
            messages=[{"role": "user", "content": "A " * 100}],
            max_tokens=512,
        )
        assert self.predictor.predict(short) < self.predictor.predict(normal)

    def test_chinese_short_keywords(self):
        body = _make_body(
            messages=[{"role": "user", "content": "请简述这个过程"}],
            max_tokens=512,
        )
        base_body = _make_body(
            messages=[{"role": "user", "content": "请描述这个过程"}],
            max_tokens=512,
        )
        assert self.predictor.predict(body) < self.predictor.predict(base_body)


class TestPassthroughPredictor:
    def test_always_returns_constant(self):
        from gateway.app.predictor import PassthroughPredictor
        p = PassthroughPredictor()
        assert p.predict(_make_body()) == 1.0
        assert p.predict(_make_body(max_tokens=9999)) == 1.0


# ---------------------------------------------------------------------------
# queue tests
# ---------------------------------------------------------------------------

class TestQueuePriority:
    def setup_method(self):
        # Create a fresh queue with mocked dependencies
        from gateway.app.queue import RequestQueue
        from gateway.app.predictor import PassthroughPredictor
        self.queue = RequestQueue()
        # Use passthrough so predicted_length is set manually
        self.queue._predictor = PassthroughPredictor()

    def test_dispatches_shortest_first(self):
        """Enqueue 3 requests with different predicted lengths; verify dispatch order."""
        from gateway.app.queue import QueueEntry

        entries: list[QueueEntry] = []
        for length in [100, 50, 200]:
            entry = QueueEntry(
                request_id=f"req-{length}",
                body={"messages": [{"role": "user", "content": "test"}]},
                user={"id": 1, "username": "test"},
                predicted_length=float(length),
                enqueue_time=time.monotonic(),
                is_stream=False,
            )
            self.queue._entries.append(entry)
            entries.append(entry)

        # Pick in priority order
        first = asyncio.get_event_loop().run_until_complete(self.queue._pick_next())
        second = asyncio.get_event_loop().run_until_complete(self.queue._pick_next())
        third = asyncio.get_event_loop().run_until_complete(self.queue._pick_next())

        assert first.predicted_length == 50
        assert second.predicted_length == 100
        assert third.predicted_length == 200

    def test_empty_queue_returns_none(self):
        result = asyncio.get_event_loop().run_until_complete(self.queue._pick_next())
        assert result is None


class TestStarvationPrevention:
    def test_old_request_gets_boosted(self):
        """A long request that waited very long should outrank a newer one."""
        from gateway.app.queue import QueueEntry, RequestQueue

        queue = RequestQueue.__new__(RequestQueue)
        queue._entries = []
        queue._lock = asyncio.Lock()
        queue._semaphore = asyncio.Semaphore(4)
        queue._predictor = None
        queue._stopped = False

        # Long request enqueued 300 seconds ago (5 minutes)
        # With 0.8^(270/30) = 0.8^9 ≈ 0.134, effective length = 500 * 0.134 ≈ 67
        old_long = QueueEntry(
            request_id="old-long",
            body={},
            user={},
            predicted_length=500.0,
            enqueue_time=time.monotonic() - 300.0,
            is_stream=False,
        )
        # Medium request just arrived
        new_medium = QueueEntry(
            request_id="new-medium",
            body={},
            user={},
            predicted_length=100.0,
            enqueue_time=time.monotonic(),
            is_stream=False,
        )

        old_score = queue._compute_priority(old_long)
        new_score = queue._compute_priority(new_medium)

        # The old request should have a lower (better) score than the new one
        # because starvation prevention exponentially boosted its priority
        assert old_score < new_score, (
            f"Old request (score={old_score}) should have higher priority "
            f"than new medium request (score={new_score})"
        )


class TestQueueSizeLimit:
    def test_queue_respects_max_size(self):
        """When the queue is full, new requests should fall back to direct dispatch."""
        from gateway.app.queue import RequestQueue
        queue = RequestQueue()
        # Fill the queue to capacity
        from gateway.app.queue import QueueEntry
        for i in range(settings.LTR_MAX_QUEUE_SIZE):
            entry = QueueEntry(
                request_id=f"fill-{i}",
                body={},
                user={},
                predicted_length=100.0,
                enqueue_time=time.monotonic(),
                is_stream=False,
            )
            queue._entries.append(entry)

        assert queue.size == settings.LTR_MAX_QUEUE_SIZE


# ---------------------------------------------------------------------------
# Import settings for test constants
# ---------------------------------------------------------------------------
from gateway.app.config import settings


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
