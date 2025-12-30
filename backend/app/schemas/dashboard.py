# backend/app/schemas/dashboard.py
from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel


class DashboardStatus(BaseModel):
    exists: bool
    path: str
    rows: int


class DashboardSummary(BaseModel):
    exists: bool
    path: str
    rows: int
    min_date: Optional[str] = None
    max_date: Optional[str] = None
    ufs_origem: List[str] = []
    ufs_destino: List[str] = []
    receita_total: float = 0.0
    icms_total: float = 0.0
    pis_total: float = 0.0
    cofins_total: float = 0.0


class DashboardKpis(BaseModel):
    receita_total: float = 0.0
    carga_atual_total: float = 0.0
    icms_total: float = 0.0
    pis_total: float = 0.0
    cofins_total: float = 0.0


class DashboardTimeSeriesPoint(BaseModel):
    period: str  # ex: "2024-01"
    receita: float = 0.0
    icms: float = 0.0
    pis: float = 0.0
    cofins: float = 0.0


class DashboardResponse(BaseModel):
    status: DashboardStatus
    summary: DashboardSummary
    kpis: DashboardKpis
    timeseries: List[DashboardTimeSeriesPoint] = []


# -----------------------------
# Comparativo Reforma (NOVO)
# -----------------------------

class DashboardCompareKpis(BaseModel):
    ano_reforma: int
    receita_total: float = 0.0
    carga_atual_total: float = 0.0
    carga_reforma_total: float = 0.0
    diferenca_absoluta: float = 0.0
    diferenca_percentual: float = 0.0


class DashboardCompareTributo(BaseModel):
    tributo: str
    atual: float = 0.0
    reforma: float = 0.0


class DashboardCompareTimeSeriesPoint(BaseModel):
    period: str  # "YYYY-MM"
    receita: float = 0.0
    atual: float = 0.0
    reforma: float = 0.0


class DashboardCompareResponse(BaseModel):
    kpis: DashboardCompareKpis
    detalhes: List[DashboardCompareTributo] = []
    timeseries: List[DashboardCompareTimeSeriesPoint] = []
