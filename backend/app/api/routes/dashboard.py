# backend/app/api/routes/dashboard.py
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import Dict, Optional, List, Set

from fastapi import APIRouter, Query, HTTPException

from app.schemas.dashboard import (
    DashboardResponse,
    DashboardKpis,
    DashboardTimeSeriesPoint,
)
from app.services.database_service import get_status
from app.storage.dataset import Filters, query_dataset
from app.services.tax_params_service import get_rate
from app.core.number import parse_money  # <-- USE UM ÚNICO PARSER
import csv

from app.core.dataset import DATASET_PATH, ensure_data_dir


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def _to_date(s: str) -> date:
    return datetime.fromisoformat(s[:10]).date()


def _default_period():
    return date(2000, 1, 1), date(2100, 12, 31)


def _parse_row_date(raw: str) -> Optional[date]:
    if not raw:
        return None
    s = str(raw).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y%m%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            continue
    return None


def _num(v: Optional[str]) -> float:
    try:
        return float(parse_money(v))
    except Exception:
        return 0.0


def _build_timeseries_by_month(rows: list[dict]) -> list[DashboardTimeSeriesPoint]:
    acc: Dict[str, Dict[str, float]] = defaultdict(
        lambda: {"receita": 0.0, "icms": 0.0, "pis": 0.0, "cofins": 0.0}
    )

    for row in rows:
        dt = _parse_row_date(row.get("dhemi", ""))
        if not dt:
            continue

        key = f"{dt.year:04d}-{dt.month:02d}"

        acc[key]["receita"] += _num(row.get("vprod"))
        acc[key]["icms"] += _num(row.get("vicms_icms"))
        acc[key]["pis"] += _num(row.get("vpis"))
        acc[key]["cofins"] += _num(row.get("vcofins"))

    points: list[DashboardTimeSeriesPoint] = []
    for k in sorted(acc.keys()):
        points.append(
            DashboardTimeSeriesPoint(
                period=k,
                receita=float(acc[k]["receita"]),
                icms=float(acc[k]["icms"]),
                pis=float(acc[k]["pis"]),
                cofins=float(acc[k]["cofins"]),
            )
        )
    return points


