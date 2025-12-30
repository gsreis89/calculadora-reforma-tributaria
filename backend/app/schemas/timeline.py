from enum import Enum
from typing import Dict, Optional
from pydantic import BaseModel

class TaxKey(str, Enum):
    PIS = "PIS"
    COFINS = "COFINS"
    CBS = "CBS"
    ICMS = "ICMS"
    ISS = "ISS"
    IBS = "IBS"
    IPI = "IPI"
    IS = "IS"

class TaxStatus(str, Enum):
    sem_alteracao = "sem_alteracao"
    ativo = "ativo"
    extinto = "extinto"
    reduzido = "reduzido"
    novo = "novo"
    definido_posteriormente = "definido_posteriormente"

class TaxConfig(BaseModel):
    status: TaxStatus
    aliquota: Optional[float] = None
    observacao: Optional[str] = None

TaxYearConfig = Dict[TaxKey, TaxConfig]
