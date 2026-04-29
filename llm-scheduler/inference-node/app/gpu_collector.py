"""GPU metrics collector — pynvml (hardware) + vLLM /metrics (inference engine)."""
import re
from typing import Optional

import httpx

from .config import settings
from shared.utils import get_logger

log = get_logger(__name__)

# ── pynvml availability flag ────────────────────────────────────────────────
_pynvml_available = False
try:
    import pynvml
    _pynvml_available = True
except ImportError:
    log.info("pynvml not installed — GPU hardware metrics will be unavailable")
except Exception:
    log.warning("pynvml init failed — GPU hardware metrics will be unavailable")


def _collect_hardware_metrics() -> dict:
    """Collect GPU hardware metrics via pynvml. Returns empty dict on failure."""
    if not _pynvml_available:
        return {}

    try:
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)  # first GPU

        util = pynvml.nvmlDeviceGetUtilizationRates(handle)
        mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
        temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)

        pynvml.nvmlShutdown()

        return {
            "gpu_util": float(util.gpu),
            "memory_used_gb": round(mem.used / (1024 ** 3), 3),
            "gpu_memory_total_gb": round(mem.total / (1024 ** 3), 3),
            "gpu_temperature": float(temp),
        }
    except Exception as exc:
        log.debug(f"pynvml collection failed: {exc}")
        try:
            pynvml.nvmlShutdown()
        except Exception:
            pass
        return {}


async def _collect_vllm_metrics() -> dict:
    """Collect inference-engine metrics from vLLM /metrics endpoint."""
    metrics_url = f"{settings.VLLM_URL}/metrics"
    result: dict = {}

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(metrics_url)
            if r.status_code != 200:
                return result
            text = r.text

        # Parse KV cache usage percentage from Prometheus exposition format
        # vLLM exposes: vllm:gpu_cache_usage_perc <value>
        kv_match = re.search(r"vllm:gpu_cache_usage_perc\s+([\d.eE+-]+)", text)
        if kv_match:
            result["kv_cache_usage"] = float(kv_match.group(1)) * 100.0

        # Also try the alternative metric name
        if "kv_cache_usage" not in result:
            kv_match2 = re.search(
                r"vllm_gpu_cache_usage_perc\s+([\d.eE+-]+)", text
            )
            if kv_match2:
                result["kv_cache_usage"] = float(kv_match2.group(1)) * 100.0

        # Parse average token generation latency from iteration counter
        # vllm:num_prompt_tokens_total and vllm:generation_tokens_total can be
        # used with timing info, but we use a simpler approach:
        # vllm:e2e_request_latency_seconds_sum / count if available
        lat_sum = re.search(
            r"vllm:e2e_request_latency_seconds_sum\s+([\d.eE+-]+)", text
        )
        lat_count = re.search(
            r"vllm:e2e_request_latency_seconds_count\s+([\d.eE+-]+)", text
        )
        if lat_sum and lat_count:
            total_lat = float(lat_sum.group(1))
            total_count = float(lat_count.group(1))
            if total_count > 0:
                # Average per-request latency in ms
                result["avg_token_latency"] = round(
                    (total_lat / total_count) * 1000.0, 2
                )

        # Parse running and waiting request counts
        running_match = re.search(
            r"vllm:num_requests_running\s+([\d.eE+-]+)", text
        )
        if running_match:
            result["num_requests_running"] = int(float(running_match.group(1)))

        waiting_match = re.search(
            r"vllm:num_requests_waiting\s+([\d.eE+-]+)", text
        )
        if waiting_match:
            result["num_requests_waiting"] = int(float(waiting_match.group(1)))

    except Exception as exc:
        log.debug(f"vLLM metrics collection failed: {exc}")

    return result


async def collect_gpu_metrics() -> dict:
    """
    Collect all GPU metrics for heartbeat reporting.

    Returns a dict with any of these keys (None if unavailable):
        gpu_util, memory_used_gb, gpu_memory_total_gb,
        gpu_temperature, kv_cache_usage, avg_token_latency
    """
    hw = _collect_hardware_metrics()
    vllm = await _collect_vllm_metrics()

    merged = {**hw, **vllm}

    # Ensure all expected keys are present (None if missing)
    return {
        "gpu_util": merged.get("gpu_util"),
        "memory_used_gb": merged.get("memory_used_gb"),
        "gpu_memory_total_gb": merged.get("gpu_memory_total_gb"),
        "gpu_temperature": merged.get("gpu_temperature"),
        "kv_cache_usage": merged.get("kv_cache_usage"),
        "avg_token_latency": merged.get("avg_token_latency"),
        "num_requests_running": merged.get("num_requests_running"),
        "num_requests_waiting": merged.get("num_requests_waiting"),
    }
