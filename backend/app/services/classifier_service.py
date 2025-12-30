# backend/app/services/classifier_service.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


FINALIDADES = {"REVENDA", "CONSUMO", "ATIVO", "TRANSFERENCIA", "OUTRAS"}
MOVIMENTOS = {"ENTRADA", "SAIDA"}


def _s(v: Any) -> str:
    return ("" if v is None else str(v)).strip()


def _u(v: Any) -> str:
    return _s(v).upper()


def _only_digits(v: Any) -> str:
    s = _s(v)
    return "".join(ch for ch in s if ch.isdigit())


def classify_movimento(row: dict) -> str:
    """
    Prioridade:
    1) coluna 'movimento' se existir e estiver correta (ENTRADA/SAIDA)
    2) inferência por CFOP (1/2/3 -> ENTRADA, 5/6/7 -> SAIDA)
    3) fallback: SAIDA
    """
    mv = _u(row.get("movimento"))
    if mv in MOVIMENTOS:
        return mv

    cfop = _only_digits(row.get("cfop"))
    if cfop:
        if cfop[0] in {"1", "2", "3"}:
            return "ENTRADA"
        if cfop[0] in {"5", "6", "7"}:
            return "SAIDA"

    return "SAIDA"


def classify_finalidade(row: dict) -> str:
    """
    MVP de finalidade:
    - tenta identificar ATIVO/TRANSFERENCIA/REVENDA/CONSUMO por palavras-chave
    - fallback: OUTRAS

    Você pode evoluir isto para regras por CFOP/NCM/conta contábil futuramente.
    """
    produto = _u(row.get("produto") or row.get("xprod") or row.get("descricao") or row.get("desc") or "")
    cfop = _only_digits(row.get("cfop"))

    # Transferência / remessa
    if any(k in produto for k in ["TRANSFER", "REMESSA", "RETORNO", "CONSIGN", "BONIFIC", "BRINDE"]):
        return "TRANSFERENCIA"

    # Ativo/Imobilizado
    if any(k in produto for k in ["IMOB", "IMOBILIZ", "ATIVO", "MAQUIN", "EQUIP", "VEICUL", "COMPUT", "SERVIDOR"]):
        return "ATIVO"

    # Revenda
    if any(k in produto for k in ["REVENDA", "MERCADORIA", "MERCADORIAS"]):
        return "REVENDA"

    # Consumo/Insumo (MVP)
    if any(k in produto for k in ["USO", "CONSUMO", "INSUM", "MATERIAL", "EMBAL", "PECAS", "PEÇAS", "MANUT", "LUBRIF"]):
        return "CONSUMO"

    # Algumas pistas por CFOP (bem simples)
    # (não tenta ser “fiscalmente perfeito”, é só um MVP para destravar o motor)
    if cfop:
        # Entradas típicas que tendem a ser estoque/insumo (heurística)
        if cfop.startswith(("11", "21")):
            return "REVENDA"
        if cfop.startswith(("12", "22", "13", "23")):
            return "CONSUMO"

    return "OUTRAS"


def safe_finalidade(v: Any) -> Optional[str]:
    s = _u(v)
    if not s:
        return None
    # aceita variações comuns
    if s in FINALIDADES:
        return s
    if s in {"INSUMO", "CONSUMO/INSUMO", "CONSUMO_INSUMO"}:
        return "CONSUMO"
    if s in {"TRANSF", "TRANSFER"}:
        return "TRANSFERENCIA"
    return None
