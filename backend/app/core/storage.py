# backend/app/core/storage.py
from __future__ import annotations

from pathlib import Path


def get_data_dir() -> Path:
    # backend/app/core/storage.py -> backend/app/core -> backend/app -> backend
    backend_dir = Path(__file__).resolve().parents[2]
    data_dir = backend_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_tax_params_path() -> Path:
    return get_data_dir() / "tax_params.json"
