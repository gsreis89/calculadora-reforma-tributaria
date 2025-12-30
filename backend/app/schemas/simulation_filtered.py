# backend/app/schemas/simulation_filtered.py
from pydantic import BaseModel
from typing import List, Optional


class SimulationFilteredRequest(BaseModel):
    periodo_inicio: str
    periodo_fim: str
    ano_reforma: int
    uf_origem: Optional[str] = None
    uf_destino: Optional[str] = None
    ncm: Optional[str] = None
    produto: Optional[str] = None


class TributoDetalhe(BaseModel):
    tributo: str
    valor_atual: float
    valor_reforma: float


class SimulationFilteredResponse(BaseModel):
    periodo_inicio: str
    periodo_fim: str
    ano_reforma: int
    receita_total: float
    carga_atual_total: float
    carga_reforma_total: float
    diferenca_absoluta: float
    diferenca_percentual: float
    detalhes: List[TributoDetalhe]
