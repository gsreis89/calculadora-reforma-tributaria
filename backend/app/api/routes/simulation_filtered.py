# backend/app/api/routes/simulation_filtered.py
from datetime import datetime
from fastapi import APIRouter, HTTPException

from app.schemas.simulation_filtered import (
    SimulationFilteredRequest,
    SimulationFilteredResponse,
    TributoDetalhe,
)
from app.storage.dataset import Filters, query_dataset, sum_field
from app.services.tax_params_service import get_rate

router = APIRouter(tags=["Simulação (base histórica)"])


def _r2(v: float) -> float:
    return float(f"{v:.2f}")


def _to_date(s: str):
    return datetime.fromisoformat(s[:10]).date()


@router.post("/simulacao-detalhada", response_model=SimulationFilteredResponse)
def simular(payload: SimulationFilteredRequest):
    # valida se existe base
    try:
        rows = query_dataset(
            Filters(
                periodo_inicio=_to_date(payload.periodo_inicio),
                periodo_fim=_to_date(payload.periodo_fim),
                uf_origem=payload.uf_origem,
                uf_destino=payload.uf_destino,
                ncm=payload.ncm,
                produto=payload.produto,
            )
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    receita_total = sum_field(rows, "vprod")
    icms_atual = sum_field(rows, "vicms_icms")
    pis_atual = sum_field(rows, "vpis")
    cofins_atual = sum_field(rows, "vcofins")

    carga_atual = icms_atual + pis_atual + cofins_atual

    # Reforma: CBS/IBS por UF origem (você pode trocar lógica depois)
    uf_ref = (payload.uf_origem or "BR").upper()
    cbs = get_rate(payload.ano_reforma, uf_ref, "CBS_PADRAO") or (0.0880 if payload.ano_reforma >= 2027 else 0.0090)
    ibs = get_rate(payload.ano_reforma, uf_ref, "IBS_PADRAO") or (0.0100 if payload.ano_reforma >= 2027 else 0.0010)

    # Base de CBS/IBS: neste MVP, usamos receita_total (vprod)
    valor_cbs = receita_total * float(cbs)
    valor_ibs = receita_total * float(ibs)

    if payload.ano_reforma >= 2027:
        pis_reforma = 0.0
        cofins_reforma = 0.0
    else:
        pis_reforma = pis_atual
        cofins_reforma = cofins_atual

    icms_reforma = icms_atual

    carga_reforma = icms_reforma + pis_reforma + cofins_reforma + valor_cbs + valor_ibs
    dif_abs = carga_reforma - carga_atual
    dif_pct = (dif_abs / carga_atual) * 100.0 if carga_atual else 0.0

    detalhes = [
        TributoDetalhe(tributo="ICMS", valor_atual=_r2(icms_atual), valor_reforma=_r2(icms_reforma)),
        TributoDetalhe(tributo="PIS", valor_atual=_r2(pis_atual), valor_reforma=_r2(pis_reforma)),
        TributoDetalhe(tributo="COFINS", valor_atual=_r2(cofins_atual), valor_reforma=_r2(cofins_reforma)),
        TributoDetalhe(tributo="CBS", valor_atual=0.0, valor_reforma=_r2(valor_cbs)),
        TributoDetalhe(tributo="IBS", valor_atual=0.0, valor_reforma=_r2(valor_ibs)),
    ]

    return SimulationFilteredResponse(
        periodo_inicio=payload.periodo_inicio,
        periodo_fim=payload.periodo_fim,
        ano_reforma=payload.ano_reforma,
        receita_total=_r2(receita_total),
        carga_atual_total=_r2(carga_atual),
        carga_reforma_total=_r2(carga_reforma),
        diferenca_absoluta=_r2(dif_abs),
        diferenca_percentual=_r2(dif_pct),
        detalhes=detalhes,
    )
