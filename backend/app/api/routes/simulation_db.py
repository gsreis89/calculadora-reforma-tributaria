from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.simulation_db_service import simular_reforma_db
from app.schemas.simulation_db import SimulationDBResult

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.simulation_db_service import simular_reforma_db
from app.schemas.simulation_db import SimulationDBResult

from app.schemas.simulation_filter import SimulationFilterRequest, SimulationFilterResponse
from app.services.simulation_filter_service import simular_reforma_filtrada

router = APIRouter(tags=["simulation-db"])


@router.get("/simulacao-db", response_model=SimulationDBResult)
def simular_db(
    ano: int,
    empresa: str | None = None,
    movimento: str | None = None,
    db: Session = Depends(get_db),
):
    try:
        return simular_reforma_db(db, ano, empresa, movimento)
    except ValueError as e:
        # Erro de regra de negócio -> 400, não 500
        raise HTTPException(status_code=400, detail=str(e))
    
router = APIRouter(tags=["simulation-db"])


@router.get("/simulacao-db", response_model=SimulationDBResult)
def simular_db(
    ano: int,
    empresa: str | None = None,
    movimento: str | None = None,
    db: Session = Depends(get_db),
):
    try:
        return simular_reforma_db(db, ano, empresa, movimento)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/simulacao-detalhada", response_model=SimulationFilterResponse)
def simular_detalhada(
    payload: SimulationFilterRequest,
    db: Session = Depends(get_db),
):
    """
    Simulação filtrada:
    - período (datas)
    - UF origem/destino
    - NCM / produto
    - ano do cronograma da reforma
    """
    try:
        return simular_reforma_filtrada(db, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

