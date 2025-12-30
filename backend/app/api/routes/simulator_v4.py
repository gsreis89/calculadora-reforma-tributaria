# backend/app/api/routes/simulator_v4.py
from __future__ import annotations

from datetime import date, datetime
from typing import Optional, Dict, Any, List, Tuple

import json
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.services.database_service import get_status
from app.storage.dataset import Filters, query_dataset

from app.services.classifier_service import safe_finalidade

# Engine v4 (novo)
from app.services.simulator_engine.dto_v4 import Scenario as EngineScenario, RunFilters as EngineRunFilters
from app.services.simulator_engine.engine_v4 import run_engine_v4

router = APIRouter(prefix="/simulator", tags=["Simulator v4"])


# ------------------------
# Helpers
# ------------------------

def _to_date(s: str) -> date:
    return datetime.fromisoformat(s[:10]).date()


def _default_period() -> Tuple[date, date]:
    return date(2000, 1, 1), date(2100, 12, 31)


def _up(v: Optional[str]) -> Optional[str]:
    if not v:
        return None
    s = str(v).strip().upper()
    return s or None


# ------------------------
# Scenario (parametrizável)
# ------------------------

class ScenarioParams(BaseModel):
    nome: str = Field(default="Cenário Base Reforma")

    aliquota_cbs: float = Field(default=0.088, ge=0, le=1)
    aliquota_ibs: float = Field(default=0.010, ge=0, le=1)
    aliquota_is: float = Field(default=0.000, ge=0, le=1)

    # Crédito por finalidade (MVP)
    perc_credit_revenda: float = Field(default=1.0, ge=0, le=1)
    perc_credit_consumo: float = Field(default=1.0, ge=0, le=1)
    perc_credit_ativo: float = Field(default=0.5, ge=0, le=1)
    perc_credit_transfer: float = Field(default=0.0, ge=0, le=1)
    perc_credit_outras: float = Field(default=0.0, ge=0, le=1)

    perc_glosa: float = Field(default=0.0, ge=0, le=1)

    # ATIVO por apropriação: ex. 48 meses
    ativo_meses: int = Field(default=48, ge=1, le=240)

    # Caixa (placeholder)
    prazo_medio_dias: int = Field(default=30, ge=0, le=365)

    split_percent: float = Field(default=0.0, ge=0, le=1)
    delay_days: int = Field(default=0, ge=0, le=365)
    residual_installments: int = Field(default=1, ge=1, le=120)
    residual_start_offset_months: int = Field(default=0, ge=0, le=60)



class BreakdownItem(BaseModel):
    key: str
    value: float


class FinalidadeItem(BaseModel):
    finalidade: str
    entrada_base: float
    credito_potencial: float
    glosa: float
    credito_aproveitado: float
    credito_apropriado_no_periodo: float


class SeriesPointV4(BaseModel):
    period: str  # YYYY-MM

    saida_receita: float
    entrada_base: float

    atual_total: float

    reforma_bruta: float
    credito_aproveitado: float  # crédito apropriado naquele mês (ATIVO 1/N)
    reforma_liquida: float

    impacto_caixa_estimado: float


class RuleItem(BaseModel):
    """Regra simples:

    - match: "cfop" | "cfop_prefix" | "ncm" | "ncm_prefix"
    - value: string (ex: "1556" ou "11" etc)
    - finalidade: opcional (REVENDA/CONSUMO/ATIVO/TRANSFERENCIA/OUTRAS)
    - perc_credit: opcional (0..1) sobrescreve o percentual da finalidade
    - perc_glosa: opcional (0..1) sobrescreve a glosa global (só quando a regra bate)

    Prioridade por ordem: a primeira regra que bater encerra.
    """

    match: str
    value: str
    finalidade: Optional[str] = None
    perc_credit: Optional[float] = Field(default=None, ge=0, le=1)
    perc_glosa: Optional[float] = Field(default=None, ge=0, le=1)


class SimulatorRunResponseV4(BaseModel):
    status: Dict[str, Any]
    filtros: Dict[str, Any]
    cenario: ScenarioParams

    base: Dict[str, Any]
    atual: Dict[str, Any]
    reforma: Dict[str, Any]
    creditos: Dict[str, Any]
    caixa: Dict[str, Any]

    breakdown_movimento: List[BreakdownItem] = []
    breakdown_finalidade: List[FinalidadeItem] = []
    series: List[SeriesPointV4] = []

    # v5+
    credit_ledger: Optional[Dict[str, Any]] = None

    # v6+
    cash_ledger: Optional[Dict[str, Any]] = None


# ------------------------
# Endpoint v4 (route fino)
# ------------------------

