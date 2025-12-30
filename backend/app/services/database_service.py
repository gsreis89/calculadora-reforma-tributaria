# backend/app/services/database_service.py
from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from app.core.dataset import DATASET_PATH, ensure_data_dir
from app.core.number import parse_money

REQUIRED_COLUMNS = [
    "dhemi",
    "uf",
    "uf_dest",
    "vprod",
    "vicms_icms",
    "vpis",
    "vcofins",
]

OPTIONAL_COLUMNS = ["ncm", "produto", "cfop", "movimento"]


def _sniff_delimiter(sample: str) -> str:
    """
    Detecta delimitador do CSV (',', ';', '\\t'). Fallback: ';'
    """
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=[",", ";", "\t"])
        return dialect.delimiter
    except Exception:
        return ";"


def clear_dataset() -> None:
    """
    Remove o arquivo de dataset importado.
    """
    ensure_data_dir()
    if DATASET_PATH.exists():
        DATASET_PATH.unlink()


def _normalize_header(h: str) -> str:
    """
    Normaliza cabeçalhos: remove BOM, trim, lowercase.
    """
    if not h:
        return ""
    return h.replace("\ufeff", "").strip().lower()


def _to_float(v) -> float:
    """
    Parser numérico único e consistente para todo o backend.
    Evita bugs do tipo 280.00 virar 28000.
    """
    return parse_money(v)


def _parse_date(v: str) -> Optional[datetime]:
    """
    Suporta:
      - YYYY-MM-DD
      - DD/MM/YYYY
      - YYYYMMDD
    """
    if not v:
        return None
    s = str(v).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y%m%d"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            continue
    return None


def validate_csv_columns(header: List[str]) -> Tuple[bool, List[str]]:
    normalized = [_normalize_header(h) for h in header]
    missing = [c for c in REQUIRED_COLUMNS if c not in normalized]
    return (len(missing) == 0, missing)


def import_csv_bytes(file_bytes: bytes) -> int:
    """
    Importa CSV (qualquer delimitador detectado), valida colunas,
    normaliza header e regrava dataset interno SEMPRE em ';'
    (forma canônica do projeto).
    """
    ensure_data_dir()

    text = file_bytes.decode("utf-8", errors="replace")
    sample = text[:50_000]
    delimiter = _sniff_delimiter(sample)

    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    if reader.fieldnames is None:
        raise ValueError("CSV sem cabeçalho (header).")

    # valida colunas obrigatórias (normalizadas)
    header_norm = [_normalize_header(h) for h in reader.fieldnames]
    ok, missing = validate_csv_columns(header_norm)
    if not ok:
        raise ValueError(
            f"CSV inválido. Faltam colunas obrigatórias: {', '.join(missing)}"
        )

    # mapeia nome original -> normalizado
    field_map: Dict[str, str] = {name: _normalize_header(name) for name in reader.fieldnames}
    output_fields = REQUIRED_COLUMNS + OPTIONAL_COLUMNS

    imported = 0
    with open(DATASET_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=output_fields, delimiter=";")
        writer.writeheader()

        for row in reader:
            normalized_row: Dict[str, str] = {}
            for k, v in row.items():
                nk = field_map.get(k, _normalize_header(k))
                normalized_row[nk] = (v or "").strip()

            out = {col: normalized_row.get(col, "") for col in output_fields}
            writer.writerow(out)
            imported += 1

    return imported


def get_status() -> dict:
    """
    Retorna status do dataset.
    """
    ensure_data_dir()

    if not DATASET_PATH.exists():
        return {"exists": False, "path": str(DATASET_PATH), "rows": 0}

    with open(DATASET_PATH, "r", encoding="utf-8", newline="") as f:
        rows = max(sum(1 for _ in f) - 1, 0)

    return {"exists": True, "path": str(DATASET_PATH), "rows": rows}


def get_summary() -> dict:
    """
    Resume dataset:
      - período min/max (dhemi)
      - ufs origem/destino
      - somatórios: receita (vprod) e tributos
    """
    ensure_data_dir()

    if not DATASET_PATH.exists():
        return {
            "exists": False,
            "path": str(DATASET_PATH),
            "rows": 0,
            "min_date": None,
            "max_date": None,
            "ufs_origem": [],
            "ufs_destino": [],
            "receita_total": 0.0,
            "icms_total": 0.0,
            "pis_total": 0.0,
            "cofins_total": 0.0,
        }

    min_dt: Optional[datetime] = None
    max_dt: Optional[datetime] = None
    ufs_o = set()
    ufs_d = set()
    receita = 0.0
    icms = 0.0
    pis = 0.0
    cofins = 0.0

    with open(DATASET_PATH, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        rows = 0

        for row in reader:
            rows += 1

            dt = _parse_date(row.get("dhemi", ""))
            if dt:
                min_dt = dt if min_dt is None else min(min_dt, dt)
                max_dt = dt if max_dt is None else max(max_dt, dt)

            uf = (row.get("uf") or "").strip().upper()
            uf_dest = (row.get("uf_dest") or "").strip().upper()

            if uf:
                ufs_o.add(uf)
            if uf_dest:
                ufs_d.add(uf_dest)

            receita += _to_float(row.get("vprod"))
            icms += _to_float(row.get("vicms_icms"))
            pis += _to_float(row.get("vpis"))
            cofins += _to_float(row.get("vcofins"))

    return {
        "exists": True,
        "path": str(DATASET_PATH),
        "rows": rows,
        "min_date": min_dt.date().isoformat() if min_dt else None,
        "max_date": max_dt.date().isoformat() if max_dt else None,
        "ufs_origem": sorted(list(ufs_o)),
        "ufs_destino": sorted(list(ufs_d)),
        "receita_total": float(receita),
        "icms_total": float(icms),
        "pis_total": float(pis),
        "cofins_total": float(cofins),
    }


def get_template_csv_bytes() -> bytes:
    """
    Template canônico do projeto (delimitador ';').
    """
    header = REQUIRED_COLUMNS + OPTIONAL_COLUMNS
    content = ";".join(header) + "\n"
    content += "2024-01-01;AM;SP;1000.00;180.00;16.50;76.00;12345678;PRODUTO X;5102;SAIDA\n"
    return content.encode("utf-8")
