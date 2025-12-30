# backend/app/api/routes/tax_schedule.py
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from app.schemas.tax_schedule import TaxParam, TaxParamCreate, TaxParamUpdate
from app.core import tax_storage

router = APIRouter()


@router.post("/", response_model=TaxParam)
def create_tax_param(payload: TaxParamCreate) -> TaxParam:
    """
    Cria um novo parâmetro de alíquota (CBS/IBS) para um ano/UF/tipo.
    Persistência em arquivo JSON (sem banco relacional).
    """
    # Regra simples: não deixar duplicar ano+uf+tipo
    existing = tax_storage.list_params(
        ano=payload.ano, uf=payload.uf, tipo=payload.tipo
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Já existe um parâmetro cadastrado para este ano/UF/tipo.",
        )
    return tax_storage.create_param(payload)


@router.get("/", response_model=List[TaxParam])
def get_tax_params(
    ano: Optional[int] = Query(None),
    uf: Optional[str] = Query(None),
    tipo: Optional[str] = Query(None),
) -> List[TaxParam]:
    """
    Lista parâmetros cadastrados, com filtros opcionais por ano/UF/tipo.
    """
    return tax_storage.list_params(ano=ano, uf=uf, tipo=tipo)


@router.put("/{param_id}", response_model=TaxParam)
def update_tax_param(param_id: int, payload: TaxParamUpdate) -> TaxParam:
    updated = tax_storage.update_param(param_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="Parâmetro não encontrado.")
    return updated


@router.delete("/{param_id}", status_code=204)
def delete_tax_param(param_id: int) -> None:
    ok = tax_storage.delete_param(param_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Parâmetro não encontrado.")
