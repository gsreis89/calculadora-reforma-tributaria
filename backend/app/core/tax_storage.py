# backend/app/core/tax_storage.py
from __future__ import annotations

import json
from pathlib import Path
from typing import List

from app.schemas.tax_schedule import TaxParam, TaxParamCreate, TaxParamUpdate

DATA_FILE = Path("data/tax_params.json")


def _ensure_data_dir() -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)


def load_all() -> List[TaxParam]:
    """Lê todos os parâmetros do arquivo JSON."""
    if not DATA_FILE.exists():
        return []
    with DATA_FILE.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    return [TaxParam(**item) for item in raw]


def save_all(items: List[TaxParam]) -> None:
    """Salva todos os parâmetros no arquivo JSON."""
    _ensure_data_dir()
    serialized = [item.model_dump() for item in items]
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(serialized, f, ensure_ascii=False, indent=2)


def create_param(payload: TaxParamCreate) -> TaxParam:
    items = load_all()
    next_id = (max((p.id for p in items), default=0) + 1) if items else 1
    param = TaxParam(id=next_id, **payload.model_dump())
    items.append(param)
    save_all(items)
    return param


def list_params(
    ano: int | None = None,
    uf: str | None = None,
    tipo: str | None = None,
) -> List[TaxParam]:
    items = load_all()
    def _match(p: TaxParam) -> bool:
        if ano is not None and p.ano != ano:
            return False
        if uf is not None and p.uf != uf:
            return False
        if tipo is not None and p.tipo != tipo:
            return False
        return True

    return [p for p in items if _match(p)]


def update_param(param_id: int, payload: TaxParamUpdate) -> TaxParam | None:
    items = load_all()
    for idx, p in enumerate(items):
        if p.id == param_id:
            data = p.model_dump()
            upd = payload.model_dump(exclude_unset=True)
            data.update(upd)
            updated = TaxParam(**data)
            items[idx] = updated
            save_all(items)
            return updated
    return None


def delete_param(param_id: int) -> bool:
    items = load_all()
    new_items = [p for p in items if p.id != param_id]
    if len(new_items) == len(items):
        return False
    save_all(new_items)
    return True
