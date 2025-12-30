# backend/app/services/simulator_engine/cash_ledger_v2.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List, Optional


def _first_day_from_period(period: str) -> date:
    # period: "YYYY-MM"
    y, m = period.split("-")
    return date(int(y), int(m), 1)


def _month_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def _add_months_first_day(d: date, months: int) -> date:
    y = d.year + (d.month - 1 + months) // 12
    m = (d.month - 1 + months) % 12 + 1
    return date(y, m, 1)


@dataclass
class CashLedgerConfigV2:
    """Config do Cash Ledger v2.

    split_percent:
      - fração do tributo líquido que será recolhida via split no pagamento (0..1).

    delay_days:
      - atraso adicional sobre o prazo médio (proxy de compensações, conciliação, calendário, etc.).

    residual_installments:
      - quantidade de parcelas do saldo residual (1 = paga tudo de uma vez).

    residual_start_offset_months:
      - em quantos meses, a partir do mês do split, começa o pagamento do residual.
        0 = mesmo mês do split
        1 = mês seguinte

    Observação:
      - Este modelo é estimativo (sem eventos reais de pagamento).
      - Quando houver F_PAGAMENTO/F_SPLIT, substituímos por conciliação real.
    """

    prazo_medio_dias: int = 30
    split_percent: float = 0.0
    delay_days: int = 0
    residual_installments: int = 1
    residual_start_offset_months: int = 0


def build_cash_ledger_v2(
    *,
    competencia_series: List[dict],
    cfg: CashLedgerConfigV2,
) -> Dict:
    """Constrói Cash Ledger v2 (split + residual em parcelas) a partir da série mensal por competência.

    Inputs esperados por item de competencia_series:
      - period (YYYY-MM)
      - reforma_bruta
      - reforma_liquida

    Output:
      cash_ledger = {
        "summary": {...},
        "series": [
          {
            "period": "YYYY-MM",
            "competencia_bruta": ...,
            "competencia_liquida": ...,
            "caixa_split": ...,
            "caixa_residual": ...,
            "caixa_total": ...,
            "delta_caixa_menos_competencia": ...,
          }, ...
        ]
      }
    """

    prazo = int(max(0, cfg.prazo_medio_dias))
    delay = int(max(0, cfg.delay_days))
    split_pct = float(min(1.0, max(0.0, cfg.split_percent)))
    nparc = int(max(1, cfg.residual_installments))
    start_off = int(max(0, cfg.residual_start_offset_months))

    # Competência (originais)
    comp_bruta: Dict[str, float] = {}
    comp_liq: Dict[str, float] = {}

    for p in competencia_series or []:
        per = str(p.get("period") or "")
        if not per:
            continue
        comp_bruta[per] = comp_bruta.get(per, 0.0) + float(p.get("reforma_bruta") or 0.0)
        comp_liq[per] = comp_liq.get(per, 0.0) + float(p.get("reforma_liquida") or 0.0)

    # Caixa (split e residual)
    cash_split: Dict[str, float] = {}
    cash_residual: Dict[str, float] = {}

    for per in sorted(set(list(comp_bruta.keys()) + list(comp_liq.keys()))):
        d0 = _first_day_from_period(per)
        pay_day = d0 + timedelta(days=(prazo + delay))
        split_month = _month_key(pay_day)

        # Base de tributo (líquido) para caixa
        due_liq = float(comp_liq.get(per, 0.0))

        split_amt = due_liq * split_pct
        residual = max(0.0, due_liq - split_amt)

        # Split no mês do pagamento
        if split_amt:
            cash_split[split_month] = cash_split.get(split_month, 0.0) + float(split_amt)

        # Residual em parcelas (proxy de recolhimento pelo contribuinte)
        if residual:
            portion = residual / float(nparc)
            start_month_date = _add_months_first_day(_first_day_from_period(split_month), start_off)
            for i in range(nparc):
                dd = _add_months_first_day(start_month_date, i)
                mm = _month_key(dd)
                cash_residual[mm] = cash_residual.get(mm, 0.0) + float(portion)

    all_periods = sorted(
        set(
            list(comp_bruta.keys())
            + list(comp_liq.keys())
            + list(cash_split.keys())
            + list(cash_residual.keys())
        )
    )

    series: List[dict] = []

    total_cash = 0.0
    total_split = 0.0
    total_residual = 0.0

    peak = {"period": None, "value": 0.0}

    for per in all_periods:
        cb = float(comp_bruta.get(per, 0.0))
        cl = float(comp_liq.get(per, 0.0))
        xs = float(cash_split.get(per, 0.0))
        xr = float(cash_residual.get(per, 0.0))
        xt = float(xs + xr)
        delta = float(xt - cl)

        series.append(
            {
                "period": per,
                "competencia_bruta": cb,
                "competencia_liquida": cl,
                "caixa_split": xs,
                "caixa_residual": xr,
                "caixa_total": xt,
                "delta_caixa_menos_competencia": delta,
            }
        )

        total_cash += xt
        total_split += xs
        total_residual += xr

        if xt > float(peak["value"]):
            peak = {"period": per, "value": float(xt)}

    summary = {
        "prazo_medio_dias": prazo,
        "delay_days": delay,
        "split_percent": split_pct,
        "residual_installments": nparc,
        "residual_start_offset_months": start_off,
        "total_caixa": float(total_cash),
        "total_split": float(total_split),
        "total_residual": float(total_residual),
        "pico_caixa": {"period": peak["period"], "value": float(peak["value"])},
    }

    return {"summary": summary, "series": series}
