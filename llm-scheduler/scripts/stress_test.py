"""Stress test: FCFS vs Heuristic SJF vs LTR SJF vs Oracle SJF.

Simulates a single-server LLM inference queue under different scheduling
policies, matching the experimental setup from "Efficient LLM Scheduling
by Learning to Rank" (NeurIPS 2024, Figure 4).

Measures:
  - Per-strategy latency (mean, P50, P90, P99)
  - Per-category latency (short / medium / long requests)
  - HOL blocking metric (avg wait of short requests behind long ones)

Usage:
  python scripts/stress_test.py                          # default: 300 req, rate 32/s
  python scripts/stress_test.py -n 500                   # more requests
  python scripts/stress_test.py --rate 64                # higher arrival rate
  python scripts/stress_test.py --rates 10,20,40,64      # multi-rate sweep
  python scripts/stress_test.py --model ltr_model.pt     # use LTR model
"""
import argparse
import json
import math
import random
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gateway.app.predictor import HeuristicPredictor

# ── Simulation parameters ─────────────────────────────────────────────────

TOK_PER_SEC = 20.0  # Simulated GPU decode speed (tokens/s)


# ── Workload ───────────────────────────────────────────────────────────────


def generate_workload(n: int, rng: random.Random) -> list[dict]:
    """Generate mixed workload: 30% short, 40% medium, 30% long."""
    short_prompts = [
        "Hi", "What is 2+2?", "Say hello", "Yes or no?", "Tell me a joke",
        "What's the capital of France?", "Define algorithm in one sentence",
        "Translate 'hello' to French", "Give me three colors", "List prime numbers < 20",
        "What time is it?", "How are you?", "1+1=?", "What day is it?",
        "给出一个词形容天气", "简述什么是AI", "列出三种编程语言",
        "What is the speed of light?", "Name a primary color",
    ]
    medium_prompts = [
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
        "Compare SQL and NoSQL databases",
        "Explain Docker containers vs virtual machines",
    ]
    long_prompts = [
        "Write a comprehensive essay on the impact of artificial intelligence on modern society, covering economic, social, and ethical implications",
        "Provide a detailed comparison of Python, JavaScript, and Go as backend programming languages, including performance benchmarks and ecosystem",
        "Explain the complete lifecycle of a web request from browser to server and back, including DNS, TCP, TLS, HTTP, and response rendering",
        "写一篇详细的论文，讨论大语言模型在自然语言处理中的最新进展，包括预训练方法、微调策略、以及对下游任务的影响",
        "详细解释Kubernetes的架构设计，包括Pod、Service、Deployment等核心概念",
        "Analyze the evolution of cloud computing from IaaS to serverless, covering the architectural shifts, trade-offs, and future directions",
    ]

    requests: list[dict] = []
    for _ in range(n):
        r = rng.random()
        if r < 0.3:
            cat, prompts, max_range = "short", short_prompts, (20, 80)
        elif r < 0.7:
            cat, prompts, max_range = "medium", medium_prompts, (100, 300)
        else:
            cat, prompts, max_range = "long", long_prompts, (400, 900)

        max_tok = rng.randint(*max_range)
        actual = int(max_tok * rng.uniform(0.4, 0.95))
        requests.append({
            "body": {
                "messages": [{"role": "user", "content": rng.choice(prompts)}],
                "max_tokens": max_tok,
            },
            "category": cat,
            "actual_tokens": actual,
            "arrival": 0.0,  # set later
        })
    return requests


def assign_arrivals(requests: list[dict], rate: float, rng: random.Random) -> None:
    """Assign Poisson-distributed arrival times."""
    for req in requests:
        req["arrival"] = 0.0  # will be overwritten
    t = 0.0
    for req in requests:
        t += rng.expovariate(rate)
        req["arrival"] = t


# ── Simulation engine ─────────────────────────────────────────────────────


def simulate(workload: list[dict], policy: str, predictor=None) -> list[dict]:
    """Simulate single-server queue with the given scheduling policy.

    Policies:
      fcfs      — first come first served (arrival order)
      heuristic — HeuristicPredictor sorts by predicted length
      ltr       — ML predictor sorts by predicted length
      oracle    — sorts by actual output length (upper bound)
    """
    items = []
    for req in workload:
        pred = req["actual_tokens"]  # default: oracle
        if policy == "fcfs":
            pred = float(items.__len__() + 1)  # keep arrival order
        elif policy == "heuristic":
            pred = HeuristicPredictor().predict(req["body"])
        elif policy == "ltr" and predictor is not None:
            pred = predictor.predict(req["body"])

        items.append({
            **req,
            "predicted": float(pred),
        })

    # Sort by policy
    if policy == "fcfs":
        pass  # keep arrival order
    elif policy == "oracle":
        items.sort(key=lambda x: x["actual_tokens"])
    else:
        items.sort(key=lambda x: x["predicted"])

    server_free = 0.0
    results = []
    for item in items:
        processing = item["actual_tokens"] / TOK_PER_SEC
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


# ── Metrics ────────────────────────────────────────────────────────────────


def percentile(arr: list[float], p: float) -> float:
    if not arr:
        return 0.0
    s = sorted(arr)
    idx = min(int(len(s) * p / 100), len(s) - 1)
    return s[idx]


