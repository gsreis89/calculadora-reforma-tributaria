# backend/app/services/simulator_engine/credit_ledger.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class CreditEvent:
    """Evento de crédito (ledger).

    Grão:
      - 1 evento por competência de apropriação.

    Observação:
      - Para finalidades não-ATIVO, geração e apropriação ocorrem no mesmo mês.
      - Para ATIVO, a geração ocorre no mês de emissão e a apropriação é distribuída por N meses.
    """

    emit_month: str              # YYYY-MM (mês do documento)
    appropriation_month: str     # YYYY-MM (mês em que apropria)
    finalidade: str

    credito_gerado: float        # crédito gerado (já após % crédito, antes da glosa)
    glosa: float                 # valor glosado
    credito_apos_glosa: float    # crédito líquido (gerado - glosa)

    credito_apropriado: float    # quanto apropria neste mês (<= credito_apos_glosa)


def build_credit_ledger(*, alloc_by_month: Dict[str, float], fin_buckets: Dict[str, Dict[str, float]]) -> Dict:
    """Constrói um resumo do ledger baseado no que o v4 já calcula.

    Entradas:
      - alloc_by_month: crédito apropriado por mês (já inclui ATIVO 1/N e não-ATIVO integral no mês)
      - fin_buckets: estrutura usada no v4 com:
          entrada_base, credito_potencial, glosa, credito_aproveitado, credito_apropriado_no_periodo

    Saída:
      - credit_ledger: bloco novo (v5) para anexar ao response, sem quebrar o frontend.

    Nota:
      O v4 não preserva rastreabilidade por item/regra. Então este ledger é "nível 1":
      entrega séries e saldos por finalidade/mês. Depois evoluímos para eventos por item.
    """

    # Totais de crédito líquido (após glosa) por finalidade
    # No v4: credito_aproveitado = cred_ap (pós glosa)
    total_liquido = 0.0
    total_glosa = 0.0
    total_gerado = 0.0

    by_finalidade: Dict[str, Dict[str, float]] = {}
    for fin, it in fin_buckets.items():
        gerado = float(it.get("credito_potencial", 0.0))
        glosa = float(it.get("glosa", 0.0))
        liquido = float(it.get("credito_aproveitado", 0.0))

        total_gerado += gerado
        total_glosa += glosa
        total_liquido += liquido

        by_finalidade[fin] = {
            "credito_gerado": gerado,
            "glosa": glosa,
            "credito_apos_glosa": liquido,
            "credito_apropriado_no_periodo": float(it.get("credito_apropriado_no_periodo", 0.0)),
        }

    # Série mensal do apropriado (competência de apropriação)
    series = []
    for month in sorted(alloc_by_month.keys()):
        series.append({"period": month, "credito_apropriado": float(alloc_by_month[month])})

    apropriado_total = sum(float(v) for v in alloc_by_month.values()) if alloc_by_month else 0.0

    # Aging simplificado (saldo a apropriar) — no nível 1, consideramos:
    # saldo = credito_liquido_total - apropriado_total
    # Isso é coerente quando você retorna meses suficientes para capturar toda a apropriação do ativo.
    # Para recortes curtos, o saldo indica "restante futuro" (útil para análise).
    saldo_a_apropriar = max(0.0, float(total_liquido) - float(apropriado_total))

    return {
        "summary": {
            "credito_gerado": float(total_gerado),
            "glosa": float(total_glosa),
            "credito_apos_glosa": float(total_liquido),
            "credito_apropriado": float(apropriado_total),
            "saldo_a_apropriar": float(saldo_a_apropriar),
        },
        "by_finalidade": by_finalidade,
        "series": series,
    }


# backend/app/services/simulator_engine/engine_v4.py
# PATCH v5: anexar credit_ledger ao resultado
#
# 1) Adicione este import no topo do engine_v4.py:
#    from app.services.simulator_engine.credit_ledger import build_credit_ledger
#
# 2) Antes do return EngineResult(...), construa o bloco:
#
#    credit_ledger = build_credit_ledger(
#        alloc_by_month=credit_alloc_month,
#        fin_buckets=bucket_fin,
#    )
#
# 3) Então inclua o campo no EngineResult (e no response do route, se desejar):
#
#    return EngineResult(
#        ...,
#        credit_ledger=credit_ledger,
#    )
#
# OBS: Para não quebrar o v4, você pode adicionar o campo como opcional no EngineResult/dto_v4
# e simplesmente ignorar no response do route até o frontend passar a consumir.
