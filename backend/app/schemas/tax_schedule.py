# backend/app/schemas/tax_schedule.py
from pydantic import BaseModel
from typing import Optional


class TaxParamBase(BaseModel):
    ano: int
    uf: str
    tipo: str          # ex: "CBS_PADRAO", "IBS_UF", etc.
    aliquota: float
    descricao: Optional[str] = None


class TaxParamCreate(TaxParamBase):
    pass


class TaxParamUpdate(BaseModel):
    aliquota: Optional[float] = None
    descricao: Optional[str] = None


class TaxParam(TaxParamBase):
    id: int
