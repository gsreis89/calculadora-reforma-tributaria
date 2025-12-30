# backend/app/api/routes/database_summary.py
from pathlib import Path

from fastapi import APIRouter

from app.services.database_summary_service import build_summary

router = APIRouter(prefix="/database", tags=["Base de Dados"])

# Ajuste aqui para o mesmo local onde você salva o CSV no import.
DATASET_PATH = Path("storage") / "nfe_itens.csv"


@router.get("/summary")
def get_summary():
    s = build_summary(DATASET_PATH)
    return {
        "exists": s.exists,
        "path": s.path,
        "rows": s.rows,
        "min_date": s.min_date,
        "max_date": s.max_date,
        "ufs_origem": s.ufs_origem,
        "ufs_destino": s.ufs_destino,
        "receita_total": s.receita_total,
        "icms_total": s.icms_total,
        "pis_total": s.pis_total,
        "cofins_total": s.cofins_total,
    }
