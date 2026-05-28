"""Benchmark: FCFS vs LTR (SJF) scheduling comparison.

Demonstrates the Head-of-Line blocking improvement from
"Efficient LLM Scheduling by Learning to Rank" (NeurIPS 2024).

Two modes:
  Simulation (default) — synthetic workload, no gateway needed
  Live (--live) — send real requests to a running gateway

Usage:
  python scripts/benchmark_ltr.py                # simulation
  python scripts/benchmark_ltr.py -n 500         # more requests
  python scripts/benchmark_ltr.py --seed 42      # reproducible
  python scripts/benchmark_ltr.py --live         # live gateway
"""
import argparse
import json
import random
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gateway.app.predictor import HeuristicPredictor

# ── Workload generation ──────────────────────────────────────────────────

SHORT_PROMPTS = [
    "Hi", "What is 2+2?", "Say hello", "Yes or no?", "List three colors",
    "What day is it?", "Tell me a joke", "Translate 'hello' to French",
    "What's the capital of France?", "Define 'algorithm' in one sentence",
    "1+1=?", "How are you?", "What time is it?", "给出一个词形容天气",
    "简述什么是AI", "列出三种编程语言",
]

MEDIUM_PROMPTS = [
    "Explain how neural networks work in a few paragraphs",
    "Compare REST and GraphQL APIs",
    "Describe the water cycle in detail",
    "What are the pros and cons of microservices?",
    "Explain the difference between TCP and UDP",
    "Summarize the key ideas behind containerization",
    "What is the theory of relativity? Explain briefly.",
    "解释什么是分布式系统及其优缺点",
    "描述HTTP和HTTPS的区别",
    "简述机器学习和深度学习的区别",
]

LONG_PROMPTS = [
    "Write a comprehensive essay on the impact of artificial intelligence on modern society, covering economic, social, and ethical implications",
    "Provide a detailed comparison of Python, JavaScript, and Go as backend programming languages, including performance benchmarks, ecosystem, and use cases",
    "Explain the complete lifecycle of a web request from browser to server and back, including DNS resolution, TCP handshake, TLS negotiation, HTTP parsing, and response rendering",
    "写一篇详细的论文，讨论大语言模型在自然语言处理中的最新进展，包括预训练方法、微调策略、以及对下游任务的影响",
    "详细解释Kubernetes的架构设计，包括Pod、Service、Deployment、Ingress等核心概念，以及它们如何协同工作来管理容器化应用",
]


def _make_request(category: str, rng: random.Random) -> dict:
    """Generate a synthetic request for a given category."""
    if category == "short":
        prompt = rng.choice(SHORT_PROMPTS)
        max_tokens = rng.randint(30, 80)
    elif category == "medium":
        prompt = rng.choice(MEDIUM_PROMPTS)
        max_tokens = rng.randint(100, 250)
    else:
        prompt = rng.choice(LONG_PROMPTS)
        max_tokens = rng.randint(400, 800)
    return {
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "model": "auto",
    }


def _actual_length(category: str, max_tokens: int, rng: random.Random) -> int:
    """Simulate actual output length (correlated with category)."""
    if category == "short":
        base = max_tokens * rng.uniform(0.4, 0.9)
    elif category == "medium":
        base = max_tokens * rng.uniform(0.5, 0.95)
    else:
        base = max_tokens * rng.uniform(0.6, 0.98)
    return int(min(base, max_tokens))


def generate_workload(n: int, rng: random.Random) -> list[dict]:
    """Generate a mixed workload: 30% short, 40% medium, 30% long."""
    requests: list[dict] = []
    for _ in range(n):
        r = rng.random()
        if r < 0.3:
            cat = "short"
        elif r < 0.7:
            cat = "medium"
        else:
            cat = "long"
        body = _make_request(cat, rng)
        actual = _actual_length(cat, body["max_tokens"], rng)
        requests.append({"body": body, "category": cat, "actual_tokens": actual})
    rng.shuffle(requests)
    return requests


# ── Simulation ────────────────────────────────────────────────────────────


