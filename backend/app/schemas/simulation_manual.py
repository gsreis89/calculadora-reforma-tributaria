# backend/app/schemas/simulation_manual.py
from typing import Optional
from pydantic import BaseModel


class SimulacaoManualPayload(BaseModel):
    ano: int
    valor_produto: float

    bc_icms: float
    bc_pis: float
    bc_cofins: float

    aliq_icms_atual: float
    aliq_pis_atual: float
    aliq_cofins_atual: float

    uf_origem: str
    uf_destino: str

    ncm: Optional[str] = None
    produto: Optional[str] = None
    movimento: Optional[str] = None
    cfop: Optional[str] = None


class SimulacaoManualResponse(BaseModel):
    ano: int
    valor_produto: float
    base_icms: float

    valor_icms_atual: float
    valor_icms_reforma: float

    valor_pis_atual: float
    valor_pis_reforma: float

    valor_cofins_atual: float
    valor_cofins_reforma: float

    valor_cbs: float
    valor_ibs: float

    carga_total_atual: float
    carga_total_reforma: float

    diferenca_absoluta: float
    diferenca_percentual: float
