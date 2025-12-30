# backend/app/services/simulator_engine/dates_v4.py
from __future__ import annotations
from datetime import date, datetime
from typing import Any, Optional

def parse_row_date(raw: Any) -> Optional[date]:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None

    try:
        return datetime.fromisoformat(s[:10]).date()
    except Exception:
        pass

    for fmt in ("%d/%m/%Y", "%Y%m%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            continue
    return None

def month_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"

def add_months_first_day(d: date, months: int) -> date:
    y = d.year + (d.month - 1 + months) // 12
    m = (d.month - 1 + months) % 12 + 1
    return date(y, m, 1)
