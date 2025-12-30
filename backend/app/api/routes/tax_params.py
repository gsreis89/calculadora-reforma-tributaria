from fastapi import APIRouter, HTTPException
from typing import List

from app.schemas.tax_params import TaxParamCreate, TaxParamItem, TaxParamUpdate
from app.services.tax_params_service import list_params, create_param, update_param, delete_param

router = APIRouter(prefix="/tax-params", tags=["Tax Params"])


@router.get("/", response_model=List[TaxParamItem])
def get_all():
    return list_params()


@router.post("/", response_model=TaxParamItem)
def create(payload: TaxParamCreate):
    return create_param(payload)


@router.put("/{param_id}", response_model=TaxParamItem)
def update(param_id: str, payload: TaxParamUpdate):
    try:
        return update_param(param_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{param_id}")
def delete(param_id: str):
    delete_param(param_id)
    return {"ok": True}
