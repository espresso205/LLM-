#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
并发测试脚本 — 观察不同负载均衡策略下的节点分配情况

Usage:
    python scripts/benchmark.py
    python scripts/benchmark.py --requests 20
    python scripts/benchmark.py --url http://192.168.1.100:8080
"""
import argparse
import time
import sys
import io
import os
import sqlite3
import threading
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# Fix Windows GBK terminal encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── 配置 ──────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATEWAY = "http://localhost:8080"
SCHEDULER = "http://localhost:8001"
USERNAME = "admin"
PASSWORD = "admin123"
REQUESTS = 10
INTERNAL_TOKEN = "internal-secret-change-me"
DB_PATH = os.path.join(BASE_DIR, "gateway", "gateway.db")

# 50 条各不相同的测试提问
PROMPTS = [
    "请用一句话解释什么是人工智能",
    "写一个关于春天的五言绝句",
    "Python中列表和元组有什么区别？",
    "请推荐三部科幻电影并简述理由",
    "用简单的语言解释量子纠缠",
    "写一首关于程序员的打油诗",
    "HTTP和HTTPS的主要区别是什么？",
    "请用比喻的方式解释什么是机器学习",
    "列举五种健康早餐的建议",
    "什么是递归？请用一个生活中的例子说明",
    "解释什么是区块链，用通俗的语言",
    "写一句励志的名言并解读其含义",
    "TCP和UDP协议有什么区别？",
    "请用三句话描述太阳系",
    "什么是微服务架构？它的优缺点是什么？",
    "写一个关于夏天的小段子",
    "Git中merge和rebase有什么区别？",
    "请解释什么是API，举一个生活中的例子",
    "列举三种常见的排序算法并比较效率",
    "什么是设计模式？请举一个例子",
    "用一句话概括相对论的核心思想",
    "写一首关于秋天的现代诗",
    "Docker容器和虚拟机有什么区别？",
    "请推荐三本值得一读的书籍",
    "什么是冒泡排序？请简述其原理",
    "解释什么是云计算，举三个应用场景",
    "写一句关于时间管理的格言",
    "SQL中INNER JOIN和LEFT JOIN有什么区别？",
    "请用三个关键词概括文艺复兴",
    "什么是RESTful API？有哪些设计原则？",
    "写一段鼓励学习编程的话",
    "解释什么是深度学习，和机器学习有什么关系",
    "请列举五种常见的编程语言及其用途",
    "什么是数据库索引？为什么能加速查询？",
    "写一个关于冬天的成语故事梗概",
    "JSON和XML有什么区别？各适合什么场景？",
    "请用一句话解释什么是量子计算",
    "什么是CI/CD？它在软件开发中的作用是什么？",
    "列举三种提高代码质量的方法",
    "解释什么是负载均衡，常见的策略有哪些",
    "写一个关于猫的趣味小故事",
    "什么是缓存？为什么需要缓存？",
    "请解释什么是容器编排，Kubernetes解决了什么问题",
    "列举五种常见的网络攻击类型",
    "什么是函数式编程？它有什么特点？",
    "写一句关于团队合作的名言",
    "解释什么是消息队列，它在系统中的作用",
    "请用三句话介绍中国四大发明之一",
    "什么是敏捷开发？它的核心价值观是什么？",
]

# ── 颜色输出 ──────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

print_lock = threading.Lock()


def safe_print(*args, **kwargs):
    with print_lock:
        print(*args, **kwargs)


# ── 工具函数 ──────────────────────────────────────────
def login(base_url):
    """登录获取 JWT token"""
    r = requests.post(f"{base_url}/auth/login",
                      data={"username": USERNAME, "password": PASSWORD},
                      timeout=10)
    r.raise_for_status()
    return r.json()["access_token"]


def get_strategy(sched_url):
    """获取当前调度策略"""
    try:
        r = requests.get(f"{sched_url}/api/strategy", timeout=5,
                         headers={"x-internal-token": INTERNAL_TOKEN})
        r.raise_for_status()
        d = r.json()
        return d.get("current", "unknown"), d.get("available", [])
    except Exception:
        return "unknown", []


def set_strategy(sched_url, strategy):
    """切换调度策略"""
    r = requests.put(f"{sched_url}/api/strategy", json={"strategy": strategy}, timeout=5,
                     headers={"x-internal-token": INTERNAL_TOKEN})
    r.raise_for_status()
    return r.json()


def check_nodes(sched_url):
    """检查节点状态，返回健康节点数"""
    try:
        r = requests.get(f"{sched_url}/api/nodes", timeout=5,
                         headers={"x-internal-token": INTERNAL_TOKEN})
        nodes = r.json()
        healthy = [n for n in nodes if n.get("status") == "healthy"]
        print(f"  {DIM}节点状态:{RESET}", end="")
        for n in nodes:
            color = GREEN if n["status"] == "healthy" else RED
            conns = n.get("active_connections", 0)
            print(f"  {color}{n['node_id']}({n['status']}, {conns}conns){RESET}", end="")
        print()
        return len(healthy)
    except Exception:
        print(f"  {RED}无法获取节点状态{RESET}")
        return 0


def get_db_node_counts(before_count):
    """从 gateway 数据库查询本轮新增请求的节点分配"""
    try:
        db = sqlite3.connect(DB_PATH)
        rows = db.execute(
            "SELECT node_id, COUNT(*) as cnt FROM request_log "
            "WHERE rowid > ? GROUP BY node_id", (before_count,)
        ).fetchall()
        db.close()
        return {r[0] or "error": r[1] for r in rows}
    except Exception:
        return {}


def send_request(base_url, token, prompt, idx):
    """发送单条推理请求，返回结果字典"""
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "model": "auto",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 128,
        "temperature": 0.7,
    }
    start = time.time()
    try:
        r = requests.post(f"{base_url}/v1/chat/completions",
                          json=payload, headers=headers, timeout=180)
        elapsed = time.time() - start
        if r.status_code == 200:
            data = r.json()
            tokens = data.get("usage", {}).get("total_tokens", "?")
            reply = data["choices"][0]["message"]["content"][:60].replace("\n", " ")
            return {
                "idx": idx, "status": "ok",
                "latency": elapsed, "tokens": tokens,
                "reply": reply, "prompt": prompt[:30],
            }
        else:
            return {
                "idx": idx, "status": f"HTTP {r.status_code}",
                "latency": elapsed, "tokens": 0,
                "reply": r.text[:60], "prompt": prompt[:30],
            }
    except Exception as e:
        elapsed = time.time() - start
        return {
            "idx": idx, "status": "error",
            "latency": elapsed, "tokens": 0,
            "reply": str(e)[:60], "prompt": prompt[:30],
        }


def run_round(base_url, token, prompts, label, batch_size=5, batch_delay=2):
    """分批发送请求，避免压垮小模型 vLLM"""
    n = len(prompts)
    # 记录当前数据库行数，用于后续查询本轮新增记录
    db = sqlite3.connect(DB_PATH)
    before_count = db.execute("SELECT COUNT(*) FROM request_log").fetchone()[0]
    db.close()

    print()
    print(f"{BOLD}{'='*60}")
    print(f"  策略: {YELLOW}{label}{RESET}{BOLD}    总请求: {CYAN}{n}{RESET}{BOLD}    批次: {CYAN}{batch_size}/批, 间隔{batch_delay}s{RESET}")
    print(f"{'='*60}{RESET}")
    print()
    print(f"  {'#':>2}  {'耗时':>8}  {'Tokens':>7}  {'状态':<8}  {'提问摘要'}")
    print(f"  {'─'*2}  {'─'*8}  {'─'*7}  {'─'*8}  {'─'*24}")

    results = []
    wall_start = time.time()
    batches = [prompts[i:i+batch_size] for i in range(0, n, batch_size)]

    for bi, batch in enumerate(batches):
        if bi > 0:
            time.sleep(batch_delay)
        with ThreadPoolExecutor(max_workers=len(batch)) as pool:
            offset = bi * batch_size
            futures = {
                pool.submit(send_request, base_url, token, p, offset + j): j
                for j, p in enumerate(batch)
            }
            for future in as_completed(futures):
                res = future.result()
                results.append(res)

                status_color = GREEN if res["status"] == "ok" else RED
                safe_print(
                    f"  {res['idx']:>2}  "
                    f"{res['latency']:>7.2f}s  "
                    f"{res['tokens']:>7}  "
                    f"{status_color}{res['status']:<8}{RESET} "
                    f"{DIM}{res['prompt']}{RESET}"
                )

    wall_time = time.time() - wall_start

    # ── 从数据库查节点分配 ──
    time.sleep(1)  # 等 DB 写完
    node_counts = get_db_node_counts(before_count)

    results.sort(key=lambda r: r["idx"])
    ok = [r for r in results if r["status"] == "ok"]

    print()
    print(f"  {BOLD}── 本轮统计 ──{RESET}")
    print(f"  总耗时: {wall_time:.2f}s   成功: {GREEN}{len(ok)}/{n}{RESET}")

    if ok:
        avg_lat = sum(r["latency"] for r in ok) / len(ok)
        max_lat = max(r["latency"] for r in ok)
        min_lat = min(r["latency"] for r in ok)
        total_tok = sum(r["tokens"] for r in ok if isinstance(r["tokens"], (int, float)))
        print(f"  延迟: 平均 {avg_lat:.2f}s / 最大 {max_lat:.2f}s / 最小 {min_lat:.2f}s")
        print(f"  总 Tokens: {total_tok}")

    total_db = sum(node_counts.values())
    print(f"  {BOLD}节点分配 (数据库):{RESET}")
    for node, count in sorted(node_counts.items()):
        bar = "█" * count
        pct = count / max(total_db, 1) * 100
        print(f"    {BLUE}{node:<10}{RESET}  {YELLOW}{bar}{RESET}  {count} 次 ({pct:.0f}%)")

    return node_counts, results


# ── 主流程 ────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="LLM-Scheduler 并发负载测试")
    parser.add_argument("--url", default=GATEWAY, help=f"Gateway 地址 (默认: {GATEWAY})")
    parser.add_argument("--sched", default=SCHEDULER, help=f"Scheduler 地址 (默认: {SCHEDULER})")
    parser.add_argument("-n", "--requests", type=int, default=REQUESTS, help=f"并发请求数 (默认: {REQUESTS})")
    parser.add_argument("--strategy", choices=["all", "round_robin", "least_connections", "weighted"],
                        default="all", help="测试策略 (默认: all = 逐个测试全部)")
    args = parser.parse_args()

    base = args.url.rstrip("/")
    sched = args.sched.rstrip("/")

    print(f"\n{BOLD}{'='*60}")
    print(f"  LLM-Scheduler 并发负载测试")
    print(f"{'='*60}{RESET}")
    print(f"  Gateway:   {base}")
    print(f"  Scheduler: {sched}")
    print(f"  并发数:    {args.requests}")

    # 补齐 prompts 到请求数
    prompts = PROMPTS[:]
    while len(prompts) < args.requests:
        prompts.append(f"请简短回答：第 {len(prompts)+1} 个问题的测试内容是什么？")
    prompts = prompts[:args.requests]

    # 登录
    print(f"\n  {DIM}登录中...{RESET}", end=" ", flush=True)
    try:
        token = login(base)
        print(f"{GREEN}OK{RESET}")
    except Exception as e:
        print(f"{RED}失败{RESET}")
        print(f"  {RED}登录错误: {e}{RESET}")
        return

    # 查询当前策略
    current, available = get_strategy(sched)
    print(f"  当前策略: {YELLOW}{current}{RESET}")
    print(f"  可用策略: {', '.join(available)}")

    # 确定要测试的策略列表
    if args.strategy == "all":
        strategies = available if available else ["round_robin", "least_connections", "weighted"]
    else:
        strategies = [args.strategy]

    all_node_counts = {}

    for i, strat in enumerate(strategies):
        # 切换策略
        try:
            set_strategy(sched, strat)
            print(f"\n  {DIM}已切换策略 → {strat}{RESET}")
            time.sleep(0.5)
        except Exception as e:
            print(f"\n  {RED}切换策略失败: {e}{RESET}")
            continue

        # 如果测试多轮，轮间等一会让节点恢复
        if i > 0:
            print(f"  {DIM}等待 10 秒让节点恢复...{RESET}")
            time.sleep(10)

        healthy = check_nodes(sched)
        if healthy == 0:
            print(f"  {RED}没有健康节点，跳过本轮{RESET}")
            continue

        node_counts, results = run_round(base, token, prompts, strat)
        all_node_counts[strat] = node_counts

    # ── 总结 ──
    if len(all_node_counts) > 1:
        print(f"\n{BOLD}{'='*60}")
        print(f"  对比总结")
        print(f"{'='*60}{RESET}\n")
        print(f"  {'策略':<20} {'总请求':>6}  {'节点分布'}")
        print(f"  {'─'*20} {'─'*6}  {'─'*30}")
        for strat, counts in all_node_counts.items():
            total = sum(counts.values())
            dist = "  ".join(f"{BLUE}{n}:{c}{RESET}" for n, c in sorted(counts.items()))
            print(f"  {strat:<20} {total:>5}  {dist}")

    print(f"\n{DIM}  测试完成{RESET}\n")


if __name__ == "__main__":
    main()
