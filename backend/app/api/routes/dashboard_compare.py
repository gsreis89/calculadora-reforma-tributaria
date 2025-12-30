from __future__ import annotations

from fastapi import APIRouter, Query
from app.schemas.dashboard_compare import DashboardCompareResponse
from app.services.dashboard_compare_service import dashboard_compare

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/compare", response_model=DashboardCompareResponse)
def compare_dashboard(ano_reforma: int = Query(2027, ge=2026, le=2033)):
    return dashboard_compare(ano_reforma)