def simulate(workload: list[dict], policy: str, rng: random.Random) -> list[dict]:
    """Simulate a single-server queue with the given policy.

    Returns list with arrival_time, start_time, completion_time for each request.
    """
    predictor = HeuristicPredictor()
    items = []
    for i, req in enumerate(workload):
        items.append({
            **req,
            "arrival": float(i) * 0.1,  # requests arrive every 0.1s
            "predicted": predictor.predict(req["body"]),
        })

    # Sort by policy
    if policy == "sjf":
        items.sort(key=lambda x: x["predicted"])
    # FCFS: keep original (shuffled) order

    results: list[dict] = []
    server_free = 0.0
    tok_per_sec = 20.0

    for item in items:
        processing = item["actual_tokens"] / tok_per_sec
        start = max(item["arrival"], server_free)
        complete = start + processing
        server_free = complete
        results.append({
            **item,
            "start": start,
            "complete": complete,
            "latency": complete - item["arrival"],
            "wait": start - item["arrival"],
        })
    return results


def compute_metrics(results: list[dict], label: str) -> dict[str, Any]:
    """Compute latency metrics from simulation results."""
    latencies = sorted(r["latency"] for r in results)
    n = len(latencies)
    by_cat: dict[str, list[float]] = defaultdict(list)
    for r in results:
        by_cat[r["category"]].append(r["latency"])

    def pct(arr: list[float], p: float) -> float:
        idx = int(len(arr) * p / 100)
        return arr[min(idx, len(arr) - 1)]

    return {
        "policy": label,
        "total_requests": n,
        "mean_latency": round(sum(latencies) / n, 3),
        "p50": round(pct(latencies, 50), 3),
        "p95": round(pct(latencies, 95), 3),
        "p99": round(pct(latencies, 99), 3),
        "short_mean": round(sum(by_cat["short"]) / max(len(by_cat["short"]), 1), 3),
        "medium_mean": round(sum(by_cat["medium"]) / max(len(by_cat["medium"]), 1), 3),
        "long_mean": round(sum(by_cat["long"]) / max(len(by_cat["long"]), 1), 3),
        "throughput": round(n / max(latencies[-1], 0.001), 2),
    }


def kendall_tau(predicted: list[float], actual: list[float]) -> float:
    """Compute Kendall's tau correlation (concordant/total pairs formula)."""
    n = len(predicted)
    concordant = 0
    total = 0
    for i in range(n):
        for j in range(i + 1, n):
            total += 1
            p_sign = (predicted[i] > predicted[j]) - (predicted[i] < predicted[j])
            a_sign = (actual[i] > actual[j]) - (actual[i] < actual[j])
            if p_sign == a_sign:
                concordant += 1
    return (2.0 * concordant / total) - 1.0 if total > 0 else 0.0


# ── Live mode ─────────────────────────────────────────────────────────────


def run_live(n: int, base_url: str) -> None:
    """Send real requests to a running gateway."""
    try:
        import requests as http_requests
    except ImportError:
        print("ERROR: 'requests' library needed for --live mode. pip install requests")
        return

    # Login
    resp = http_requests.post(
        f"{base_url}/auth/login",
        data={"username": "admin", "password": "admin123"},
    )
    if resp.status_code != 200:
        print(f"Login failed: {resp.status_code} {resp.text}")
        return
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    rng = random.Random()
    categories: dict[str, list[float]] = {"short": [], "medium": [], "long": []}

    for i in range(n):
        r = rng.random()
        cat = "short" if r < 0.3 else ("medium" if r < 0.7 else "long")
        body = _make_request(cat, rng)
        try:
            t0 = time.time()
            resp = http_requests.post(
                f"{base_url}/v1/chat/completions",
                json=body,
                headers=headers,
                timeout=120,
            )
            elapsed = time.time() - t0
            if resp.status_code == 200:
                categories[cat].append(elapsed)
                print(f"  [{i+1}/{n}] {cat:6s}  {elapsed:.2f}s")
            else:
                print(f"  [{i+1}/{n}] {cat:6s}  ERROR {resp.status_code}")
        except Exception as exc:
            print(f"  [{i+1}/{n}] {cat:6s}  FAIL: {exc}")

    print("\n── Live Results ──")
    for cat in ["short", "medium", "long"]:
        lats = sorted(categories[cat])
        if lats:
            print(f"  {cat:6s}  n={len(lats):3d}  mean={sum(lats)/len(lats):.2f}s  "
                  f"p50={lats[len(lats)//2]:.2f}s")
        else:
            print(f"  {cat:6s}  no successful requests")


