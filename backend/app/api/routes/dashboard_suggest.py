from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
from app.services.dashboard_service import suggest_values

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/suggest", response_model=List[str])
def dashboard_suggest(
    field: str = Query(..., description="produto|ncm|cfop"),
    q: str = Query("", description="texto digitado"),
    limit: int = Query(10, ge=1, le=50),

    periodo_inicio: Optional[str] = None,
    periodo_fim: Optional[str] = None,
    uf_origem: Optional[str] = None,
    uf_destino: Optional[str] = None,
    ncm: Optional[str] = None,
    produto: Optional[str] = None,
    cfop: Optional[str] = None,
):
    if field not in {"produto", "ncm", "cfop"}:
        raise HTTPException(status_code=400, detail="field inválido")

    return suggest_values(
        field=field,
        q=q,
        limit=limit,
        periodo_inicio=periodo_inicio,
        periodo_fim=periodo_fim,
        uf_origem=uf_origem,
        uf_destino=uf_destino,
        ncm=ncm,
        produto=produto,
        cfop=cfop,
    )
