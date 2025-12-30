import json
import os
from typing import List, Optional
from uuid import uuid4

from app.schemas.tax_params import TaxParamCreate, TaxParamItem, TaxParamUpdate


_STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage")
_STORAGE_FILE = os.path.join(_STORAGE_DIR, "tax_params.json")


def _ensure_storage() -> None:
    os.makedirs(_STORAGE_DIR, exist_ok=True)
    if not os.path.exists(_STORAGE_FILE):
        with open(_STORAGE_FILE, "w", encoding="utf-8") as f:
            json.dump({"items": []}, f, ensure_ascii=False, indent=2)


def _load() -> dict:
    _ensure_storage()
    with open(_STORAGE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data: dict) -> None:
    _ensure_storage()
    with open(_STORAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def list_params() -> List[TaxParamItem]:
    data = _load()
    return [TaxParamItem(**x) for x in data.get("items", [])]


def create_param(payload: TaxParamCreate) -> TaxParamItem:
    data = _load()
    items = data.get("items", [])

    # regra: não duplicar mesma chave (ano, uf, tipo)
    for it in items:
        if it["ano"] == payload.ano and it.get("uf") == payload.uf and it["tipo"] == payload.tipo:
            # atualiza em vez de duplicar
            it["aliquota"] = payload.aliquota
            it["descricao"] = payload.descricao
            _save(data)
            return TaxParamItem(**it)

    new_item = {
        "id": str(uuid4()),
        "ano": payload.ano,
        "uf": payload.uf,
        "tipo": payload.tipo,
        "aliquota": payload.aliquota,
        "descricao": payload.descricao,
    }
    items.append(new_item)
    data["items"] = items
    _save(data)
    return TaxParamItem(**new_item)


def update_param(param_id: str, payload: TaxParamUpdate) -> TaxParamItem:
    data = _load()
    items = data.get("items", [])

    for it in items:
        if it["id"] == param_id:
            if payload.aliquota is not None:
                it["aliquota"] = payload.aliquota
            if payload.descricao is not None:
                it["descricao"] = payload.descricao
            _save(data)
            return TaxParamItem(**it)

    raise ValueError("Parametro não encontrado")


def delete_param(param_id: str) -> None:
    data = _load()
    items = data.get("items", [])
    new_items = [it for it in items if it["id"] != param_id]
    data["items"] = new_items
    _save(data)


def get_rate(ano: int, tipo: str, uf: Optional[str] = None, default: float = 0.0) -> float:
    """
    Busca taxa por (ano, tipo, uf).
    Se não achar por UF, tenta UF = None (geral).
    """
    data = _load()
    items = data.get("items", [])

    # 1) tenta com UF específica
    for it in items:
        if it["ano"] == ano and it["tipo"] == tipo and it.get("uf") == uf:
            return float(it["aliquota"])

    # 2) tenta geral (uf null)
    for it in items:
        if it["ano"] == ano and it["tipo"] == tipo and it.get("uf") is None:
            return float(it["aliquota"])

    return default
