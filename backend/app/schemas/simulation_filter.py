from datetime import date
from typing import Optional, List

from pydantic import BaseModel


class SimulationFilterRequest(BaseModel):
    """
    Filtros para buscar a base histórica que será usada na simulação.
    - periodo_inicio / periodo_fim: período dos dados reais (saídas).
    - ano_reforma: ano do cronograma da reforma (2026–2033) que queremos simular.
    - uf_origem / uf_destino: filtros opcionais de origem/destino.
    - ncm / produto: opcional, para simular um item ou grupo específico.
    """

    periodo_inicio: date
    periodo_fim: date
    ano_reforma: int

    uf_origem: Optional[str] = None
    uf_destino: Optional[str] = None
    ncm: Optional[str] = None
    produto: Optional[str] = None


class TributoComparado(BaseModel):
    tributo: str          # "ICMS", "PIS", "COFINS", "CBS", "IBS"
    valor_atual: float    # quanto sai hoje (para CBS/IBS será 0)
    valor_reforma: float  # quanto sairia no cenário da reforma


class SimulationFilterResponse(BaseModel):
    # eco dos filtros (pra mostrar na tela / auditoria)
    periodo_inicio: date
    periodo_fim: date
    ano_reforma: int
    uf_origem: Optional[str]
    uf_destino: Optional[str]
    ncm: Optional[str]
    produto: Optional[str]

    # base econômica
    receita_total: float

    # carga hoje
    carga_atual_total: float

    # carga no cenário da reforma
    carga_reforma_total: float

    # comparativo
    diferenca_absoluta: float
    diferenca_percentual: float

    # detalhamento por tributo
    detalhes: List[TributoComparado]
