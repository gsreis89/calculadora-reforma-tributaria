# backend/app/services/simulator_engine/credit_events.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional

from app.services.simulator_engine.dates_v4 import add_months_first_day, month_key


@dataclass
class CreditEventV2:
    """Evento de crédito com rastreabilidade (nível 2).

    Grão:
      - 1 evento por item por mês de apropriação.

    Observação:
      - Para NÃO-ATIVO: 1 evento no mesmo mês de emissão.
      - Para ATIVO: N eventos (1/N por mês) a partir do mês de emissão.

    Campos de rastreabilidade são strings (como vêm do CSV) para evitar custo de casting.
    """

    emit_month: str
    appropriation_month: str
    finalidade: str

    uf_origem: str
    uf_destino: str
    cfop: str
    ncm: str
    produto: str

    credito_gerado: float        # antes da glosa
    glosa: float                 # valor glosado
    credito_apos_glosa: float    # líquido

    credito_apropriado: float    # apropriado nesta competência


def _s(v: Any) -> str:
    return "" if v is None else str(v).strip()


def _upper(v: Any) -> str:
    return _s(v).upper()


def _row_dims(row: Dict[str, Any]) -> Dict[str, str]:
    return {
        "uf_origem": _upper(row.get("uf")),
        "uf_destino": _upper(row.get("uf_dest")),
        "cfop": _s(row.get("cfop")),
        "ncm": _s(row.get("ncm")),
        "produto": _s(row.get("produto")),
    }


def add_credit_events_for_item(
    *,
    out: List[CreditEventV2],
    row: Dict[str, Any],
    fin_eff: str,
    dr: Optional[date],
    cred_pot: float,
    gl: float,
    cred_ap: float,
    ativo_meses: int,
) -> None:
    """Cria e adiciona eventos de crédito para 1 item.

    Regras:
      - Se não houver data (dr is None), não gera eventos (mantém semântica de série mensal).
      - ATIVO: distribui cred_ap em N meses (portion), a partir do mês de emissão.
      - Não-ATIVO: apropria integralmente no mês de emissão.

    Observação importante:
      - Para ATIVO, por simplicidade (e coerência com v4), a glosa é rateada proporcionalmente
        junto com o crédito (glosa_portion = gl/N, gerado_portion = cred_pot/N).
    """

    if dr is None:
        return

    dims = _row_dims(row)
    emit_month = month_key(dr)

    fin = (fin_eff or "").upper()
    if fin == "ATIVO":
        n = int(max(1, ativo_meses))
        base_month = date(dr.year, dr.month, 1)

        ger_portion = float(cred_pot) / float(n)
        gl_portion = float(gl) / float(n)
        ap_portion = float(cred_ap) / float(n)

        for i in range(n):
            dd = add_months_first_day(base_month, i)
            mm = month_key(dd)
            out.append(
                CreditEventV2(
                    emit_month=emit_month,
                    appropriation_month=mm,
                    finalidade=fin,
                    uf_origem=dims["uf_origem"],
                    uf_destino=dims["uf_destino"],
                    cfop=dims["cfop"],
                    ncm=dims["ncm"],
                    produto=dims["produto"],
                    credito_gerado=float(ger_portion),
                    glosa=float(gl_portion),
                    credito_apos_glosa=float(max(0.0, ger_portion - gl_portion)),
                    credito_apropriado=float(ap_portion),
                )
            )
        return

    # Não-ATIVO: apropria no mesmo mês
    out.append(
        CreditEventV2(
            emit_month=emit_month,
            appropriation_month=emit_month,
            finalidade=fin or "OUTRAS",
            uf_origem=dims["uf_origem"],
            uf_destino=dims["uf_destino"],
            cfop=dims["cfop"],
            ncm=dims["ncm"],
            produto=dims["produto"],
            credito_gerado=float(cred_pot),
            glosa=float(gl),
            credito_apos_glosa=float(max(0.0, float(cred_pot) - float(gl))),
            credito_apropriado=float(cred_ap),
        )
    )
