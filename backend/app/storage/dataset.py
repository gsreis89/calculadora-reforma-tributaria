# backend/app/storage/dataset.py
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional, Iterable

from app.core.dataset import DATASET_PATH, ensure_data_dir
from app.core.number import parse_money


@dataclass
class Filters:
    periodo_inicio: date
    periodo_fim: date
    uf_origem: Optional[str] = None
    uf_destino: Optional[str] = None
    ncm: Optional[str] = None
    produto: Optional[str] = None
    cfop: Optional[str] = None


# ------------------------
# Cache persistente (server-friendly)
# ------------------------

def _cache_paths(csv_path: Path) -> tuple[Path, Path, Path]:
    """Retorna (pickle_path, parquet_path, meta_path)."""
    pkl_path = csv_path.with_suffix(csv_path.suffix + ".pkl")
    pq_path = csv_path.with_suffix(csv_path.suffix + ".parquet")
    meta_path = csv_path.with_suffix(csv_path.suffix + ".meta.json")
    return pkl_path, pq_path, meta_path


def _file_fingerprint(path: Path) -> dict:
    st = path.stat()
    return {
        "mtime_ns": int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9))),
        "size": int(st.st_size),
    }


def _read_meta(meta_path: Path) -> Optional[dict]:
    try:
        if not meta_path.exists():
            return None
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_meta(meta_path: Path, meta: dict) -> None:
    try:
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        # se falhar, não bloqueia a execução
        pass


def _cache_is_fresh(csv_path: Path, meta_path: Path) -> bool:
    meta = _read_meta(meta_path)
    if not meta or "csv" not in meta:
        return False

    try:
        current = _file_fingerprint(csv_path)
        cached = meta.get("csv") or {}
        return (
            int(cached.get("mtime_ns", -1)) == int(current.get("mtime_ns", -2))
            and int(cached.get("size", -1)) == int(current.get("size", -2))
        )
    except Exception:
        return False


def _build_cache(csv_path: Path) -> "pd.DataFrame":
    """Carrega CSV, normaliza colunas e retorna DataFrame pronto para consulta."""
    import pandas as pd

    # lê tudo como string para preservar vírgulas e formatos; numéricos serão parseados no engine
    df = pd.read_csv(csv_path, sep=";", dtype=str, encoding="utf-8")

    # normalizações leves (robustez)
    for col in ("uf", "uf_dest", "cfop", "ncm", "movimento"):
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()

    if "movimento" in df.columns:
        df["movimento"] = df["movimento"].str.upper()

    # data: suporta YYYY-MM-DD, DD/MM/YYYY, YYYYMMDD (e variantes)
    # dayfirst=True cobre DD/MM/YYYY; errors='coerce' evita crash
    date_col = None
    for cand in ("dhemi", "dtemi", "dt_emissao"):
        if cand in df.columns:
            date_col = cand
            break

    if not date_col:
        raise ValueError("CSV não possui colunas de data esperadas (dhemi/dtemi/dt_emissao).")

    df["__dt"] = pd.to_datetime(df[date_col].astype(str).str.strip(), errors="coerce", dayfirst=True)

    # elimina linhas sem data válida (mesma semântica do código atual)
    df = df[df["__dt"].notna()].copy()

    # chave mês (para consultas futuras e para engine, se desejar)
    df["__month"] = df["__dt"].dt.to_period("M").astype(str)  # YYYY-MM

    return df


def _load_dataset_df() -> "pd.DataFrame":
    """Carrega DataFrame do cache persistente, reconstruindo se necessário."""
    ensure_data_dir()

    if not DATASET_PATH.exists():
        raise ValueError("Base não encontrada. Faça upload do CSV em /database/import-csv.")

    pkl_path, pq_path, meta_path = _cache_paths(DATASET_PATH)

    # Tenta reutilizar cache se estiver fresco
    if _cache_is_fresh(DATASET_PATH, meta_path):
        # Preferência: Parquet (mais rápido/compacto) -> Pickle
        try:
            if pq_path.exists():
                import pandas as pd
                return pd.read_parquet(pq_path)
        except Exception:
            pass

        try:
            if pkl_path.exists():
                import pandas as pd
                return pd.read_pickle(pkl_path)
        except Exception:
            pass

    # Reconstrói cache
    df = _build_cache(DATASET_PATH)

    # Persiste: tenta parquet; se não tiver engine, cai no pickle
    wrote_any = False
    try:
        df.to_parquet(pq_path, index=False)  # requer pyarrow ou fastparquet
        wrote_any = True
    except Exception:
        pass

    try:
        df.to_pickle(pkl_path)
        wrote_any = True
    except Exception:
        pass

    # Sempre escreve meta (mesmo se persistência falhar; meta controla freshness)
    meta = {
        "csv": _file_fingerprint(DATASET_PATH),
        "cache": {
            "parquet": bool(pq_path.exists()),
            "pickle": bool(pkl_path.exists()),
            "wrote_any": wrote_any,
        },
    }
    _write_meta(meta_path, meta)

    return df


# ------------------------
# Query
# ------------------------

def _norm(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    s2 = str(s).strip()
    return s2 or None


def query_dataset(filters: Filters) -> list[dict]:
    """Retorna list[dict] compatível com o engine.

    Implementação:
    - carrega DataFrame do cache persistente
    - aplica filtros de forma vetorizada
    - devolve records (dicts) com valores como strings (preserva parse_money no engine)
    """
    import pandas as pd

    df = _load_dataset_df()

    # período
    d0 = pd.Timestamp(filters.periodo_inicio)
    d1 = pd.Timestamp(filters.periodo_fim)
    m = (df["__dt"] >= d0) & (df["__dt"] <= d1)

    # UF origem/destino
    uf_or = _norm(filters.uf_origem)
    if uf_or:
        m &= df.get("uf", "").astype(str).str.upper().eq(uf_or.upper())

    uf_de = _norm(filters.uf_destino)
    if uf_de:
        m &= df.get("uf_dest", "").astype(str).str.upper().eq(uf_de.upper())

    # NCM exato
    ncm = _norm(filters.ncm)
    if ncm:
        m &= df.get("ncm", "").astype(str).str.strip().eq(ncm)

    # Produto contém
    prod = _norm(filters.produto)
    if prod:
        m &= df.get("produto", "").astype(str).str.upper().str.contains(prod.upper(), na=False)

    # CFOP exato
    cfop = _norm(filters.cfop)
    if cfop:
        m &= df.get("cfop", "").astype(str).str.strip().eq(cfop)

    out_df = df.loc[m].copy()

    # Remove colunas internas antes de serializar
    for col in ("__dt", "__month"):
        if col in out_df.columns:
            out_df.drop(columns=[col], inplace=True)

    # Converte NaN -> "" para manter semântica do engine (parse_money trata vazio)
    out_df = out_df.where(out_df.notna(), "")

    return out_df.to_dict("records")


def sum_field(rows: Iterable[dict], field: str) -> float:
    total = 0.0
    for r in rows:
        total += parse_money(r.get(field, "0"))
    return float(total)
