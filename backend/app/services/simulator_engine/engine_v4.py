# backend/app/services/simulator_engine/engine_v4.py
from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from app.core.number import parse_money
from app.services.classifier_service import (
    classify_movimento,
    classify_finalidade,
    safe_finalidade,
)

from app.services.simulator_engine.dto_v4 import EngineResult, RunFilters, Scenario, Rule
from app.services.simulator_engine.dates_v4 import (
    parse_row_date,
    month_key,
    add_months_first_day,
)
from app.services.simulator_engine.rules_v4 import apply_rules

from app.services.simulator_engine.credit_ledger import build_credit_ledger
from app.services.simulator_engine.credit_events import (
    CreditEventV2,
    add_credit_events_for_item,
)
from app.services.simulator_engine.credit_aggregations import (
    top_by,
    aging_saldo_a_apropriar,
)

from app.services.simulator_engine.cash_ledger import build_cash_ledger

from app.services.simulator_engine.cash_ledger_v2 import build_cash_ledger_v2, CashLedgerConfigV2




# ------------------------
# Helpers
# ------------------------

def _num(v: Any) -> float:
    try:
        return float(parse_money(v))
    except Exception:
        return 0.0


def _up(v: Optional[str]) -> Optional[str]:
    if not v:
        return None
    s = str(v).strip().upper()
    return s or None


# ------------------------
# Rules JSON
# ------------------------

def parse_rules_json(raw: Optional[str]) -> List[Rule]:
    if not raw:
        return []
    try:
        obj = json.loads(raw)
        if not isinstance(obj, list):
            return []
        out: List[Rule] = []
        for it in obj:
            if not isinstance(it, dict):
                continue
            out.append(
                Rule(
                    match=str(it.get("match") or ""),
                    value=str(it.get("value") or ""),
                    finalidade=it.get("finalidade"),
                    perc_credit=it.get("perc_credit"),
                    perc_glosa=it.get("perc_glosa"),
                )
            )
        return out
    except Exception:
        return []


# ------------------------
# Engine v4 (v5.2: credit ledger nível 2)
# ------------------------

