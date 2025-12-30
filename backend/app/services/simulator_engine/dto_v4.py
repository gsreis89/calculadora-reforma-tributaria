# backend/app/services/simulator_engine/dto_v4.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, Optional


@dataclass
class RunFilters:
    periodo_inicio: date
    periodo_fim: date

    uf_origem: Optional[str] = None
    uf_destino: Optional[str] = None
    ncm: Optional[str] = None
    produto: Optional[str] = None
    cfop: Optional[str] = None

    movimento: Optional[str] = None
    finalidade: Optional[str] = None

    regras_json: Optional[str] = None


@dataclass
class Scenario:
    nome: str = "Cenário Base Reforma"

    aliquota_cbs: float = 0.088
    aliquota_ibs: float = 0.010
    aliquota_is: float = 0.0

    perc_credit_revenda: float = 1.0
    perc_credit_consumo: float = 1.0
    perc_credit_ativo: float = 0.5
    perc_credit_transfer: float = 0.0
    perc_credit_outras: float = 0.0

    perc_glosa: float = 0.0

    ativo_meses: int = 48

    prazo_medio_dias: int = 30

    split_percent: float = 0.0
    delay_days: int = 0
    residual_installments: int = 1
    residual_start_offset_months: int = 0



@dataclass
class Rule:
    match: str
    value: str
    finalidade: Optional[str] = None
    perc_credit: Optional[float] = None
    perc_glosa: Optional[float] = None


@dataclass
class EngineResult:
    # blocos base do v4
    base: Dict[str, Any]
    atual: Dict[str, Any]
    reforma: Dict[str, Any]
    creditos: Dict[str, Any]
    caixa: Dict[str, Any]

    breakdown_movimento: Any
    breakdown_finalidade: Any
    series: Any

    # v5+: blocos adicionais (opcionais)
    credit_ledger: Optional[Dict[str, Any]] = None

    # v6+: cash ledger (competência x caixa)
    cash_ledger: Optional[Dict[str, Any]] = None
