from typing import Optional, List

from sqlalchemy.orm import Session

from app.db.models import NFeDocumento
from app.core.tax_table import TAX_TRANSITION, DEFAULT_CBS
from app.schemas.simulation_filter import (
    SimulationFilterRequest,
    SimulationFilterResponse,
    TributoComparado,
)


def _to_float(v) -> float:
    if not v:
        return 0.0
    s = str(v).strip().replace(" ", "")
    # trata formato 1.234,56
    if "," in s and s.count(",") == 1:
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def simular_reforma_filtrada(
    db: Session,
    filtro: SimulationFilterRequest,
) -> SimulationFilterResponse:
    """
    1) Busca as saídas no período/UF/NCM/Produto informado.
    2) Calcula ICMS / PIS / COFINS atuais.
    3) Aplica CBS + IBS do ano da reforma selecionado.
    """

    # 1. Alíquotas da reforma para o ano selecionado
    config = TAX_TRANSITION.get(filtro.ano_reforma)
    if not config:
        raise ValueError(f"Ano {filtro.ano_reforma} não está na faixa da reforma (2026–2033).")

    aliquota_cbs = config.get("cbs") or DEFAULT_CBS
    aliquota_ibs = config.get("ibs") or 0.0

    # 2. Monta filtros da query
    inicio_str = filtro.periodo_inicio.strftime("%Y-%m-%d")
    fim_str = filtro.periodo_fim.strftime("%Y-%m-%d")

    query = db.query(NFeDocumento).filter(
        NFeDocumento.dhemi >= inicio_str,
        NFeDocumento.dhemi <= fim_str,
    )

    if filtro.uf_origem:
        query = query.filter(NFeDocumento.uf == filtro.uf_origem)

    if filtro.uf_destino:
        query = query.filter(NFeDocumento.uf_dest == filtro.uf_destino)

    if filtro.ncm:
        query = query.filter(NFeDocumento.ncm == filtro.ncm)

    if filtro.produto:
        # xprod é o nome/descrição do produto, ajuste se o campo no modelo tiver outro nome
        query = query.filter(NFeDocumento.xprod.ilike(f"%{filtro.produto}%"))

    # Se quiser, aqui podemos colocar um LIMIT de segurança, mas como já há filtros,
    # vamos sem limit inicialmente. Se ficar pesado, colocamos um param opcional depois.
    docs: List[NFeDocumento] = query.all()

    if not docs:
        # Nenhuma nota encontrada: devolve tudo zerado, mas com filtros ecoados
        return SimulationFilterResponse(
            periodo_inicio=filtro.periodo_inicio,
            periodo_fim=filtro.periodo_fim,
            ano_reforma=filtro.ano_reforma,
            uf_origem=filtro.uf_origem,
            uf_destino=filtro.uf_destino,
            ncm=filtro.ncm,
            produto=filtro.produto,
            receita_total=0.0,
            carga_atual_total=0.0,
            carga_reforma_total=0.0,
            diferenca_absoluta=0.0,
            diferenca_percentual=0.0,
            detalhes=[
                TributoComparado(tributo="ICMS", valor_atual=0.0, valor_reforma=0.0),
                TributoComparado(tributo="PIS", valor_atual=0.0, valor_reforma=0.0),
                TributoComparado(tributo="COFINS", valor_atual=0.0, valor_reforma=0.0),
                TributoComparado(tributo="CBS", valor_atual=0.0, valor_reforma=0.0),
                TributoComparado(tributo="IBS", valor_atual=0.0, valor_reforma=0.0),
            ],
        )

    # 3. Soma valores atuais
    receita_total = sum(_to_float(d.vprod) for d in docs)
    total_icms = sum(_to_float(d.vicms_icms) for d in docs)
    total_pis = sum(_to_float(d.vpis) for d in docs)
    total_cofins = sum(_to_float(d.vcofins) for d in docs)

    carga_atual_total = total_icms + total_pis + total_cofins

    # 4. Carga no cenário da reforma (CBS + IBS sobre a receita)
    carga_cbs = receita_total * aliquota_cbs
    carga_ibs = receita_total * aliquota_ibs
    carga_reforma_total = carga_cbs + carga_ibs

    diferenca_absoluta = carga_reforma_total - carga_atual_total
    diferenca_percentual = (
        (diferenca_absoluta / carga_atual_total * 100) if carga_atual_total > 0 else 0.0
    )

    detalhes = [
        TributoComparado(
            tributo="ICMS",
            valor_atual=total_icms,
            valor_reforma=0.0,  # assumindo substituição por IBS/CBS
        ),
        TributoComparado(
            tributo="PIS",
            valor_atual=total_pis,
            valor_reforma=0.0,
        ),
        TributoComparado(
            tributo="COFINS",
            valor_atual=total_cofins,
            valor_reforma=0.0,
        ),
        TributoComparado(
            tributo="CBS",
            valor_atual=0.0,
            valor_reforma=carga_cbs,
        ),
        TributoComparado(
            tributo="IBS",
            valor_atual=0.0,
            valor_reforma=carga_ibs,
        ),
    ]

    return SimulationFilterResponse(
        periodo_inicio=filtro.periodo_inicio,
        periodo_fim=filtro.periodo_fim,
        ano_reforma=filtro.ano_reforma,
        uf_origem=filtro.uf_origem,
        uf_destino=filtro.uf_destino,
        ncm=filtro.ncm,
        produto=filtro.produto,
        receita_total=receita_total,
        carga_atual_total=carga_atual_total,
        carga_reforma_total=carga_reforma_total,
        diferenca_absoluta=diferenca_absoluta,
        diferenca_percentual=diferenca_percentual,
        detalhes=detalhes,
    )
