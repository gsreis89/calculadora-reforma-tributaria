def classificar_finalidade(cfop: str | None) -> str:
    if not cfop:
        return "OUTRAS"

    if cfop.startswith(("11", "21")):
        return "INSUMO"

    if cfop.startswith(("15", "25")):
        return "ATIVO"

    if cfop.startswith(("51", "61")):
        return "REVENDA"

    return "OUTRAS"