# =========================
# NEW: SUGGEST (autocomplete)
# =========================
@router.get("/suggest")
def suggest(
    field: str = Query(..., description="produto|ncm|cfop"),
    q: str = Query("", description="texto digitado"),
    limit: int = Query(10, ge=1, le=50),

    # opcionais para sugerir dentro do recorte atual
    periodo_inicio: Optional[str] = Query(default=None),
    periodo_fim: Optional[str] = Query(default=None),
    uf_origem: Optional[str] = Query(default=None),
    uf_destino: Optional[str] = Query(default=None),
):
    st = get_status()
    if not st.get("exists"):
        return {"items": []}

    field = (field or "").strip().lower()
    q_norm = (q or "").strip().lower()

    if field not in {"produto", "ncm", "cfop"}:
        raise HTTPException(status_code=400, detail="field inválido. Use: produto|ncm|cfop")

    # Recorte de período (default amplo)
    d0, d1 = _default_period()
    if periodo_inicio:
        d0 = _to_date(periodo_inicio)
    if periodo_fim:
        d1 = _to_date(periodo_fim)

    ufo = (uf_origem or "").strip().upper()
    ufd = (uf_destino or "").strip().upper()

    ensure_data_dir()
    if not DATASET_PATH.exists():
        return {"items": []}

    def pick_value(row: dict) -> str:
        if field == "produto":
            return (row.get("produto") or "").strip()
        if field == "ncm":
            return (row.get("ncm") or "").strip()
        return (row.get("cfop") or "").strip()

    seen = set()
    items: List[str] = []

    # STREAMING: lê e para ao atingir o limit
    with open(DATASET_PATH, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            # período
            dt = _parse_row_date(row.get("dhemi", ""))
            if not dt:
                continue
            if dt < d0 or dt > d1:
                continue

            # UF origem/destino (match exato como seu dataset.py)
            if ufo and (row.get("uf", "") or "").strip().upper() != ufo:
                continue
            if ufd and (row.get("uf_dest", "") or "").strip().upper() != ufd:
                continue

            v = pick_value(row)
            if not v:
                continue

            vn = v.lower()
            if q_norm and q_norm not in vn:
                continue

            if vn in seen:
                continue

            seen.add(vn)
            items.append(v)

            if len(items) >= limit:
                break

    return {"items": items}


# =========================
# NEW: BREAKDOWNS (cards + rankings)
# =========================
from typing import Any, Tuple

def _norm(s: Optional[str]) -> str:
    return (s or "").strip()

def _upper(s: Optional[str]) -> str:
    return _norm(s).upper()

def _contains(hay: str, needle: str) -> bool:
    if not needle:
        return True
    return needle.upper() in (hay or "").strip().upper()

def _match_exact(value: str, expected: str) -> bool:
    if not expected:
        return True
    return (value or "").strip().upper() == expected.strip().upper()

def _match_ncm(value: str, expected: str) -> bool:
    if not expected:
        return True
    return (value or "").strip() == expected.strip()

def _parse_movimento(v: str) -> str:
    x = (v or "").strip().upper()
    if x in {"ENTRADA", "E"}:
        return "ENTRADA"
    if x in {"SAIDA", "SAÍDA", "S"}:
        return "SAIDA"
    return x or "N/I"

def _topn_from_dict(d: Dict[str, float], n: int = 10) -> list[dict]:
    items = sorted(d.items(), key=lambda kv: kv[1], reverse=True)[:n]
    return [{"key": k, "value": float(v)} for k, v in items]

@router.get("/breakdowns")
def breakdowns(
    # mesmos filtros do dashboard
    periodo_inicio: Optional[str] = Query(default=None),
    periodo_fim: Optional[str] = Query(default=None),
    uf_origem: Optional[str] = Query(default=None),
    uf_destino: Optional[str] = Query(default=None),
    ncm: Optional[str] = Query(default=None),
    produto: Optional[str] = Query(default=None),
    cfop: Optional[str] = Query(default=None),
    limit: int = Query(10, ge=5, le=50),
):
    st = get_status()
    if not st.get("exists"):
        return {
            "distinct": {"produtos": 0, "ncm": 0, "cfop": 0},
            "movimento": [],
            "top_produtos": [],
            "top_ncm": [],
            "top_cfop": [],
            "top_uf_origem": [],
            "top_uf_destino": [],
        }

    # período
    d0, d1 = _default_period()
    if periodo_inicio:
        d0 = _to_date(periodo_inicio)
    if periodo_fim:
        d1 = _to_date(periodo_fim)

    ufo = _upper(uf_origem)
    ufd = _upper(uf_destino)
    ncm_f = _norm(ncm)
    produto_f = _norm(produto)
    cfop_f = _norm(cfop)

    ensure_data_dir()
    if not DATASET_PATH.exists():
        return {
            "distinct": {"produtos": 0, "ncm": 0, "cfop": 0},
            "movimento": [],
            "top_produtos": [],
            "top_ncm": [],
            "top_cfop": [],
            "top_uf_origem": [],
            "top_uf_destino": [],
        }

    # acumuladores
    distinct_prod: Set[str] = set()
    distinct_ncm: Set[str] = set()
    distinct_cfop: Set[str] = set()

    top_prod: Dict[str, float] = defaultdict(float)
    top_ncm_map: Dict[str, float] = defaultdict(float)
    top_cfop_map: Dict[str, float] = defaultdict(float)
    top_ufo_map: Dict[str, float] = defaultdict(float)
    top_ufd_map: Dict[str, float] = defaultdict(float)
    mov_map: Dict[str, float] = defaultdict(float)

    # leitura streaming do CSV (rápido e consistente com /suggest)
    with open(DATASET_PATH, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            dt = _parse_row_date(row.get("dhemi", ""))
            if not dt:
                continue
            if dt < d0 or dt > d1:
                continue

            # filtros UF origem/destino (exato)
            if ufo and (row.get("uf", "") or "").strip().upper() != ufo:
                continue
            if ufd and (row.get("uf_dest", "") or "").strip().upper() != ufd:
                continue

            # NCM / CFOP (exato)
            if ncm_f and (row.get("ncm", "") or "").strip() != ncm_f:
                continue
            if cfop_f and (row.get("cfop", "") or "").strip() != cfop_f:
                continue

            # Produto (contains)
            if produto_f and not _contains(row.get("produto", ""), produto_f):
                continue

            receita = _num(row.get("vprod"))
            if receita == 0:
                # ainda assim conta distincts
                pass

            prod = (row.get("produto") or "").strip()
            ncm_v = (row.get("ncm") or "").strip()
            cfop_v = (row.get("cfop") or "").strip()
            uf_o = (row.get("uf") or "").strip().upper()
            uf_d = (row.get("uf_dest") or "").strip().upper()
            mov = _parse_movimento(row.get("movimento", ""))

            if prod:
                distinct_prod.add(prod.upper())
                top_prod[prod] += receita

            if ncm_v:
                distinct_ncm.add(ncm_v)
                top_ncm_map[ncm_v] += receita

            if cfop_v:
                distinct_cfop.add(cfop_v)
                top_cfop_map[cfop_v] += receita

            if uf_o:
                top_ufo_map[uf_o] += receita

            if uf_d:
                top_ufd_map[uf_d] += receita

            mov_map[mov] += receita

    return {
        "distinct": {
            "produtos": len(distinct_prod),
            "ncm": len(distinct_ncm),
            "cfop": len(distinct_cfop),
        },
        "movimento": _topn_from_dict(mov_map, n=10),
        "top_produtos": _topn_from_dict(top_prod, n=limit),
        "top_ncm": _topn_from_dict(top_ncm_map, n=limit),
        "top_cfop": _topn_from_dict(top_cfop_map, n=limit),
        "top_uf_origem": _topn_from_dict(top_ufo_map, n=limit),
        "top_uf_destino": _topn_from_dict(top_ufd_map, n=limit),
    }


@router.get("/overview", response_model=DashboardResponse)
def overview(
    periodo_inicio: Optional[str] = Query(default=None),
    periodo_fim: Optional[str] = Query(default=None),
    uf_origem: Optional[str] = Query(default=None),
    uf_destino: Optional[str] = Query(default=None),
    ncm: Optional[str] = Query(default=None),
    produto: Optional[str] = Query(default=None),
    cfop: Optional[str] = Query(default=None),
):
    st = get_status()

    if not st.get("exists"):
        return DashboardResponse(
            status=st,
            summary={
                "exists": False,
                "path": st.get("path", ""),
                "rows": 0,
                "min_date": None,
                "max_date": None,
                "ufs_origem": [],
                "ufs_destino": [],
                "receita_total": 0.0,
                "icms_total": 0.0,
                "pis_total": 0.0,
                "cofins_total": 0.0,
            },
            kpis=DashboardKpis(),
            timeseries=[],
        )

    d0, d1 = _default_period()
    if periodo_inicio:
        d0 = _to_date(periodo_inicio)
    if periodo_fim:
        d1 = _to_date(periodo_fim)

    rows = query_dataset(
        Filters(
            periodo_inicio=d0,
            periodo_fim=d1,
            uf_origem=uf_origem,
            uf_destino=uf_destino,
            ncm=ncm,
            produto=produto,
            cfop=cfop,
        )
    )

    receita_total = 0.0
    icms_total = 0.0
    pis_total = 0.0
    cofins_total = 0.0

    ufs_o = set()
    ufs_d = set()
    dates: list[date] = []

    for r in rows:
        receita_total += _num(r.get("vprod"))
        icms_total += _num(r.get("vicms_icms"))
        pis_total += _num(r.get("vpis"))
        cofins_total += _num(r.get("vcofins"))

        ufo = (r.get("uf") or "").strip().upper()
        ufd = (r.get("uf_dest") or "").strip().upper()
        if ufo:
            ufs_o.add(ufo)
        if ufd:
            ufs_d.add(ufd)

        dt = _parse_row_date(r.get("dhemi", ""))
        if dt:
            dates.append(dt)

    min_date = min(dates).isoformat() if dates else None
    max_date = max(dates).isoformat() if dates else None

    summary = {
        "exists": True,
        "path": st.get("path", ""),
        "rows": len(rows),
        "min_date": min_date,
        "max_date": max_date,
        "ufs_origem": sorted(ufs_o),
        "ufs_destino": sorted(ufs_d),
        "receita_total": float(receita_total),
        "icms_total": float(icms_total),
        "pis_total": float(pis_total),
        "cofins_total": float(cofins_total),
    }

    kpis = DashboardKpis(
        receita_total=float(receita_total),
        icms_total=float(icms_total),
        pis_total=float(pis_total),
        cofins_total=float(cofins_total),
        carga_atual_total=float(icms_total + pis_total + cofins_total),
    )

    ts = _build_timeseries_by_month(rows)

    return DashboardResponse(
        status=st,
        summary=summary,
        kpis=kpis,
        timeseries=ts,
    )


@router.get("/compare")
def compare(
    ano_reforma: int = Query(..., ge=2026, le=2033),
    periodo_inicio: Optional[str] = Query(default=None),
    periodo_fim: Optional[str] = Query(default=None),
    uf_origem: Optional[str] = Query(default=None),
    uf_destino: Optional[str] = Query(default=None),
    ncm: Optional[str] = Query(default=None),
    produto: Optional[str] = Query(default=None),
    cfop: Optional[str] = Query(default=None),
):
    st = get_status()
    if not st.get("exists"):
        return {
            "kpis": {
                "ano_reforma": ano_reforma,
                "receita_total": 0.0,
                "carga_atual_total": 0.0,
                "carga_reforma_total": 0.0,
                "diferenca_absoluta": 0.0,
                "diferenca_percentual": 0.0,
            },
            "detalhes": [],
            "timeseries": [],
        }

    d0, d1 = _default_period()
    if periodo_inicio:
        d0 = _to_date(periodo_inicio)
    if periodo_fim:
        d1 = _to_date(periodo_fim)

    rows = query_dataset(
        Filters(
            periodo_inicio=d0,
            periodo_fim=d1,
            uf_origem=uf_origem,
            uf_destino=uf_destino,
            ncm=ncm,
            produto=produto,
            cfop=cfop,
        )
    )

    receita_total = 0.0
    icms_atual = 0.0
    pis_atual = 0.0
    cofins_atual = 0.0

    for r in rows:
        receita_total += _num(r.get("vprod"))
        icms_atual += _num(r.get("vicms_icms"))
        pis_atual += _num(r.get("vpis"))
        cofins_atual += _num(r.get("vcofins"))

    carga_atual = icms_atual + pis_atual + cofins_atual

    # ✅ CORREÇÃO: get_rate(ano, tipo, uf)
    uf_ref = (uf_origem or "BR").upper()

    cbs = get_rate(ano_reforma, "CBS_PADRAO", uf_ref, default=0.0) or (
        0.0880 if ano_reforma >= 2027 else 0.0090
    )
    ibs = get_rate(ano_reforma, "IBS_PADRAO", uf_ref, default=0.0) or (
        0.0100 if ano_reforma >= 2027 else 0.0010
    )

    valor_cbs = receita_total * float(cbs)
    valor_ibs = receita_total * float(ibs)

    if ano_reforma >= 2027:
        pis_reforma = 0.0
        cofins_reforma = 0.0
    else:
        pis_reforma = pis_atual
        cofins_reforma = cofins_atual

    icms_reforma = icms_atual
    carga_reforma = icms_reforma + pis_reforma + cofins_reforma + valor_cbs + valor_ibs

    dif_abs = carga_reforma - carga_atual
    dif_pct = (dif_abs / carga_atual) * 100.0 if carga_atual else 0.0

    monthly: Dict[str, Dict[str, float]] = defaultdict(
        lambda: {"receita": 0.0, "icms": 0.0, "pis": 0.0, "cofins": 0.0, "atual": 0.0, "reforma": 0.0}
    )

    for r in rows:
        dt = _parse_row_date(r.get("dhemi", ""))
        if not dt:
            continue
        key = f"{dt.year:04d}-{dt.month:02d}"

        receita = _num(r.get("vprod"))
        icms = _num(r.get("vicms_icms"))
        pis = _num(r.get("vpis"))
        cofins = _num(r.get("vcofins"))

        monthly[key]["receita"] += receita
        monthly[key]["icms"] += icms
        monthly[key]["pis"] += pis
        monthly[key]["cofins"] += cofins

    for key in list(monthly.keys()):
        receita_m = monthly[key]["receita"]
        icms_m = monthly[key]["icms"]
        pis_m = monthly[key]["pis"]
        cofins_m = monthly[key]["cofins"]

        atual_m = icms_m + pis_m + cofins_m

        cbs_m = receita_m * float(cbs)
        ibs_m = receita_m * float(ibs)

        if ano_reforma >= 2027:
            reforma_m = icms_m + 0.0 + 0.0 + cbs_m + ibs_m
        else:
            reforma_m = icms_m + pis_m + cofins_m + cbs_m + ibs_m

        monthly[key]["atual"] = atual_m
        monthly[key]["reforma"] = reforma_m

    timeseries = []
    for key in sorted(monthly.keys()):
        timeseries.append(
            {
                "period": key,
                "receita": float(monthly[key]["receita"]),
                "atual": float(monthly[key]["atual"]),
                "reforma": float(monthly[key]["reforma"]),
            }
        )

    detalhes = [
        {"tributo": "ICMS", "atual": float(icms_atual), "reforma": float(icms_reforma)},
        {"tributo": "PIS", "atual": float(pis_atual), "reforma": float(pis_reforma)},
        {"tributo": "COFINS", "atual": float(cofins_atual), "reforma": float(cofins_reforma)},
        {"tributo": "CBS", "atual": 0.0, "reforma": float(valor_cbs)},
        {"tributo": "IBS", "atual": 0.0, "reforma": float(valor_ibs)},
    ]

    return {
        "kpis": {
            "ano_reforma": int(ano_reforma),
            "receita_total": float(receita_total),
            "carga_atual_total": float(carga_atual),
            "carga_reforma_total": float(carga_reforma),
            "diferenca_absoluta": float(dif_abs),
            "diferenca_percentual": float(dif_pct),
        },
        "detalhes": detalhes,
        "timeseries": timeseries,
    }
