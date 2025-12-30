def calcular_reforma(
    item,
    ano: int,
    aliquota_cbs: float,
    aliquota_ibs: float,
    aliquota_is: float = 0.0,
):
    """
    Retorna (cbs, ibs, is)
    """

    # regra MVP: base = valor bruto
    base = item.valor_bruto

    cbs = base * aliquota_cbs
    ibs = base * aliquota_ibs
    is_ = base * aliquota_is

    # crédito (simplificado)
    credito = 0.0
    if item.finalidade in ("REVENDA", "INSUMO"):
        credito = cbs + ibs

    return {
        "cbs": cbs,
        "ibs": ibs,
        "is": is_,
        "credito": credito,
    }
