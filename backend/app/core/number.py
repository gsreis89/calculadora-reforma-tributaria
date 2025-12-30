# backend/app/core/number.py
from __future__ import annotations

import re

def parse_money(v) -> float:
    """
    Converte valores string/num para float, suportando:
      - 1000.00
      - 1,000.00
      - 1000,00
      - 1.000,00
    Regra:
      - Se tiver . e , => assume pt-BR (1.234,56) => remove '.' e troca ',' por '.'
      - Se tiver só ',' => assume decimal => troca ',' por '.'
      - Se tiver só '.' => assume decimal padrão
    """
    if v is None:
        return 0.0

    if isinstance(v, (int, float)):
        return float(v)

    s = str(v).strip()
    if not s:
        return 0.0

    # remove espaços e símbolos
    s = s.replace("R$", "").strip()
    s = re.sub(r"\s+", "", s)

    has_dot = "." in s
    has_comma = "," in s

    if has_dot and has_comma:
        # 1.234,56 (pt-BR)
        s = s.replace(".", "").replace(",", ".")
    elif has_comma and not has_dot:
        # 1234,56
        s = s.replace(",", ".")
    # else: 1234.56 ou 1234

    try:
        return float(s)
    except Exception:
        return 0.0
