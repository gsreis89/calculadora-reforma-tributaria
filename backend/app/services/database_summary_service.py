# backend/app/services/database_summary_service.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any, Set

import csv


@dataclass
class DatasetSummary:
    exists: bool
    path: str
    rows: int

    min_date: Optional[str]
    max_date: Optional[str]

    ufs_origem: list[str]
    ufs_destino: list[str]

    receita_total: float
    icms_total: float
    pis_total: float
    cofins_total: float


def _to_float(v: str) -> float:
    try:
        return float(str(v).replace(",", "."))
    except Exception:
        return 0.0


def build_summary(csv_path: Path) -> DatasetSummary:
    if not csv_path.exists():
        return DatasetSummary(
            exists=False,
            path=str(csv_path),
            rows=0,
            min_date=None,
            max_date=None,
            ufs_origem=[],
            ufs_destino=[],
            receita_total=0.0,
            icms_total=0.0,
            pis_total=0.0,
            cofins_total=0.0,
        )

    min_date: Optional[str] = None
    max_date: Optional[str] = None
    ufo: Set[str] = set()
    ufd: Set[str] = set()

    receita_total = 0.0
    icms_total = 0.0
    pis_total = 0.0
    cofins_total = 0.0
    rows = 0

    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows += 1

            dhemi = (row.get("dhemi") or "").strip()
            uf = (row.get("uf") or "").strip().upper()
            uf_dest = (row.get("uf_dest") or "").strip().upper()

            if uf:
                ufo.add(uf)
            if uf_dest:
                ufd.add(uf_dest)

            # datas no formato YYYY-MM-DD: compare lexicográfico funciona
            if dhemi:
                if min_date is None or dhemi < min_date:
                    min_date = dhemi
                if max_date is None or dhemi > max_date:
                    max_date = dhemi

            vprod = _to_float(row.get("vprod") or "0")
            vicms = _to_float(row.get("vicms_icms") or "0")
            vpis = _to_float(row.get("vpis") or "0")
            vcof = _to_float(row.get("vcofins") or "0")

            receita_total += vprod
            icms_total += vicms
            pis_total += vpis
            cofins_total += vcofins if (vcofins := vcof) else 0.0  # compat python

    return DatasetSummary(
        exists=True,
        path=str(csv_path),
        rows=rows,
        min_date=min_date,
        max_date=max_date,
        ufs_origem=sorted(list(ufo)),
        ufs_destino=sorted(list(ufd)),
        receita_total=round(receita_total, 2),
        icms_total=round(icms_total, 2),
        pis_total=round(pis_total, 2),
        cofins_total=round(cofins_total, 2),
    )
