"""
Tabela de transição de tributos da Reforma (2026–2033).

- icms_factor:
    Fator multiplicador sobre a carga atual de ICMS.
    1.00 = 100% da carga atual
    0.90 = 90% da carga atual
    0.00 = extinção do ICMS

- pis_cofins_factor:
    Fator multiplicador sobre a carga atual de PIS/COFINS.
    1.00 = 100% da carga atual
    0.00 = extinção (a partir de 2027)

- cbs / ibs:
    Alíquotas em termos decimais (9% = 0.09, 0,90% = 0.009 etc).
    Estes valores são referenciais para simulação.
"""

TAX_TRANSITION = {
    # 2026 – PIS/COFINS ainda existem, ICMS 100%.
    # CBS 0,90% e IBS 0,10% (teste paralelo).
    2026: {
        "icms_factor": 1.00,
        "pis_cofins_factor": 1.00,
        "cbs": 0.009,   # 0,90%
        "ibs": 0.001,   # 0,10% (exemplo)
    },

    # 2027 – PIS/COFINS extintos, ICMS 100%.
    # CBS assume a base PIS/COFINS, IBS sobe um pouco.
    2027: {
        "icms_factor": 1.00,
        "pis_cofins_factor": 0.00,
        "cbs": 0.088,   # 8,80% (referência)
        "ibs": 0.01,    # 1,00% (exemplo)
    },

    # 2028 – ainda sem redução de ICMS, PIS/COFINS extintos.
    2028: {
        "icms_factor": 1.00,
        "pis_cofins_factor": 0.00,
        "cbs": 0.088,
        "ibs": 0.01,
    },

    # 2029 – ICMS reduzido para 90% da carga atual.
    2029: {
        "icms_factor": 0.90,
        "pis_cofins_factor": 0.00,
        "cbs": 0.088,
        "ibs": 0.01,
    },

    # 2030 – ICMS reduzido para 80%.
    2030: {
        "icms_factor": 0.80,
        "pis_cofins_factor": 0.00,
        "cbs": 0.088,
        "ibs": 0.01,
    },

    # 2031 – ICMS reduzido para 70%.
    2031: {
        "icms_factor": 0.70,
        "pis_cofins_factor": 0.00,
        "cbs": 0.088,
        "ibs": 0.01,
    },

    # 2032 – ICMS reduzido para 60%.
    2032: {
        "icms_factor": 0.60,
        "pis_cofins_factor": 0.00,
        "cbs": 0.088,
        "ibs": 0.01,
    },

    # 2033 – ICMS e PIS/COFINS extintos.
    2033: {
        "icms_factor": 0.00,
        "pis_cofins_factor": 0.00,
        "cbs": 0.088,
        "ibs": 0.01,
    },
}

# Constantes de fallback (usadas em alguns serviços que importam DEFAULT_CBS, etc.)
# Se algum serviço não achar ano na TAX_TRANSITION, ele pode usar esses valores padrão.
DEFAULT_CBS = 0.088  # 8,8% como referência
DEFAULT_IBS = 0.01   # 1% como referência
