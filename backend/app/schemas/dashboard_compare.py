from __future__ import annotations

from pydantic import BaseModel
from typing import List


class CompareKpis(BaseModel):
    ano_reforma: int
    receita_total: float
    carga_atual_total: float
    carga_reforma_total: float
    diferenca_absoluta: float
    diferenca_percentual: float


class CompareTributo(BaseModel):
    tributo: str
    atual: float
    reforma: float


class CompareTimeSeriesPoint(BaseModel):
    period: str  # YYYY-MM
    receita: float
    atual: float
    reforma: float


class DashboardCompareResponse(BaseModel):
    kpis: CompareKpis
    detalhes: List[CompareTributo]
    timeseries: List[CompareTimeSeriesPoint]
