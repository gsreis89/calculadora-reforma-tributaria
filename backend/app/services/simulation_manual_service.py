# backend/app/services/simulation_manual_service.py
from __future__ import annotations

from app.schemas.simulation_manual import SimulacaoManualPayload, SimulacaoManualResponse
from app.services.tax_params_service import get_rate


def _r2(v: float) -> float:
    return float(f"{v:.2f}")


def _get_cbs_ibs_rates(ano: int, uf_origem: str) -> tuple[float, float]:
    """
    Busca CBS/IBS no cadastro (JSON) por:
      1) (ano, tipo, uf=UF_ORIGEM)
      2) (ano, tipo, uf=None)  -> "geral"
      3) default (fallback)

    Obs: você comentou que depois podemos mudar para usar UF_DESTINO no IBS, etc.
    """
    # defaults finais (caso não exista nada no JSON)
    default_cbs = 0.0880 if ano >= 2027 else 0.0090
    default_ibs = 0.0100 if ano >= 2027 else 0.0010

    cbs = get_rate(ano=ano, tipo="CBS_PADRAO", uf=uf_origem, default=default_cbs)
    ibs = get_rate(ano=ano, tipo="IBS_PADRAO", uf=uf_origem, default=default_ibs)

    return float(cbs), float(ibs)


def simular_manual_unico(payload: SimulacaoManualPayload) -> SimulacaoManualResponse:
    ano = int(payload.ano)

    # ATUAL
    valor_icms_atual = float(payload.bc_icms) * float(payload.aliq_icms_atual)
    valor_pis_atual = float(payload.bc_pis) * float(payload.aliq_pis_atual)
    valor_cofins_atual = float(payload.bc_cofins) * float(payload.aliq_cofins_atual)

    carga_total_atual = valor_icms_atual + valor_pis_atual + valor_cofins_atual

    # REFORMA (cadastrável via JSON)
    cbs_rate, ibs_rate = _get_cbs_ibs_rates(ano, payload.uf_origem)

    # CBS/IBS calculados em cima da base do PIS (mantendo sua lógica atual)
    valor_cbs = float(payload.bc_pis) * cbs_rate
    valor_ibs = float(payload.bc_pis) * ibs_rate

    # transição (mantive seu comportamento)
    if ano >= 2027:
        valor_pis_reforma = 0.0
        valor_cofins_reforma = 0.0
    else:
        valor_pis_reforma = valor_pis_atual
        valor_cofins_reforma = valor_cofins_atual

    valor_icms_reforma = valor_icms_atual

    carga_total_reforma = (
        valor_icms_reforma
        + valor_pis_reforma
        + valor_cofins_reforma
        + valor_cbs
        + valor_ibs
    )

    diferenca_absoluta = carga_total_reforma - carga_total_atual
    diferenca_percentual = (
        (diferenca_absoluta / carga_total_atual) * 100.0 if carga_total_atual else 0.0
    )

    return SimulacaoManualResponse(
        ano=ano,
        valor_produto=_r2(float(payload.valor_produto)),
        base_icms=_r2(float(payload.bc_icms)),
        valor_icms_atual=_r2(valor_icms_atual),
        valor_icms_reforma=_r2(valor_icms_reforma),
        valor_pis_atual=_r2(valor_pis_atual),
        valor_pis_reforma=_r2(valor_pis_reforma),
        valor_cofins_atual=_r2(valor_cofins_atual),
        valor_cofins_reforma=_r2(valor_cofins_reforma),
        valor_cbs=_r2(valor_cbs),
        valor_ibs=_r2(valor_ibs),
        carga_total_atual=_r2(carga_total_atual),
        carga_total_reforma=_r2(carga_total_reforma),
        diferenca_absoluta=_r2(diferenca_absoluta),
        diferenca_percentual=_r2(diferenca_percentual),
    )
