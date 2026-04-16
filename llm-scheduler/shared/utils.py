"""Shared utilities: logging setup and timing helpers."""
from __future__ import annotations
import logging
import time
from contextlib import contextmanager
from typing import Generator


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


@contextmanager
def timer() -> Generator[dict, None, None]:
    """Context manager that records elapsed milliseconds into result['ms']."""
    result: dict = {}
    start = time.perf_counter()
    try:
        yield result
    finally:
        result["ms"] = (time.perf_counter() - start) * 1000
