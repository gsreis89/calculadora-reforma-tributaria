# backend/app/schemas/database.py
from __future__ import annotations

from pydantic import BaseModel
from typing import List, Optional


class DatabaseStatus(BaseModel):
    exists: bool
    path: str
    rows: int


class DatabaseSummary(BaseModel):
    exists: bool
    path: str
    rows: int
    min_date: Optional[str] = None
    max_date: Optional[str] = None
    ufs_origem: List[str] = []
    ufs_destino: List[str] = []
    receita_total: float = 0.0
    icms_total: float = 0.0
    pis_total: float = 0.0
    cofins_total: float = 0.0


class ImportCsvResponse(BaseModel):
    imported_rows: int
    path: str
