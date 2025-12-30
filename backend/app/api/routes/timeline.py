from fastapi import APIRouter
from app.services.tax_timeline_service import get_timeline, get_year_config, list_years

router = APIRouter(prefix="/tax-timeline", tags=["timeline"])

@router.get("")
def read_timeline():
    return get_timeline()

@router.get("/years")
def read_years():
    return list_years()

@router.get("/{ano}")
def read_year(ano: int):
    return get_year_config(ano)
