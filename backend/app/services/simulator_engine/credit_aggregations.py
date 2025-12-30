# backend/app/services/simulator_engine/credit_aggregations.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

from app.services.simulator_engine.credit_events import CreditEventV2


def _parse_month(m: str) -> Tuple[int, int]:
    # "YYYY-MM"
    y, mm = m.split("-")
    return int(y), int(mm)


def month_diff(a: str, b: str) -> int:
    """Retorna diferença em meses entre a e b (b - a), onde a e b são "YYYY-MM"."""
    ay, am = _parse_month(a)
    by, bm = _parse_month(b)
    return (by - ay) * 12 + (bm - am)


def top_by(
    events: Iterable[CreditEventV2],
    *,
    field: str,
    limit: int = 15,
    metric: str = "credito_apropriado",
) -> List[Dict[str, float]]:
    """Top-N por dimensão.

    field: "ncm" | "cfop" | "produto" | "uf_origem" | "uf_destino" | "finalidade"
    metric: "credito_apropriado" | "credito_apos_glosa" | "credito_gerado" | "glosa"

    Retorna lista: [{"key": <valor>, "value": <soma>}]
    """
    buckets: Dict[str, float] = {}
    for e in events:
        key = getattr(e, field, "") or ""
        val = float(getattr(e, metric, 0.0) or 0.0)
        buckets[key] = buckets.get(key, 0.0) + val

    items = sorted(buckets.items(), key=lambda kv: kv[1], reverse=True)
    items = items[: max(0, int(limit))]
    return [{"key": k, "value": float(v)} for k, v in items]


def series_by_month(
    events: Iterable[CreditEventV2],
    *,
    metric: str = "credito_apropriado",
) -> List[Dict[str, float]]:
    buckets: Dict[str, float] = {}
    for e in events:
        m = e.appropriation_month
        val = float(getattr(e, metric, 0.0) or 0.0)
        buckets[m] = buckets.get(m, 0.0) + val
    return [{"period": k, "value": float(buckets[k])} for k in sorted(buckets.keys())]


def aging_saldo_a_apropriar(
    events: Iterable[CreditEventV2],
    *,
    end_month: str,
) -> Dict[str, float]:
    """Aging do SALDO a apropriar (pós-glosa), na data de corte end_month.

    Cálculo:
      - Agrupa por emit_month.
      - total_liquido_emit = soma(credito_apos_glosa) de todos os eventos daquele emit_month.
      - apropriado_ate_corte = soma(credito_apropriado) onde appropriation_month <= end_month.
      - saldo = max(0, total_liquido_emit - apropriado_ate_corte).

    Bucketização por idade (meses desde emissão até o corte):
      0-3, 3-6, 6-12, 12+

    Observação:
      - Para itens não-ATIVO, saldo tende a zero (apropriado no mesmo mês).
      - Para recortes curtos, ATIVO ainda terá saldo futuro, que é exatamente o objetivo.
    """

    total_liquido_by_emit: Dict[str, float] = {}
    apropriado_by_emit_ate: Dict[str, float] = {}

    for e in events:
        em = e.emit_month
        total_liquido_by_emit[em] = total_liquido_by_emit.get(em, 0.0) + float(e.credito_apos_glosa)

        if month_diff(e.appropriation_month, end_month) >= 0:
            # e.appropriation_month <= end_month
            apropriado_by_emit_ate[em] = apropriado_by_emit_ate.get(em, 0.0) + float(e.credito_apropriado)

    buckets = {"0_3": 0.0, "3_6": 0.0, "6_12": 0.0, "12_plus": 0.0}

    for em, total_liq in total_liquido_by_emit.items():
        apropriado = apropriado_by_emit_ate.get(em, 0.0)
        saldo = max(0.0, float(total_liq) - float(apropriado))
        if saldo <= 0:
            continue

        age = month_diff(em, end_month)  # end - emit
        if age < 3:
            buckets["0_3"] += saldo
        elif age < 6:
            buckets["3_6"] += saldo
        elif age < 12:
            buckets["6_12"] += saldo
        else:
            buckets["12_plus"] += saldo

    return {k: float(v) for k, v in buckets.items()}