def compute_metrics(results: list[dict], label: str) -> dict[str, Any]:
    latencies = [r["latency"] for r in results]
    by_cat: dict[str, list[float]] = defaultdict(list)
    for r in results:
        by_cat[r["category"]].append(r["latency"])

    return {
        "strategy": label,
        "n": len(results),
        "mean": round(sum(latencies) / len(latencies), 3),
        "p50": round(percentile(latencies, 50), 3),
        "p90": round(percentile(latencies, 90), 3),
        "p99": round(percentile(latencies, 99), 3),
        "short_mean": round(sum(by_cat["short"]) / max(len(by_cat["short"]), 1), 3),
        "medium_mean": round(sum(by_cat["medium"]) / max(len(by_cat["medium"]), 1), 3),
        "long_mean": round(sum(by_cat["long"]) / max(len(by_cat["long"]), 1), 3),
        "throughput": round(len(results) / max(latencies[-1] if latencies else 1, 0.001), 2),
    }


def hol_blocking(results: list[dict]) -> float:
    """Average wait time of short requests that arrived while a long request was being served."""
    # Find all long requests
    long_intervals = [(r["start"], r["complete"]) for r in results if r["category"] == "long"]
    # Find short requests that arrived during a long request's service
    blocked_waits = []
    for r in results:
        if r["category"] != "short":
            continue
        for ls, lc in long_intervals:
            if ls <= r["arrival"] < lc:
                blocked_waits.append(r["wait"])
                break
    return round(sum(blocked_waits) / max(len(blocked_waits), 1), 3)


# ── Printing ───────────────────────────────────────────────────────────────


def print_comparison(all_metrics: list[dict], hol_data: dict[str, float]) -> None:
    print(f"\n{'Strategy':<18} | {'Mean':>7} | {'P50':>7} | {'P90':>7} | {'Short':>7} | {'Med':>7} | {'Long':>7}")
    print("-" * 85)
    for m in all_metrics:
        print(f"{m['strategy']:<18} | {m['mean']:>6.2f}s | {m['p50']:>6.2f}s | {m['p90']:>6.2f}s "
              f"| {m['short_mean']:>6.2f}s | {m['medium_mean']:>6.2f}s | {m['long_mean']:>6.2f}s")

    print(f"\nHOL Blocking (avg wait of short requests behind long):")
    parts = []
    for name, val in hol_data.items():
        parts.append(f"  {name}: {val:.2f}s")
    print(" |".join(parts))

    # Improvement ratios
    if len(all_metrics) >= 2:
        fcfs = all_metrics[0]
        for m in all_metrics[1:]:
            if fcfs["mean"] > 0:
                speedup = fcfs["mean"] / m["mean"]
                short_speedup = fcfs["short_mean"] / m["short_mean"] if m["short_mean"] > 0 else 0
                print(f"\n{m['strategy']} vs FCFS: mean {speedup:.2f}x, short {short_speedup:.2f}x")


def run_single(n: int, rate: float, seed: int, model_path: str | None, tok_per_sec: float = TOK_PER_SEC) -> None:
    global TOK_PER_SEC
    TOK_PER_SEC = tok_per_sec
    rng = random.Random(seed)
    workload = generate_workload(n, rng)
    assign_arrivals(workload, rate, rng)

    cats = defaultdict(int)
    for r in workload:
        cats[r["category"]] += 1
    print(f"=== Stress Test: {n} requests, rate={rate}/s "
          f"(short={cats['short']}, med={cats['medium']}, long={cats['long']}) ===")

    predictor = None
    if model_path:
        try:
            from gateway.app.predictor_ml import LTRPredictor
            predictor = LTRPredictor(model_path)
            print(f"LTR model loaded: {model_path}")
        except Exception as e:
            print(f"Warning: could not load LTR model ({e}), skipping LTR strategy")

    strategies = [
        ("FCFS", "fcfs"),
        ("Heuristic SJF", "heuristic"),
        ("Oracle SJF", "oracle"),
    ]
    if predictor:
        strategies.insert(2, ("LTR SJF (Ours)", "ltr"))

    all_metrics = []
    hol_data = {}
    for name, policy in strategies:
        results = simulate(workload, policy, predictor)
        m = compute_metrics(results, name)
        all_metrics.append(m)
        hol_data[name] = hol_blocking(results)

    print_comparison(all_metrics, hol_data)

    # Save
    out = {
        "params": {"n": n, "rate": rate, "tok_per_sec": TOK_PER_SEC, "seed": seed},
        "results": all_metrics,
        "hol_blocking": hol_data,
    }
    fname = f"stress_test_r{rate}_n{n}.json"
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to {fname}")


# ── Main ──────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="Stress Test: FCFS vs SJF")
    parser.add_argument("-n", "--num-requests", type=int, default=300)
    parser.add_argument("--rate", type=float, default=32.0, help="Arrival rate (req/s)")
    parser.add_argument("--rates", type=str, default=None,
                        help="Comma-separated rates to sweep, e.g. 10,20,40,64")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--model", type=str, default="ltr_model.pt",
                        help="Path to trained LTR model (set '' to skip)")
    parser.add_argument("--tok-per-sec", type=float, default=TOK_PER_SEC)
    args = parser.parse_args()

    model_path = args.model if args.model else None

    if args.rates:
        rates = [float(r.strip()) for r in args.rates.split(",")]
        for rate in rates:
            run_single(args.num_requests, rate, args.seed, model_path, args.tok_per_sec)
            print("\n" + "=" * 85 + "\n")
    else:
        run_single(args.num_requests, args.rate, args.seed, model_path, args.tok_per_sec)


if __name__ == "__main__":
    main()
