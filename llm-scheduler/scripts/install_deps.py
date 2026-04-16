#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Install all Python dependencies for local (non-Docker) development.
Run from the llm-scheduler/ project root.

Usage:
    python scripts/install_deps.py
"""
import subprocess
import sys
import os

# Fix Windows GBK terminal encoding
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def pip(*args):
    subprocess.check_call([sys.executable, "-m", "pip", "install", *args])


# Install shared package — try editable first, fall back to plain install
print("[*] Installing shared package (pydantic)...")
try:
    pip("-e", os.path.join(BASE, "shared"))
    print("[OK] Installed shared package as editable")
except subprocess.CalledProcessError:
    print("[*] Editable install failed, installing pydantic directly...")
    pip("pydantic>=2.0", "pydantic-settings>=2.0")
    print("[OK] pydantic installed; shared/ will be imported via PYTHONPATH")

# Install all service dependencies in one shot (they overlap a lot)
print("\n[*] Installing all service dependencies...")
pip(
    "fastapi>=0.111.0",
    "uvicorn[standard]>=0.29.0",
    "httpx>=0.27.0",
    "aiosqlite>=0.20.0",
    "pydantic-settings>=2.0.0",
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    "bcrypt<4.0",          # passlib 1.7.4 is incompatible with bcrypt>=4
    "python-multipart>=0.0.9",
)

print("\n[OK] All dependencies installed.")
print("     Run: python scripts/start_local.py")
