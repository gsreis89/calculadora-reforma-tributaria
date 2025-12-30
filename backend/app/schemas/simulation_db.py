from pydantic import BaseModel

class SimulationDBResult(BaseModel):
    ano: int
    total_valor_operacoes: float

    carga_atual_icms: float
    carga_atual_pis: float
    carga_atual_cofins: float
    carga_atual_total: float

    aliquota_cbs: float
    aliquota_ibs: float
    carga_reforma_total: float

    diferenca_absoluta: float
    diferenca_percentual: float
