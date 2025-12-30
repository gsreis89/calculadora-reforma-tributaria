# backend/app/services/simulator_engine/cash_ledger.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple


def _first_day_from_period(period: str) -> date:
    # period: "YYYY-MM"
    y, m = period.split("-")
    return date(int(y), int(m), 1)


def _month_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


@dataclass
class CashSeriesPoint:
    period: str
    competencia_liquida: float
    competencia_bruta: float
    caixa_liquida: float
    caixa_bruta: float


def build_cash_ledger(
    *,
    competencia_series: List[dict],
    prazo_medio_dias: int,
) -> Dict:
    """Constrói Cash Ledger estimado a partir da série mensal por competência.

    Entradas:
      - competencia_series: lista de pontos do v4 (cada item com period, reforma_bruta, reforma_liquida).
      - prazo_medio_dias: proxy para o deslocamento caixa (pagamento/split).

    Modelo (estimado):
      - Caixa_bruta(periodo_pagamento) = soma(reforma_bruta(periodo_competencia) deslocada por prazo_medio_dias)
      - Caixa_liquida(periodo_pagamento) = soma(reforma_liquida(periodo_competencia) deslocada por prazo_medio_dias)

    Observação:
      - Este v6 não usa base real de pagamentos, apenas deslocamento por prazo médio.
      - Quando houver F_PAGAMENTO, substituímos a regra por conciliação real.
    """

    prazo = int(max(0, prazo_medio_dias))

    # Buckets por mês de competência (originais)
    comp_bruta: Dict[str, float] = {}
    comp_liq: Dict[str, float] = {}

    for p in competencia_series or []:
        per = str(p.get("period") or "")
        if not per:
            continue
        comp_bruta[per] = comp_bruta.get(per, 0.0) + float(p.get("reforma_bruta") or 0.0)
        comp_liq[per] = comp_liq.get(per, 0.0) + float(p.get("reforma_liquida") or 0.0)

    # Buckets por mês de caixa (deslocados)
    cash_bruta: Dict[str, float] = {}
    cash_liq: Dict[str, float] = {}

    for per in sorted(set(list(comp_bruta.keys()) + list(comp_liq.keys()))):
        d0 = _first_day_from_period(per)
        pay_day = d0 + timedelta(days=prazo)
        cash_per = _month_key(pay_day)

        cash_bruta[cash_per] = cash_bruta.get(cash_per, 0.0) + float(comp_bruta.get(per, 0.0))
        cash_liq[cash_per] = cash_liq.get(cash_per, 0.0) + float(comp_liq.get(per, 0.0))

    # Série unificada (competência e caixa)
    all_periods = sorted(set(list(comp_bruta.keys()) + list(cash_bruta.keys()) + list(comp_liq.keys()) + list(cash_liq.keys())))

    series: List[dict] = []
    peak = {"period": None, "value": 0.0}
    total_cash_liq = 0.0

    for per in all_periods:
        cb = float(comp_bruta.get(per, 0.0))
        cl = float(comp_liq.get(per, 0.0))
        xb = float(cash_bruta.get(per, 0.0))
        xl = float(cash_liq.get(per, 0.0))

        series.append(
            {
                "period": per,
                "competencia_bruta": cb,
                "competencia_liquida": cl,
                "caixa_bruta": xb,
                "caixa_liquida": xl,
            }
        )

        total_cash_liq += xl
        if xl > float(peak["value"]):
            peak = {"period": per, "value": float(xl)}

    # KPIs
    summary = {
        "prazo_medio_dias": prazo,
        "total_caixa_liquida": float(total_cash_liq),
        "pico_caixa_liquida": {"period": peak["period"], "value": float(peak["value"])},
    }

    return {
        "summary": summary,
        "series": series,
    }