@router.get("/v4/run", response_model=SimulatorRunResponseV4)
def run_v4(
    # filtros (iguais ao dashboard)
    periodo_inicio: Optional[str] = Query(default=None),
    periodo_fim: Optional[str] = Query(default=None),
    uf_origem: Optional[str] = Query(default=None),
    uf_destino: Optional[str] = Query(default=None),
    ncm: Optional[str] = Query(default=None),
    produto: Optional[str] = Query(default=None),
    cfop: Optional[str] = Query(default=None),

    # filtros extra
    movimento: Optional[str] = Query(default=None, description="ENTRADA|SAIDA (opcional)"),
    finalidade: Optional[str] = Query(
        default=None,
        description="REVENDA|CONSUMO|ATIVO|TRANSFERENCIA|OUTRAS (opcional)",
    ),

    # cenário
    nome: str = Query(default="Cenário Base Reforma"),
    aliquota_cbs: float = Query(default=0.088, ge=0, le=1),
    aliquota_ibs: float = Query(default=0.010, ge=0, le=1),
    aliquota_is: float = Query(default=0.0, ge=0, le=1),

    perc_credit_revenda: float = Query(default=1.0, ge=0, le=1),
    perc_credit_consumo: float = Query(default=1.0, ge=0, le=1),
    perc_credit_ativo: float = Query(default=0.5, ge=0, le=1),
    perc_credit_transfer: float = Query(default=0.0, ge=0, le=1),
    perc_credit_outras: float = Query(default=0.0, ge=0, le=1),

    perc_glosa: float = Query(default=0.0, ge=0, le=1),
    ativo_meses: int = Query(default=48, ge=1, le=240),
    prazo_medio_dias: int = Query(default=30, ge=0, le=365),

    # regras por CFOP/NCM (JSON em string)
    regras_json: Optional[str] = Query(default=None),
):
    st = get_status()

    cenario = ScenarioParams(
        nome=nome,
        aliquota_cbs=aliquota_cbs,
        aliquota_ibs=aliquota_ibs,
        aliquota_is=aliquota_is,
        perc_credit_revenda=perc_credit_revenda,
        perc_credit_consumo=perc_credit_consumo,
        perc_credit_ativo=perc_credit_ativo,
        perc_credit_transfer=perc_credit_transfer,
        perc_credit_outras=perc_credit_outras,
        perc_glosa=perc_glosa,
        ativo_meses=ativo_meses,
        prazo_medio_dias=prazo_medio_dias,
    )

    # Se não existe dataset carregado, mantém resposta vazia compatível
    if not st.get("exists"):
        return SimulatorRunResponseV4(
            status=st,
            filtros={},
            cenario=cenario,
            base={"rows": 0, "saida_receita": 0.0, "entrada_base": 0.0},
            atual={"icms": 0.0, "pis": 0.0, "cofins": 0.0, "carga_total": 0.0},
            reforma={"cbs": 0.0, "ibs": 0.0, "is": 0.0, "carga_bruta": 0.0, "carga_liquida": 0.0},
            creditos={
                "credito_potencial": 0.0,
                "glosa": 0.0,
                "credito_aproveitado": 0.0,
                "credito_apropriado_no_periodo": 0.0,
            },
            caixa={"prazo_medio_dias": cenario.prazo_medio_dias, "impacto_caixa_estimado": 0.0},
            breakdown_movimento=[],
            breakdown_finalidade=[],
            series=[],
            credit_ledger=None,
            cash_ledger=None,
        )

    # Período
    d0, d1 = _default_period()
    if periodo_inicio:
        d0 = _to_date(periodo_inicio)
    if periodo_fim:
        d1 = _to_date(periodo_fim)

    # Dataset (filtros iguais ao dashboard)
    rows = query_dataset(
        Filters(
            periodo_inicio=d0,
            periodo_fim=d1,
            uf_origem=uf_origem,
            uf_destino=uf_destino,
            ncm=ncm,
            produto=produto,
            cfop=cfop,
        )
    )

    mov_filter = _up(movimento)
    fin_filter = safe_finalidade(finalidade)

    # DTOs do engine (desacoplados)
    engine_filters = EngineRunFilters(
        periodo_inicio=d0,
        periodo_fim=d1,
        uf_origem=_up(uf_origem),
        uf_destino=_up(uf_destino),
        ncm=(ncm or "").strip() or None,
        produto=(produto or "").strip() or None,
        cfop=(cfop or "").strip() or None,
        movimento=mov_filter,
        finalidade=fin_filter,
        regras_json=regras_json,
    )

    engine_scenario = EngineScenario(
        nome=cenario.nome,
        aliquota_cbs=float(cenario.aliquota_cbs),
        aliquota_ibs=float(cenario.aliquota_ibs),
        aliquota_is=float(cenario.aliquota_is),
        perc_credit_revenda=float(cenario.perc_credit_revenda),
        perc_credit_consumo=float(cenario.perc_credit_consumo),
        perc_credit_ativo=float(cenario.perc_credit_ativo),
        perc_credit_transfer=float(cenario.perc_credit_transfer),
        perc_credit_outras=float(cenario.perc_credit_outras),
        perc_glosa=float(cenario.perc_glosa),
        ativo_meses=int(cenario.ativo_meses),
        prazo_medio_dias=int(cenario.prazo_medio_dias),
        split_percent=float(cenario.split_percent),
        delay_days=int(cenario.delay_days),
        residual_installments=int(cenario.residual_installments),
        residual_start_offset_months=int(cenario.residual_start_offset_months),
    )

    res = run_engine_v4(rows=rows, f=engine_filters, c=engine_scenario)

    return SimulatorRunResponseV4(
        status=st,
        filtros={
            "periodo_inicio": d0.isoformat(),
            "periodo_fim": d1.isoformat(),
            "uf_origem": _up(uf_origem),
            "uf_destino": _up(uf_destino),
            "ncm": (ncm or "").strip() or None,
            "produto": (produto or "").strip() or None,
            "cfop": (cfop or "").strip() or None,
            "movimento": mov_filter,
            "finalidade": fin_filter,
            "regras_json": regras_json,
        },
        cenario=cenario,
        base=res.base,
        atual=res.atual,
        reforma=res.reforma,
        creditos=res.creditos,
        caixa=res.caixa,
        breakdown_movimento=[BreakdownItem(**x) for x in res.breakdown_movimento],
        breakdown_finalidade=[FinalidadeItem(**x) for x in res.breakdown_finalidade],
        series=[SeriesPointV4(**x) for x in res.series],
        credit_ledger=res.credit_ledger,
        cash_ledger=res.cash_ledger,
    )