# ── Main ──────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="LTR Benchmark: FCFS vs SJF")
    parser.add_argument("-n", "--num-requests", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--live", action="store_true", help="Test against live gateway")
    parser.add_argument("--base-url", default="http://localhost:8080")
    args = parser.parse_args()

    if args.live:
        run_live(args.num_requests, args.base_url)
        return

    rng = random.Random(args.seed)
    workload = generate_workload(args.num_requests, rng)
    print(f"Generated {len(workload)} requests "
          f"(short={sum(1 for w in workload if w['category']=='short')}, "
          f"medium={sum(1 for w in workload if w['category']=='medium')}, "
          f"long={sum(1 for w in workload if w['category']=='long')})")

    # Kendall's tau
    predictor = HeuristicPredictor()
    predicted = [predictor.predict(w["body"]) for w in workload]
    actual = [float(w["actual_tokens"]) for w in workload]
    tau = kendall_tau(predicted, actual)
    print(f"Predictor Kendall's tau: {tau:.4f}\n")

    # Run both policies
    fcfs_results = simulate(workload, "fcfs", rng)
    sjf_results = simulate(workload, "sjf", rng)

    fcfs_m = compute_metrics(fcfs_results, "FCFS")
    sjf_m = compute_metrics(sjf_results, "SJF (LTR)")

    # Print comparison table
    print("┌──────────────────┬────────────┬────────────┐")
    print("│ Metric           │     FCFS   │  SJF (LTR) │")
    print("├──────────────────┼────────────┼────────────┼")
    for key in ["mean_latency", "p50", "p95", "p99",
                "short_mean", "medium_mean", "long_mean", "throughput"]:
        f_val = fcfs_m[key]
        s_val = sjf_m[key]
        unit = "req/s" if key == "throughput" else "s"
        print(f"│ {key:16s} │ {f_val:8.3f} {unit} │ {s_val:8.3f} {unit} │")
    print("└──────────────────┴────────────┴────────────┘")

    # Improvement
    if fcfs_m["mean_latency"] > 0:
        speedup = fcfs_m["mean_latency"] / sjf_m["mean_latency"]
        short_speedup = fcfs_m["short_mean"] / sjf_m["short_mean"] if sjf_m["short_mean"] > 0 else 0
        print(f"\nMean latency improvement: {speedup:.2f}x")
        print(f"Short request improvement: {short_speedup:.2f}x")

    # Save results
    results = {"fcfs": fcfs_m, "sjf": sjf_m, "kendall_tau": round(tau, 4), "seed": args.seed}
    with open("benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to benchmark_results.json")

    # Plot CDF (optional)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fcfs_lats = sorted(r["latency"] for r in fcfs_results)
        sjf_lats = sorted(r["latency"] for r in sjf_results)
        n = len(fcfs_lats)
        y = [i / n for i in range(n)]

        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot(fcfs_lats, y, label="FCFS", linewidth=2)
        ax.plot(sjf_lats, y, label="SJF (LTR)", linewidth=2)
        ax.set_xlabel("Latency (seconds)")
        ax.set_ylabel("CDF")
        ax.set_title("FCFS vs SJF (LTR) Latency Distribution")
        ax.legend()
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig("benchmark_cdf.png", dpi=150)
        print("CDF plot saved to benchmark_cdf.png")
    except ImportError:
        print("(matplotlib not installed, skipping CDF plot)")


if __name__ == "__main__":
    main()
