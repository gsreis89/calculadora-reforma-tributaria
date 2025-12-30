from __future__ import annotations

import csv
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from app.core.dataset import DATASET_PATH, ensure_data_dir
from app.services.tax_params_service import get_rate


def _to_float(v: str) -> float:
    if v is None:
        return 0.0
    s = str(v).strip()
    if not s:
        return 0.0
    # Regra simples (igual ao seu database_service): remove milhar "." e troca "," por "."
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except Exception:
        return 0.0


def _parse_date(v: str) -> Optional[datetime]:
    if not v:
        return None
    s = str(v).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y%m%d"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            continue
    return None


def _period_yyyy_mm(dt: datetime) -> str:
    return f"{dt.year:04d}-{dt.month:02d}"


def _get_cbs_ibs_rates(ano: int, uf_ref: str) -> Tuple[float, float]:
    uf_ref = (uf_ref or "BR").upper()
    cbs = get_rate(ano, uf_ref, "CBS_PADRAO")
    ibs = get_rate(ano, uf_ref, "IBS_PADRAO")

    # fallback MVP
    if cbs is None:
        cbs = 0.0880 if ano >= 2027 else 0.0090
    if ibs is None:
        ibs = 0.0100 if ano >= 2027 else 0.0010

    return float(cbs), float(ibs)


def dashboard_compare(ano_reforma: int) -> Dict:
    ensure_data_dir()

    if not DATASET_PATH.exists():
        return {
            "kpis": {
                "ano_reforma": int(ano_reforma),
                "receita_total": 0.0,
                "carga_atual_total": 0.0,
                "carga_reforma_total": 0.0,
                "diferenca_absoluta": 0.0,
                "diferenca_percentual": 0.0,
            },
            "detalhes": [
                {"tributo": "ICMS", "atual": 0.0, "reforma": 0.0},
                {"tributo": "PIS", "atual": 0.0, "reforma": 0.0},
                {"tributo": "COFINS", "atual": 0.0, "reforma": 0.0},
                {"tributo": "CBS", "atual": 0.0, "reforma": 0.0},
                {"tributo": "IBS", "atual": 0.0, "reforma": 0.0},
            ],
            "timeseries": [],
        }

    # Totais atuais (do dataset)
    receita_total = 0.0
    icms_atual = 0.0
    pis_atual = 0.0
    cofins_atual = 0.0

    # Série por período
    series: Dict[str, Dict[str, float]] = {}

    with open(DATASET_PATH, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            receita = _to_float(row.get("vprod", "0"))
            icms = _to_float(row.get("vicms_icms", "0"))
            pis = _to_float(row.get("vpis", "0"))
            cofins = _to_float(row.get("vcofins", "0"))

            receita_total += receita
            icms_atual += icms
            pis_atual += pis
            cofins_atual += cofins

            dt = _parse_date(row.get("dhemi", "")) or None
            period = _period_yyyy_mm(dt) if dt else "SEM_DATA"

            if period not in series:
                series[period] = {
                    "receita": 0.0,
                    "icms": 0.0,
                    "pis": 0.0,
                    "cofins": 0.0,
                }
            series[period]["receita"] += receita
            series[period]["icms"] += icms
            series[period]["pis"] += pis
            series[period]["cofins"] += cofins

    carga_atual_total = icms_atual + pis_atual + cofins_atual

    # Reforma (MVP): CBS/IBS em cima da receita (vprod)
    # UF referência: por simplicidade, BR (depois refinamos por UF origem/destino)
    cbs_rate, ibs_rate = _get_cbs_ibs_rates(ano_reforma, "BR")
    cbs_reforma = receita_total * cbs_rate
    ibs_reforma = receita_total * ibs_rate

    if ano_reforma >= 2027:
        pis_reforma = 0.0
        cofins_reforma = 0.0
    else:
        pis_reforma = pis_atual
        cofins_reforma = cofins_atual

    icms_reforma = icms_atual

    carga_reforma_total = icms_reforma + pis_reforma + cofins_reforma + cbs_reforma + ibs_reforma
    dif_abs = carga_reforma_total - carga_atual_total
    dif_pct = (dif_abs / carga_atual_total) * 100.0 if carga_atual_total else 0.0

    # Timeseries: atual vs reforma por período
    ts_out: List[Dict] = []
    for period in sorted(series.keys()):
        rec = series[period]["receita"]
        icms_p = series[period]["icms"]
        pis_p = series[period]["pis"]
        cofins_p = series[period]["cofins"]

        atual_p = icms_p + pis_p + cofins_p

        cbs_p = rec * cbs_rate
        ibs_p = rec * ibs_rate

        if ano_reforma >= 2027:
            pis_p_ref = 0.0
            cofins_p_ref = 0.0
        else:
            pis_p_ref = pis_p
            cofins_p_ref = cofins_p

        reforma_p = icms_p + pis_p_ref + cofins_p_ref + cbs_p + ibs_p

        ts_out.append(
            {
                "period": period,
                "receita": float(rec),
                "atual": float(atual_p),
                "reforma": float(reforma_p),
            }
        )

    return {
        "kpis": {
            "ano_reforma": int(ano_reforma),
            "receita_total": float(receita_total),
            "carga_atual_total": float(carga_atual_total),
            "carga_reforma_total": float(carga_reforma_total),
            "diferenca_absoluta": float(dif_abs),
            "diferenca_percentual": float(dif_pct),
        },
        "detalhes": [
            {"tributo": "ICMS", "atual": float(icms_atual), "reforma": float(icms_reforma)},
            {"tributo": "PIS", "atual": float(pis_atual), "reforma": float(pis_reforma)},
            {"tributo": "COFINS", "atual": float(cofins_atual), "reforma": float(cofins_reforma)},
            {"tributo": "CBS", "atual": 0.0, "reforma": float(cbs_reforma)},
            {"tributo": "IBS", "atual": 0.0, "reforma": float(ibs_reforma)},
        ],
        "timeseries": ts_out,
    }
