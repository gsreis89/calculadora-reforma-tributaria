from __future__ import annotations

from pathlib import Path

from app.core.classifier import classificar_finalidade
from app.core.fiscal_item import FiscalItem

# Pasta "data" dentro do backend (ajuste se quiser outro local)
BASE_DIR = Path(__file__).resolve().parents[2]  # .../backend
DATA_DIR = BASE_DIR / "data"
DATASET_PATH = DATA_DIR / "dataset_nfe_itens.csv"


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
