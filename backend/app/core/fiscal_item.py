from dataclasses import dataclass
from datetime import date
from typing import Optional

@dataclass
class FiscalItem:
    data: date
    uf_origem: str
    uf_destino: str
    produto: str
    ncm: Optional[str]
    cfop: Optional[str]
    movimento: str  # ENTRADA / SAIDA / SERVICO
    finalidade: str  # REVENDA / INSUMO / ATIVO / USO_CONSUMO / OUTRAS

    valor_bruto: float

    # tributos atuais
    icms: float
    pis: float
    cofins: float

    # campos calculados
    base_cbs: float = 0.0
    base_ibs: float = 0.0
    base_is: float = 0.0
