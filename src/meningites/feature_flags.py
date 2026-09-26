"""Feature flags do Meningites VNext."""
from __future__ import annotations

import os


def enabled(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "sim", "yes", "on"}
