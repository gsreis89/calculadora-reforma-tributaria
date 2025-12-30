# backend/app/services/simulator_engine/rules_v4.py
from __future__ import annotations
from typing import Any, List, Optional, Tuple
from .dto_v4 import Rule, Scenario

def digits(v: Any) -> str:
    s = "" if v is None else str(v)
    return "".join(ch for ch in s if ch.isdigit())

def credit_percent_for(finalidade: str, c: Scenario) -> float:
    f = (finalidade or "").upper()
    if f == "REVENDA":
        return float(c.perc_credit_revenda)
    if f == "CONSUMO":
        return float(c.perc_credit_consumo)
    if f == "ATIVO":
        return float(c.perc_credit_ativo)
    if f == "TRANSFERENCIA":
        return float(c.perc_credit_transfer)
    return float(c.perc_credit_outras)

def match_rule(rule: Rule, cfop_digits: str, ncm_digits: str) -> bool:
    m = (rule.match or "").strip().lower()
    v = (rule.value or "").strip()
    if not v:
        return False

    dv = digits(v)
    if m == "cfop":
        return cfop_digits == dv
    if m == "cfop_prefix":
        return cfop_digits.startswith(dv)
    if m == "ncm":
        return ncm_digits == dv
    if m == "ncm_prefix":
        return ncm_digits.startswith(dv)

    return False

def apply_rules(
    row: dict,
    base_finalidade: str,
    cenario: Scenario,
    rules: List[Rule],
    safe_finalidade_fn,  # injeta safe_finalidade do seu classifier_service
) -> Tuple[str, float, float]:
    cfop_d = digits(row.get("cfop"))
    ncm_d = digits(row.get("ncm"))

    fin = base_finalidade
    perc_credit = credit_percent_for(fin, cenario)
    perc_glosa = float(cenario.perc_glosa)

    for rule in rules:
        if not match_rule(rule, cfop_d, ncm_d):
            continue

        if rule.finalidade:
            fin2 = safe_finalidade_fn(rule.finalidade) or fin
            fin = fin2

        if rule.perc_credit is not None:
            perc_credit = float(rule.perc_credit)
        else:
            perc_credit = credit_percent_for(fin, cenario)

        if rule.perc_glosa is not None:
            perc_glosa = float(rule.perc_glosa)

        break

    return fin, float(perc_credit), float(perc_glosa)
