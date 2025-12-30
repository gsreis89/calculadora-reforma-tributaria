from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import NFeDocumento
from app.core.tax_table import TAX_TRANSITION, DEFAULT_CBS
from app.schemas.simulation_db import SimulationDBResult


def _to_float(v) -> float:
    if not v:
        return 0.0
    s = str(v).strip().replace(" ", "")
    if "," in s and s.count(",") == 1:
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def simular_reforma_db(
    db: Session,
    ano: int,
    empresa: Optional[str] = None,
    movimento: Optional[str] = None,
) -> SimulationDBResult:
    # 1) Alíquotas do ano
    config = TAX_TRANSITION.get(ano)
    if not config:
        raise ValueError(f"Ano {ano} não está na faixa da reforma (2026–2033).")

    aliquota_cbs = config["cbs"] if config["cbs"] is not None else DEFAULT_CBS
    aliquota_ibs = config["ibs"]

    # 2) Intervalo de datas como STRING, porque dhemi é TEXT no banco
    inicio_ano_str = f"{ano}-01-01"
    inicio_prox_ano_str = f"{ano + 1}-01-01"

    query = db.query(NFeDocumento).filter(
        NFeDocumento.dhemi >= inicio_ano_str,
        NFeDocumento.dhemi < inicio_prox_ano_str,
    )

    if empresa:
        query = query.filter(NFeDocumento.empresa == empresa)

    if movimento:
        query = query.filter(NFeDocumento.movimento == movimento)

        # ⚠️ LIMIT TEMPORÁRIO PARA TESTE
    docs = query.limit(1000).all()


    # Se não tiver notas nesse ano, devolve tudo zerado
    if not docs:
        return SimulationDBResult(
            ano=ano,
            total_valor_operacoes=0.0,
            carga_atual_icms=0.0,
            carga_atual_pis=0.0,
            carga_atual_cofins=0.0,
            carga_atual_total=0.0,
            aliquota_cbs=aliquota_cbs,
            aliquota_ibs=aliquota_ibs,
            carga_reforma_total=0.0,
            diferenca_absoluta=0.0,
            diferenca_percentual=0.0,
        )

    # 3) Soma valores
    total_operacoes = sum(_to_float(d.vprod) for d in docs)
    total_icms = sum(_to_float(d.vicms_icms) for d in docs)
    total_pis = sum(_to_float(d.vpis) for d in docs)
    total_cofins = sum(_to_float(d.vcofins) for d in docs)

    carga_atual_total = total_icms + total_pis + total_cofins
    carga_reforma_total = total_operacoes * (aliquota_cbs + aliquota_ibs)

    diferenca_absoluta = carga_reforma_total - carga_atual_total
    diferenca_percentual = (
        (diferenca_absoluta / carga_atual_total * 100) if carga_atual_total > 0 else 0.0
    )

    return SimulationDBResult(
        ano=ano,
        total_valor_operacoes=total_operacoes,
        carga_atual_icms=total_icms,
        carga_atual_pis=total_pis,
        carga_atual_cofins=total_cofins,
        carga_atual_total=carga_atual_total,
        aliquota_cbs=aliquota_cbs,
        aliquota_ibs=aliquota_ibs,
        carga_reforma_total=carga_reforma_total,
        diferenca_absoluta=diferenca_absoluta,
        diferenca_percentual=diferenca_percentual,
    )
