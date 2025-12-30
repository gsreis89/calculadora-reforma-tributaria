# backend/app/api/routes/simulation_manual.py
from __future__ import annotations

from datetime import date, datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.database_service import get_status
from app.storage.dataset import Filters, query_dataset
from app.core.number import parse_money


router = APIRouter(tags=["Simulação"])


def _to_date(s: str) -> date:
    # aceita "YYYY-MM-DD" (input date do frontend)
    try:
        return datetime.fromisoformat(s[:10]).date()
    except Exception:
        raise ValueError(f"Data inválida: {s}")


def _num(v: Optional[str]) -> float:
    try:
        return float(parse_money(v))
    except Exception:
        return 0.0


class SimulacaoDetalhadaRequest(BaseModel):
    # obrigatórios no seu Simulator.tsx
    periodo_inicio: str = Field(..., description="YYYY-MM-DD")
    periodo_fim: str = Field(..., description="YYYY-MM-DD")
    ano_reforma: int = Field(..., ge=2026, le=2033)

    # filtros opcionais
    uf_origem: Optional[str] = None
    uf_destino: Optional[str] = None
    ncm: Optional[str] = None
    produto: Optional[str] = None
    cfop: Optional[str] = None

    # parâmetros opcionais (se você quiser evoluir depois)
    # por enquanto o endpoint usa alíquotas fixas default
    alic_cbs: Optional[float] = None
    alic_ibs: Optional[float] = None
    alic_is: Optional[float] = None
    ncm_seletivo: Optional[List[str]] = None


@router.post("/simulacao-detalhada")
def simulacao_detalhada(payload: SimulacaoDetalhadaRequest) -> Dict[str, Any]:
    """
    Responde no formato que o frontend/src/pages/Simulator.tsx espera:
    {
      periodo_inicio, periodo_fim, ano_reforma,
      receita_total, carga_atual_total, carga_reforma_total,
      diferenca_percentual,
      detalhes: [{tributo, valor_atual, valor_reforma}, ...]
    }
    """

    st = get_status()
    if not st.get("exists"):
        raise HTTPException(status_code=400, detail="Base não encontrada. Faça upload do CSV.")

    try:
        d0 = _to_date(payload.periodo_inicio)
        d1 = _to_date(payload.periodo_fim)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if d0 > d1:
        raise HTTPException(status_code=400, detail="Período inválido: início maior que fim.")

    # normalização simples
    uf_origem = (payload.uf_origem or "").strip().upper() or None
    uf_destino = (payload.uf_destino or "").strip().upper() or None
    ncm = (payload.ncm or "").strip() or None
    produto = (payload.produto or "").strip() or None
    cfop = (payload.cfop or "").strip() or None

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

    receita_total = 0.0
    icms_atual = 0.0
    pis_atual = 0.0
    cofins_atual = 0.0

    for r in rows:
        receita_total += _num(r.get("vprod"))
        icms_atual += _num(r.get("vicms_icms"))
        pis_atual += _num(r.get("vpis"))
        cofins_atual += _num(r.get("vcofins"))

    carga_atual = icms_atual + pis_atual + cofins_atual

    # Defaults do MVP (os mesmos que você vinha usando no compare)
    # Você pode depois ligar isso em tabela de parâmetros (tax_params).
    ano = int(payload.ano_reforma)

    cbs = payload.alic_cbs if payload.alic_cbs is not None else (0.0880 if ano >= 2027 else 0.0090)
    ibs = payload.alic_ibs if payload.alic_ibs is not None else (0.0100 if ano >= 2027 else 0.0010)
    alic_is = payload.alic_is if payload.alic_is is not None else 0.0

    # IS seletivo (por NCM) — opcional
    seletivos = set([x.strip() for x in (payload.ncm_seletivo or []) if x and x.strip()])

    valor_cbs = receita_total * float(cbs)
    valor_ibs = receita_total * float(ibs)

    # IS: só aplica se vier lista de NCM seletivo + alíquota > 0
    valor_is = 0.0
    if seletivos and alic_is > 0:
        for r in rows:
            if (r.get("ncm") or "").strip() in seletivos:
                valor_is += _num(r.get("vprod")) * float(alic_is)

    # transição simplificada do MVP: 2027+ zera PIS/COFINS
    if ano >= 2027:
        pis_reforma = 0.0
        cofins_reforma = 0.0
    else:
        pis_reforma = pis_atual
        cofins_reforma = cofins_atual

    icms_reforma = icms_atual

    carga_reforma = icms_reforma + pis_reforma + cofins_reforma + valor_cbs + valor_ibs + valor_is

    dif_pct = ((carga_reforma - carga_atual) / carga_atual) * 100.0 if carga_atual else 0.0

    detalhes = [
        {"tributo": "ICMS", "valor_atual": float(icms_atual), "valor_reforma": float(icms_reforma)},
        {"tributo": "PIS", "valor_atual": float(pis_atual), "valor_reforma": float(pis_reforma)},
        {"tributo": "COFINS", "valor_atual": float(cofins_atual), "valor_reforma": float(cofins_reforma)},
        {"tributo": "CBS", "valor_atual": 0.0, "valor_reforma": float(valor_cbs)},
        {"tributo": "IBS", "valor_atual": 0.0, "valor_reforma": float(valor_ibs)},
    ]

    if valor_is > 0:
        detalhes.append({"tributo": "IS", "valor_atual": 0.0, "valor_reforma": float(valor_is)})

    return {
        "periodo_inicio": payload.periodo_inicio,
        "periodo_fim": payload.periodo_fim,
        "ano_reforma": ano,
        "receita_total": float(receita_total),
        "carga_atual_total": float(carga_atual),
        "carga_reforma_total": float(carga_reforma),
        "diferenca_percentual": float(dif_pct),
        "detalhes": detalhes,
    }
