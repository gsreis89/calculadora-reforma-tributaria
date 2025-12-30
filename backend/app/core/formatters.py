# app/core/formatters.py

from typing import Any


def format_two_decimals(data: Any) -> Any:
    """
    Varre recursivamente o objeto (dict/list) e
    arredonda todos os floats para duas casas decimais.
    """

    # Float isolado
    if isinstance(data, float):
        # round() evita caudas longas e trata -0.0
        value = round(data, 2)
        # Se der -0.0, normaliza para 0.0
        if value == -0.0:
            value = 0.0
        return float(f"{value:.2f}")

    # Dicionário
    if isinstance(data, dict):
        return {k: format_two_decimals(v) for k, v in data.items()}

    # Lista/tupla
    if isinstance(data, (list, tuple)):
        return [format_two_decimals(v) for v in data]

    # Outros tipos: retorna como está
    return data
