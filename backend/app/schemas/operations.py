from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class OperacaoResumo(BaseModel):
    id: int
    empresa: Optional[str] = None
    movimento: Optional[str] = None
    data_emissao: Optional[datetime] = None
    uf_origem: Optional[str] = None
    uf_destino: Optional[str] = None
    cfop: Optional[str] = None
    valor_produtos: Optional[float] = None
    valor_icms: Optional[float] = None
    valor_pis: Optional[float] = None
    valor_cofins: Optional[float] = None

    class Config:
        from_attributes = True  # pydantic v2: ao invés de orm_mode = True

