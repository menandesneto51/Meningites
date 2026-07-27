# -*- coding: utf-8 -*-
"""Carrega Meningites/.env para os.environ (sem sobrescrever o que já estiver definido)."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load_meningites_env(force: bool = False) -> Path | None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return None
    for raw in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if not key:
            continue
        if force or key not in os.environ or os.environ.get(key, "") == "":
            os.environ[key] = val
    return env_path