def run_engine_v4(*, rows: List[dict], f: RunFilters, c: Scenario) -> EngineResult:
    """Executa a simulação v4 em cima de `rows` (list[dict]) já filtradas pelo dataset.py.

    Otimizações incluídas:
    - Usa o campo `movimento` do CSV como fonte de verdade (fallback para classificador).
    - Otimiza apropriação de ATIVO: agrega crédito por mês de emissão e distribui por mês,
      evitando loop N-meses por linha.

    v5.1:
    - Anexa credit_ledger (nível 1): summary/series/by_finalidade.

    v5.2:
    - Gera eventos por item (CreditEventV2) e adiciona:
      - tops (NCM/CFOP/Produto)
      - aging do saldo a apropriar

    Mantém o contrato do Simulator v4; campos novos são adicionados no bloco credit_ledger.
    """

    rules = parse_rules_json(f.regras_json)

    mov_filter = _up(f.movimento)
    fin_filter = safe_finalidade(f.finalidade)

    # buckets
    bucket_month: Dict[str, Dict[str, float]] = {}
    bucket_mov: Dict[str, float] = {"ENTRADA": 0.0, "SAIDA": 0.0}
    bucket_fin: Dict[str, Dict[str, float]] = {}

    # crédito apropriado por mês (após regra ATIVO)
    credit_alloc_month: Dict[str, float] = {}

    # Para otimizar ATIVO: soma de crédito (já após glosa) por mês de emissão
    ativo_credit_by_emission_month: Dict[str, float] = {}

    # Eventos de crédito (nível 2)
    credit_events: List[CreditEventV2] = []

    # totais
    rows_filtradas = 0
    saida_receita = 0.0
    entrada_base = 0.0

    icms = pis = cofins = 0.0

    # reforma bruta (sobre SAÍDA)
    cbs = ibs = isel = 0.0

    # crédito potencial e glosa (calculados na entrada), e apropriado no período
    credito_potencial = 0.0
    glosa_total = 0.0
    credito_aproveitado_total = 0.0  # total teórico (antes da apropriação do ATIVO)
    credito_apropriado_no_periodo = 0.0  # soma que cai dentro do recorte retornado (KPI)

    # Normalizações locais para reduzir custo em loop
    aliq_total = float(c.aliquota_cbs + c.aliquota_ibs + c.aliquota_is)
    aliq_cbs = float(c.aliquota_cbs)
    aliq_ibs = float(c.aliquota_ibs)
    aliq_is = float(c.aliquota_is)

    for r in rows:
        # MOVIMENTO: fonte de verdade do CSV; fallback para classificador apenas se vier inválido
        mov = (r.get("movimento") or "").strip().upper()
        if mov not in {"ENTRADA", "SAIDA"}:
            mov = classify_movimento(r)

        # Finalidade: ainda vem do classificador (e pode ser sobrescrita por regra)
        fin_base = classify_finalidade(r)

        if mov_filter in {"ENTRADA", "SAIDA"} and mov != mov_filter:
            continue

        # regra por CFOP/NCM pode sobrescrever finalidade e percentuais
        fin_eff, perc_credit_eff, perc_glosa_eff = apply_rules(
            r,
            fin_base,
            c,
            rules,
            safe_finalidade_fn=safe_finalidade,
        )

        if fin_filter and fin_eff != fin_filter:
            continue

        rows_filtradas += 1

        vprod = _num(r.get("vprod"))
        icms_i = _num(r.get("vicms_icms"))
        pis_i = _num(r.get("vpis"))
        cofins_i = _num(r.get("vcofins"))

        icms += icms_i
        pis += pis_i
        cofins += cofins_i

        dr = parse_row_date(r.get("dhemi") or r.get("dtemi") or r.get("dt_emissao"))
        mk = month_key(dr) if dr else None

        # buckets do mês (se tiver data)
        if mk and mk not in bucket_month:
            bucket_month[mk] = {
                "saida_receita": 0.0,
                "entrada_base": 0.0,
                "atual_total": 0.0,
                "reforma_bruta": 0.0,
                "credito_aproveitado": 0.0,  # preenchido depois via credit_alloc_month
            }

        if mk:
            bucket_month[mk]["atual_total"] += (icms_i + pis_i + cofins_i)

        if mov == "SAIDA":
            saida_receita += vprod
            bucket_mov["SAIDA"] += vprod

            cbs += vprod * aliq_cbs
            ibs += vprod * aliq_ibs
            isel += vprod * aliq_is

            if mk:
                bucket_month[mk]["saida_receita"] += vprod
                bucket_month[mk]["reforma_bruta"] += vprod * aliq_total

        else:
            entrada_base += vprod
            bucket_mov["ENTRADA"] += vprod

            base_trib = vprod * aliq_total
            cred_pot = base_trib * float(perc_credit_eff)
            gl = cred_pot * float(perc_glosa_eff)
            cred_ap = max(0.0, cred_pot - gl)

            credito_potencial += cred_pot
            glosa_total += gl
            credito_aproveitado_total += cred_ap

            # EVENTOS (nível 2) — gera eventos por item (não altera totais)
            add_credit_events_for_item(
                out=credit_events,
                row=r,
                fin_eff=fin_eff,
                dr=dr,
                cred_pot=cred_pot,
                gl=gl,
                cred_ap=cred_ap,
                ativo_meses=int(max(1, c.ativo_meses)),
            )

            # acumula por finalidade (tabela)
            fin_bucket = bucket_fin.setdefault(
                fin_eff,
                {
                    "entrada_base": 0.0,
                    "credito_potencial": 0.0,
                    "glosa": 0.0,
                    "credito_aproveitado": 0.0,
                    "credito_apropriado_no_periodo": 0.0,
                },
            )
            fin_bucket["entrada_base"] += vprod
            fin_bucket["credito_potencial"] += cred_pot
            fin_bucket["glosa"] += gl
            fin_bucket["credito_aproveitado"] += cred_ap

            if mk:
                bucket_month[mk]["entrada_base"] += vprod

            # Apropriação:
            # - ATIVO: apropria 1/N meses a partir do mês do documento (otimizado via agregação por mês)
            # - demais finalidades: credita no próprio mês
            if mk:
                if fin_eff == "ATIVO":
                    # soma crédito do mês de emissão; a distribuição será feita após o loop
                    ativo_credit_by_emission_month[mk] = ativo_credit_by_emission_month.get(mk, 0.0) + cred_ap
                else:
                    credit_alloc_month[mk] = credit_alloc_month.get(mk, 0.0) + cred_ap
                    fin_bucket["credito_apropriado_no_periodo"] += cred_ap

    # ------------------------
    # Distribuição otimizada do ATIVO
    # ------------------------
    if ativo_credit_by_emission_month:
        n = int(max(1, c.ativo_meses))
        for mk_emit, total_cred_ap in ativo_credit_by_emission_month.items():
            portion = float(total_cred_ap) / float(n)

            # mk_emit é "YYYY-MM". Monta date do 1º dia do mês.
            y, m = mk_emit.split("-")
            base_month = date(int(y), int(m), 1)

            for i in range(n):
                dd = add_months_first_day(base_month, i)
                mm = month_key(dd)
                credit_alloc_month[mm] = credit_alloc_month.get(mm, 0.0) + portion

        # Para a tabela por finalidade: somar o apropriado no período para ATIVO
        ativo_bucket = bucket_fin.get("ATIVO")
        if ativo_bucket is not None:
            for mm, val in credit_alloc_month.items():
                if mm in bucket_month:
                    ativo_bucket["credito_apropriado_no_periodo"] += float(val)

    # ------------------------
    # Injeta crédito apropriado por mês nos buckets e computa KPI
    # ------------------------
    for mk, val in credit_alloc_month.items():
        if mk in bucket_month:
            bucket_month[mk]["credito_aproveitado"] += float(val)
            credito_apropriado_no_periodo += float(val)

    carga_atual = icms + pis + cofins
    carga_bruta_reforma = cbs + ibs + isel

    # v4: carga líquida considera o crédito apropriado NO PERÍODO
    carga_liquida_reforma = max(0.0, carga_bruta_reforma - credito_apropriado_no_periodo)

    impacto_caixa_estimado = carga_liquida_reforma * (
        c.prazo_medio_dias / 30.0 if c.prazo_medio_dias else 0.0
    )

    breakdown_movimento = [
        {"key": "SAIDA", "value": float(bucket_mov["SAIDA"])},
        {"key": "ENTRADA", "value": float(bucket_mov["ENTRADA"])},
    ]

    breakdown_finalidade: List[Dict[str, Any]] = []
    for fin in sorted(bucket_fin.keys(), key=lambda k: bucket_fin[k]["entrada_base"], reverse=True):
        it = bucket_fin[fin]
        breakdown_finalidade.append(
            {
                "finalidade": fin,
                "entrada_base": float(it["entrada_base"]),
                "credito_potencial": float(it["credito_potencial"]),
                "glosa": float(it["glosa"]),
                "credito_aproveitado": float(it["credito_aproveitado"]),
                "credito_apropriado_no_periodo": float(it["credito_apropriado_no_periodo"]),
            }
        )

    series_out: List[Dict[str, Any]] = []
    for period in sorted(bucket_month.keys()):
        m = bucket_month[period]
        reforma_bruta_m = float(m["reforma_bruta"])
        credito_ap_m = float(m["credito_aproveitado"])
        reforma_liq_m = max(0.0, reforma_bruta_m - credito_ap_m)
        caixa_m = reforma_liq_m * (c.prazo_medio_dias / 30.0 if c.prazo_medio_dias else 0.0)

        series_out.append(
            {
                "period": period,
                "saida_receita": float(m["saida_receita"]),
                "entrada_base": float(m["entrada_base"]),
                "atual_total": float(m["atual_total"]),
                "reforma_bruta": reforma_bruta_m,
                "credito_aproveitado": credito_ap_m,
                "reforma_liquida": float(reforma_liq_m),
                "impacto_caixa_estimado": float(caixa_m),
            }
        )

    # ------------------------
    # Credit Ledger v5.1 + v5.2
    # ------------------------
    credit_ledger = build_credit_ledger(
        alloc_by_month=credit_alloc_month,
        fin_buckets=bucket_fin,
    )

    # v5.2: aging e tops com base nos eventos por item
    if credit_events:
        # mês de corte: fim do período
        end_month = month_key(f.periodo_fim)

        credit_ledger["aging"] = aging_saldo_a_apropriar(credit_events, end_month=end_month)
        credit_ledger["top_ncm"] = top_by(credit_events, field="ncm", limit=15, metric="credito_apropriado")
        credit_ledger["top_cfop"] = top_by(credit_events, field="cfop", limit=15, metric="credito_apropriado")
        credit_ledger["top_produto"] = top_by(credit_events, field="produto", limit=15, metric="credito_apropriado")

    cash_cfg = CashLedgerConfigV2(
        prazo_medio_dias=int(c.prazo_medio_dias),
        split_percent=float(getattr(c, "split_percent", 0.0) or 0.0),
        delay_days=int(getattr(c, "delay_days", 0) or 0),
        residual_installments=int(getattr(c, "residual_installments", 1) or 1),
        residual_start_offset_months=int(getattr(c, "residual_start_offset_months", 0) or 0),
    )

    cash_ledger = build_cash_ledger_v2(
        competencia_series=series_out,
        cfg=cash_cfg,
    )


    
    return EngineResult(
        base={
            "rows": int(rows_filtradas),
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
            "credito_aproveitado": float(credito_aproveitado_total),
            "credito_apropriado_no_periodo": float(credito_apropriado_no_periodo),
        },
        caixa={
            "prazo_medio_dias": int(c.prazo_medio_dias),
            "impacto_caixa_estimado": float(impacto_caixa_estimado),
        },
        breakdown_movimento=breakdown_movimento,
        breakdown_finalidade=breakdown_finalidade,
        series=series_out,
        credit_ledger=credit_ledger,
        cash_ledger=cash_ledger,
    )
