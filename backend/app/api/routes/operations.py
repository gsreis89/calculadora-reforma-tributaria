from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.operations import OperacaoResumo
from app.services.operations_service import listar_operacoes_resumo

router = APIRouter(prefix="/operacoes", tags=["operacoes"])


@router.get("/resumo", response_model=List[OperacaoResumo])
def get_operacoes_resumo(
    data_inicio: Optional[datetime] = Query(
        None, description="Data/hora inicial (ex: 2024-01-01T00:00:00)"
    ),
    data_fim: Optional[datetime] = Query(
        None, description="Data/hora final (ex: 2024-12-31T23:59:59)"
    ),
    movimento: Optional[str] = Query(
        None, description="Filtro por tipo de movimento (ex: ENTRADA, SAIDA)"
    ),
    limite: int = Query(200, le=1000, description="Quantidade máxima de registros"),
    db: Session = Depends(get_db),
):
    """
    Retorna um resumo enxuto das operações de NFe, com filtros opcionais.
    """
    return listar_operacoes_resumo(
        db=db,
        data_inicio=data_inicio,
        data_fim=data_fim,
        movimento=movimento,
        limite=limite,
    )
