"""Contratos territoriais do Meningites VNext.

Compatibilidade interna com o legado SES-MT: município em IBGE-6.
O código original deve permanecer na evidência quando necessário; não se infere
código por nome de município.
"""
from __future__ import annotations

import re
from typing import Any


def normalize_municipality_code(value: Any) -> str:
    if value is None:
        return ""
    raw = str(value).strip()
    if raw.casefold() in {"", "nan", "none", "<na>"}:
        return ""
    digits = re.sub(r"\D", "", raw)
    if len(digits) >= 7:
        digits = digits[:6]
    return digits if len(digits) == 6 else ""


def municipality_codes_equivalent(left: Any, right: Any) -> bool:
    a = normalize_municipality_code(left)
    b = normalize_municipality_code(right)
    return bool(a and b and a == b)
