# backend/app/api/routes/database.py
from __future__ import annotations

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import Response

from fastapi import APIRouter, HTTPException
from app.services.database_service import clear_dataset

from app.schemas.database import DatabaseStatus, DatabaseSummary, ImportCsvResponse
from app.services.database_service import (
    get_status,
    get_summary,
    import_csv_bytes,
    get_template_csv_bytes,
)

router = APIRouter(prefix="/database", tags=["Database"])

@router.delete("/clear-dataset")
async def clear_dataset_endpoint():
    try:
        clear_dataset()  # Chama a função para limpar a base de dados
        return {"message": "Base de dados limpa com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao limpar base de dados: {str(e)}")


@router.get("/status", response_model=DatabaseStatus)
def database_status():
    return get_status()


@router.get("/summary", response_model=DatabaseSummary)
def database_summary():
    return get_summary()


@router.get("/template-csv")
def template_csv():
    content = get_template_csv_bytes()
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=template_nfe_itens.csv"},
    )


@router.post("/import-csv", response_model=ImportCsvResponse)
async def import_csv(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Envie um arquivo .csv")

    raw = await file.read()
    try:
        imported = import_csv_bytes(raw)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Falha interna ao importar CSV")

    st = get_status()
    return {"imported_rows": imported, "path": st["path"]}
