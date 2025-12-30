from pydantic import BaseModel, Field
from typing import Optional, Literal

TaxTipo = Literal[
    "CBS_PADRAO",
    "IBS_PADRAO",
    "ICMS_ATUAL",
    "PIS_ATUAL",
    "COFINS_ATUAL",
]

class TaxParamBase(BaseModel):
    ano: int = Field(..., ge=2000, le=2100)
    uf: Optional[str] = Field(default=None, description="UF (ex: SP). Pode ser null para 'geral'.")
    tipo: TaxTipo
    aliquota: float = Field(..., ge=0.0, le=1.0, description="Alíquota em decimal (ex: 0.0925 = 9,25%).")
    descricao: Optional[str] = None

class TaxParamCreate(TaxParamBase):
    pass

class TaxParamUpdate(BaseModel):
    aliquota: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    descricao: Optional[str] = None

class TaxParamItem(TaxParamBase):
    id: str
