#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Local development startup script.
Starts all 4 services in separate processes with correct working directories.

Usage:
    python scripts/start_local.py

Prerequisites:
    python scripts/install_deps.py
"""
import subprocess
import sys
import os
import time
import signal
import socket

# Fix Windows GBK terminal encoding
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def port_in_use(port):
    """Check if a port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0

SERVICES = [
    {
        "name": "Scheduler   :8001",
        "cwd": os.path.join(BASE, "scheduler"),
        "cmd": [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"],
    },
    {
        "name": "Infer Node-1:8003",
        "cwd": os.path.join(BASE, "inference-node"),
        "cmd": [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003", "--reload"],
        "env": {
            "NODE_ID": "node-1",
            "NODE_HOST": "localhost",
            "NODE_PORT": "8003",
            "VLLM_URL": "http://172.17.77.32:8000",
        },
    },
    {
        "name": "Infer Node-2:8004",
        "cwd": os.path.join(BASE, "inference-node"),
        "cmd": [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8004", "--reload"],
        "env": {
            "NODE_ID": "node-2",
            "NODE_HOST": "localhost",
            "NODE_PORT": "8004",
            "VLLM_URL": "http://172.17.77.32:8005",
            "DATABASE_URL": "node2.db",
        },
    },
    {
        "name": "Gateway     :8080",
        "cwd": os.path.join(BASE, "gateway"),
        "cmd": [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"],
    },
    {
        "name": "Monitoring  :8002",
        "cwd": os.path.join(BASE, "monitoring"),
        "cmd": [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002", "--reload"],
    },
]

procs = []


def shutdown(sig, frame):
    print("\n[*] Shutting down all services...")
    for p in procs:
        try:
            p.terminate()
        except Exception:
            pass
    # Wait for processes to actually exit
    for p in procs:
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            p.kill()
    # On Windows, kill the entire process tree (--reload spawns children)
    if sys.platform == "win32":
        for p in procs:
            try:
                subprocess.call(["taskkill", "/F", "/T", "/PID", str(p.pid)],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
    print("[*] All services stopped.")
    sys.exit(0)


signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)

# ── Pre-flight: check for port conflicts ──
_used_ports = {}
for svc in SERVICES:
    port = int(svc["cmd"][svc["cmd"].index("--port") + 1])
    if port_in_use(port):
        _used_ports[svc["name"]] = port

if _used_ports:
    print()
    print("  ⚠  端口冲突！以下端口已被占用：")
    for name, port in _used_ports.items():
        print(f"     {name}  →  :{port}")
    print()
    print("  请先关闭占用端口的进程，再重新运行。")
    print("  提示: netstat -ano | findstr :端口号  可查找占用进程")
    print()
    sys.exit(1)

print("=" * 50)
print("  LLM Scheduler System - Local Dev Mode")
print("=" * 50)

for svc in SERVICES:
    env = os.environ.copy()
    env["PYTHONPATH"] = BASE  # makes 'shared' importable as a package
    if "env" in svc:
        env.update(svc["env"])
    p = subprocess.Popen(svc["cmd"], cwd=svc["cwd"], env=env)
    procs.append(p)
    print(f"  [OK] {svc['name']} started (PID {p.pid})")
    time.sleep(1.5)  # stagger startup so scheduler is ready before nodes connect

print()
print("  Services:")
print("    Gateway (main UI):  http://localhost:8080")
print("    Scheduler UI:      http://localhost:8001")
print("    Monitoring UI:     http://localhost:8002")
print("    Inference Node-1:  http://localhost:8003 (Qwen3-0.6B)")
print("    Inference Node-2:  http://localhost:8004 (TinyLlama-1.1B)")
print("    Inference Node-3:  http://localhost:8007 (Qwen2.5-7B Remote)")
print()
print("  Default login: admin / admin123")
print()
print("  Press Ctrl+C to stop all services.")
print("=" * 50)

while True:
    for p in procs:
        ret = p.poll()
        if ret is not None:
            print(f"  [!] Process {p.pid} exited with code {ret}")
    time.sleep(2)
