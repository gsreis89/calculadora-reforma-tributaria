from datetime import date
from typing import List
from pydantic import BaseModel
from .timeline import TaxKey

class SimulationRequest(BaseModel):
    empresa_id: int
    cenario_id: int
    ano: int
    periodo_inicio: date
    periodo_fim: date
    receita_total: float = 1_000_000.0

class SimulationTributeDetail(BaseModel):
    tributo: TaxKey
    carga_antes: float
    carga_depois: float

class SimulationResponse(BaseModel):
    empresa_id: int
    cenario_id: int
    ano: int
    periodo_inicio: date
    periodo_fim: date
    receita_total: float
    carga_total_antes: float
    carga_total_depois: float
    margem_antes: float
    margem_depois: float
    detalhes_por_tributo: List[SimulationTributeDetail]
