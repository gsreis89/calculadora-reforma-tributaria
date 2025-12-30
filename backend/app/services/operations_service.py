from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.models import NFeDocumento
from app.schemas.operations import OperacaoResumo


def _to_float(value) -> Optional[float]:
    """Converte texto/decimal para float, tratando vírgula e valores inválidos."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    s = s.replace(".", "").replace(",", ".") if "," in s and s.count(",") == 1 else s
    try:
        return float(s)
    except ValueError:
        return None


def listar_operacoes_resumo(
    db: Session,
    data_inicio: Optional[datetime] = None,
    data_fim: Optional[datetime] = None,
    movimento: Optional[str] = None,
    limite: int = 200,
) -> List[OperacaoResumo]:
    """
    Busca operações na tabela de NFe e retorna um resumo enxuto.

    Otimizações:
    - Se NÃO tiver filtro de data, ordena por ID (PK) em vez de por data,
      pra usar índice e não precisar varrer a tabela inteira.
    """
    query = db.query(NFeDocumento)

    # Filtros opcionais
    if data_inicio:
        query = query.filter(NFeDocumento.dhemi >= data_inicio)
    if data_fim:
        query = query.filter(NFeDocumento.dhemi <= data_fim)
    if movimento:
        query = query.filter(NFeDocumento.movimento == movimento)

    # Ordenação otimizada
    if data_inicio or data_fim:
        query = query.order_by(NFeDocumento.dhemi.desc())
    else:
        query = query.order_by(NFeDocumento.id.desc())

    query = query.limit(limite)

    resultados = query.all()

    return [
        OperacaoResumo(
            id=op.id,
            empresa=op.empresa,
            movimento=op.movimento,
            data_emissao=op.dhemi,
            uf_origem=op.uf,
            uf_destino=op.uf_dest,
            cfop=op.cfop,
            valor_produtos=_to_float(op.vprod),
            valor_icms=_to_float(op.vicms_icms),
            valor_pis=_to_float(op.vpis),
            valor_cofins=_to_float(op.vcofins),
        )
        for op in resultados
    ]
