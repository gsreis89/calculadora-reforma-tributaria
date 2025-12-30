# backend/app/api/routes/simulator_v2.py
from __future__ import annotations

from datetime import date, datetime
from typing import Optional, Dict, Any, List, Tuple

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.services.database_service import get_status
from app.storage.dataset import Filters, query_dataset
from app.core.number import parse_money

from app.services.classifier_service import classify_movimento, classify_finalidade, safe_finalidade

router = APIRouter(prefix="/simulator", tags=["Simulator"])


# ------------------------
# Helpers
# ------------------------
def _to_date(s: str) -> date:
    return datetime.fromisoformat(s[:10]).date()


def _default_period() -> Tuple[date, date]:
    return date(2000, 1, 1), date(2100, 12, 31)


def _parse_row_date(raw: Any) -> Optional[date]:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None

    # tenta ISO primeiro
    try:
        return datetime.fromisoformat(s[:10]).date()
    except Exception:
        pass

    for fmt in ("%d/%m/%Y", "%Y%m%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            continue
    return None


def _num(v: Any) -> float:
    try:
        return float(parse_money(v))
    except Exception:
        return 0.0


def _month_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


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

    # Alíquotas (ex.: 0.088 = 8,8%)
    aliquota_cbs: float = Field(default=0.088, ge=0, le=1)
    aliquota_ibs: float = Field(default=0.010, ge=0, le=1)
    aliquota_is: float = Field(default=0.000, ge=0, le=1)

    # Crédito por finalidade (MVP):
    # - REVENDA: 1.0
    # - CONSUMO: 1.0
    # - ATIVO: 0.5 (placeholder: depois vira apropriação)
    # - TRANSFERENCIA: 0.0 (placeholder)
    # - OUTRAS: 0.0
    perc_credit_revenda: float = Field(default=1.0, ge=0, le=1)
    perc_credit_consumo: float = Field(default=1.0, ge=0, le=1)
    perc_credit_ativo: float = Field(default=0.5, ge=0, le=1)
    perc_credit_transfer: float = Field(default=0.0, ge=0, le=1)
    perc_credit_outras: float = Field(default=0.0, ge=0, le=1)

    # Glosa global simples (placeholder)
    perc_glosa: float = Field(default=0.0, ge=0, le=1)

    # Caixa (placeholder)
    prazo_medio_dias: int = Field(default=30, ge=0, le=365)


class BreakdownItem(BaseModel):
    key: str
    value: float


class FinalidadeItem(BaseModel):
    finalidade: str
    entrada_base: float
    credito_potencial: float
    glosa: float
    credito_aproveitado: float


class SeriesPointV3(BaseModel):
    period: str  # YYYY-MM

    saida_receita: float
    entrada_base: float

    atual_total: float

    reforma_bruta: float
    credito_aproveitado: float
    reforma_liquida: float

    impacto_caixa_estimado: float


class SimulatorRunResponseV3(BaseModel):
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
    series: List[SeriesPointV3] = []


# ------------------------
# Cálculo de crédito por finalidade
# ------------------------
def _credit_percent_for(finalidade: str, c: ScenarioParams) -> float:
    f = (finalidade or "").upper()
    if f == "REVENDA":
        return float(c.perc_credit_revenda)
    if f == "CONSUMO":
        return float(c.perc_credit_consumo)
    if f == "ATIVO":
        return float(c.perc_credit_ativo)
    if f == "TRANSFERENCIA":
        return float(c.perc_credit_transfer)
    return float(c.perc_credit_outras)


# ------------------------
# Endpoint v3
# ------------------------
@router.get("/v3/run", response_model=SimulatorRunResponseV3)
def run_v3(
    # filtros (iguais ao dashboard)
    periodo_inicio: Optional[str] = Query(default=None),
    periodo_fim: Optional[str] = Query(default=None),
    uf_origem: Optional[str] = Query(default=None),
    uf_destino: Optional[str] = Query(default=None),
    ncm: Optional[str] = Query(default=None),
    produto: Optional[str] = Query(default=None),
    cfop: Optional[str] = Query(default=None),

    # filtros extra v3
    movimento: Optional[str] = Query(default=None, description="ENTRADA|SAIDA (opcional)"),
    finalidade: Optional[str] = Query(default=None, description="REVENDA|CONSUMO|ATIVO|TRANSFERENCIA|OUTRAS (opcional)"),

    # cenário (parâmetros)
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
    prazo_medio_dias: int = Query(default=30, ge=0, le=365),
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
        prazo_medio_dias=prazo_medio_dias,
    )

    if not st.get("exists"):
        return SimulatorRunResponseV3(
            status=st,
            filtros={},
            cenario=cenario,
            base={"rows": 0, "saida_receita": 0.0, "entrada_base": 0.0},
            atual={"icms": 0.0, "pis": 0.0, "cofins": 0.0, "carga_total": 0.0},
            reforma={"cbs": 0.0, "ibs": 0.0, "is": 0.0, "carga_bruta": 0.0, "carga_liquida": 0.0},
            creditos={"credito_potencial": 0.0, "glosa": 0.0, "credito_aproveitado": 0.0},
            caixa={"prazo_medio_dias": cenario.prazo_medio_dias, "impacto_caixa_estimado": 0.0},
            breakdown_movimento=[],
            breakdown_finalidade=[],
            series=[],
        )

    d0, d1 = _default_period()
    if periodo_inicio:
        d0 = _to_date(periodo_inicio)
    if periodo_fim:
        d1 = _to_date(periodo_fim)

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

    # normalize filtros extra
    mov_filter = _up(movimento)
    fin_filter = safe_finalidade(finalidade)

    # buckets
    bucket_month: Dict[str, Dict[str, float]] = {}
    bucket_mov: Dict[str, float] = {"ENTRADA": 0.0, "SAIDA": 0.0}
    bucket_fin: Dict[str, Dict[str, float]] = {}

    # totais
    saida_receita = 0.0
    entrada_base = 0.0

    icms = pis = cofins = 0.0

    # reforma bruta (sobre SAÍDA)
    cbs = ibs = isel = 0.0

    # crédito (sobre ENTRADA, por finalidade)
    credito_potencial = 0.0
    glosa_total = 0.0
    credito_aproveitado = 0.0

    for r in rows:
        mov = classify_movimento(r)
        fin = classify_finalidade(r)

        if mov_filter in {"ENTRADA", "SAIDA"} and mov != mov_filter:
            continue
        if fin_filter and fin != fin_filter:
            continue

        # valores base do dataset (MVP)
        vprod = _num(r.get("vprod"))
        icms_i = _num(r.get("vicms_icms"))
        pis_i = _num(r.get("vpis"))
        cofins_i = _num(r.get("vcofins"))

        # atual (soma geral no recorte)
        icms += icms_i
        pis += pis_i
        cofins += cofins_i

        # base por movimento
        if mov == "SAIDA":
            saida_receita += vprod
            bucket_mov["SAIDA"] += vprod

            # reforma bruta: CBS/IBS/IS sobre receita de saída (MVP)
            cbs += vprod * float(cenario.aliquota_cbs)
            ibs += vprod * float(cenario.aliquota_ibs)
            isel += vprod * float(cenario.aliquota_is)

        else:
            entrada_base += vprod
            bucket_mov["ENTRADA"] += vprod

            # crédito potencial por finalidade (MVP)
            perc = _credit_percent_for(fin, cenario)
            base_trib = vprod * float(cenario.aliquota_cbs + cenario.aliquota_ibs + cenario.aliquota_is)
            cred_pot = base_trib * perc
            gl = cred_pot * float(cenario.perc_glosa)
            cred_ap = max(0.0, cred_pot - gl)

            credito_potencial += cred_pot
            glosa_total += gl
            credito_aproveitado += cred_ap

            fin_bucket = bucket_fin.setdefault(
                fin,
                {"entrada_base": 0.0, "credito_potencial": 0.0, "glosa": 0.0, "credito_aproveitado": 0.0},
            )
            fin_bucket["entrada_base"] += vprod
            fin_bucket["credito_potencial"] += cred_pot
            fin_bucket["glosa"] += gl
            fin_bucket["credito_aproveitado"] += cred_ap

        # série mensal (com base no período do documento)
        dr = _parse_row_date(r.get("dhemi") or r.get("dtemi") or r.get("dt_emissao"))
        if not dr:
            continue
        mk = _month_key(dr)
        b = bucket_month.setdefault(
            mk,
            {
                "saida_receita": 0.0,
                "entrada_base": 0.0,
                "atual_total": 0.0,
                "reforma_bruta": 0.0,
                "credito_aproveitado": 0.0,
            },
        )

        b["atual_total"] += (icms_i + pis_i + cofins_i)

        if mov == "SAIDA":
            b["saida_receita"] += vprod
            b["reforma_bruta"] += vprod * float(cenario.aliquota_cbs + cenario.aliquota_ibs + cenario.aliquota_is)
        else:
            b["entrada_base"] += vprod
            base_trib_m = vprod * float(cenario.aliquota_cbs + cenario.aliquota_ibs + cenario.aliquota_is)
            perc_m = _credit_percent_for(fin, cenario)
            cred_pot_m = base_trib_m * perc_m
            gl_m = cred_pot_m * float(cenario.perc_glosa)
            cred_ap_m = max(0.0, cred_pot_m - gl_m)
            b["credito_aproveitado"] += cred_ap_m

    carga_atual = icms + pis + cofins
    carga_bruta_reforma = cbs + ibs + isel
    carga_liquida_reforma = max(0.0, carga_bruta_reforma - credito_aproveitado)

    impacto_caixa_estimado = carga_liquida_reforma * (
        cenario.prazo_medio_dias / 30.0 if cenario.prazo_medio_dias else 0.0
    )

    # breakdown movimento
    breakdown_movimento = [
        BreakdownItem(key="SAIDA", value=float(bucket_mov["SAIDA"])),
        BreakdownItem(key="ENTRADA", value=float(bucket_mov["ENTRADA"])),
    ]

    # breakdown finalidade (ordenado por entrada_base desc)
    breakdown_finalidade: List[FinalidadeItem] = []
    for fin in sorted(bucket_fin.keys(), key=lambda k: bucket_fin[k]["entrada_base"], reverse=True):
        it = bucket_fin[fin]
        breakdown_finalidade.append(
            FinalidadeItem(
                finalidade=fin,
                entrada_base=float(it["entrada_base"]),
                credito_potencial=float(it["credito_potencial"]),
                glosa=float(it["glosa"]),
                credito_aproveitado=float(it["credito_aproveitado"]),
            )
        )

    # série mensal ordenada
    series_out: List[SeriesPointV3] = []
    for period in sorted(bucket_month.keys()):
        m = bucket_month[period]
        reforma_bruta_m = float(m["reforma_bruta"])
        credito_ap_m = float(m["credito_aproveitado"])
        reforma_liq_m = max(0.0, reforma_bruta_m - credito_ap_m)
        caixa_m = reforma_liq_m * (cenario.prazo_medio_dias / 30.0 if cenario.prazo_medio_dias else 0.0)

        series_out.append(
            SeriesPointV3(
                period=period,
                saida_receita=float(m["saida_receita"]),
                entrada_base=float(m["entrada_base"]),
                atual_total=float(m["atual_total"]),
                reforma_bruta=reforma_bruta_m,
                credito_aproveitado=credito_ap_m,
                reforma_liquida=float(reforma_liq_m),
                impacto_caixa_estimado=float(caixa_m),
            )
        )

    return SimulatorRunResponseV3(
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
        },
        cenario=cenario,
        base={
            "rows": len(rows),
            "saida_receita": float(saida_receita),
            "entrada_base": float(entrada_base),
        },
        atual={
            "icms": float(icms),
            "pis": float(pis),
            "cofins": float(cofins),
            "carga_total": float(carga_atual),
        },
        reforma={
            "cbs": float(cbs),
            "ibs": float(ibs),
            "is": float(isel),
            "carga_bruta": float(carga_bruta_reforma),
            "carga_liquida": float(carga_liquida_reforma),
        },
        creditos={
            "credito_potencial": float(credito_potencial),
            "glosa": float(glosa_total),
            "credito_aproveitado": float(credito_aproveitado),
        },
        caixa={
            "prazo_medio_dias": int(cenario.prazo_medio_dias),
            "impacto_caixa_estimado": float(impacto_caixa_estimado),
        },
        breakdown_movimento=breakdown_movimento,
        breakdown_finalidade=breakdown_finalidade,
        series=series_out,
    )
