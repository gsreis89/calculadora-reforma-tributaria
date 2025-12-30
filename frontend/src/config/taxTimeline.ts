// src/config/taxTimeline.ts

export type TaxKey =
  | "PIS"
  | "COFINS"
  | "CBS"
  | "ICMS"
  | "ISS"
  | "IBS"
  | "IPI"
  | "IS";

export type TaxStatus =
  | "sem_alteracao"
  | "ativo"
  | "extinto"
  | "reduzido"
  | "novo"
  | "definido_posteriormente";

export interface TaxConfig {
  status: TaxStatus;
  /**
   * Alíquota em percentual (ex: 0.9 => 0,9%)
   * Quando for uma alíquota "proporcional" (90% de redução, etc.),
   * usamos o campo `observacao` para explicar melhor.
   */
  aliquota?: number;
  observacao?: string;
}

export type TaxYearConfig = Record<TaxKey, TaxConfig>;

export const TAX_YEARS = [2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033] as const;

export const TAX_TIMELINE: Record<number, TaxYearConfig> = {
  2026: {
    PIS: { status: "sem_alteracao", observacao: "sem alteração" },
    COFINS: { status: "sem_alteracao", observacao: "sem alteração" },
    CBS: {
      status: "novo",
      aliquota: 0.9,
      observacao: "início da CBS em 0,90%",
    },
    ICMS: { status: "sem_alteracao", observacao: "sem alteração" },
    ISS: { status: "sem_alteracao", observacao: "sem alteração" },
    IBS: {
      status: "novo",
      aliquota: 0.1,
      observacao: "0,05% estadual + 0,05% municipal",
    },
    IPI: { status: "sem_alteracao", observacao: "sem alteração" },
    IS: {
      status: "definido_posteriormente",
      observacao: "ainda não implementado",
    },
  },
  2027: {
    PIS: { status: "extinto", observacao: "extinção do PIS" },
    COFINS: { status: "extinto", observacao: "extinção da COFINS" },
    CBS: {
      status: "ativo",
      aliquota: 8.8,
      observacao: "CBS em 8,80%",
    },
    ICMS: { status: "sem_alteracao", observacao: "sem alteração" },
    ISS: { status: "sem_alteracao", observacao: "sem alteração" },
    IBS: {
      status: "novo",
      aliquota: 0.1,
      observacao: "0,05% estadual + 0,05% municipal",
    },
    IPI: { status: "sem_alteracao", observacao: "sem alteração" },
    IS: {
      status: "definido_posteriormente",
      observacao: "ainda não implementado",
    },
  },
  2028: {
    PIS: { status: "extinto", observacao: "extinção do PIS" },
    COFINS: { status: "extinto", observacao: "extinção da COFINS" },
    CBS: {
      status: "ativo",
      aliquota: 8.8,
      observacao: "CBS em 8,80%",
    },
    ICMS: { status: "sem_alteracao", observacao: "sem alteração" },
    ISS: { status: "sem_alteracao", observacao: "sem alteração" },
    IBS: {
      status: "novo",
      aliquota: 0.1,
      observacao: "0,05% estadual + 0,05% municipal",
    },
    IPI: {
      status: "reduzido",
      observacao:
        "alíquota reduzida a 0%, mantida apenas para produtos com incentivos na Zona Franca",
    },
    IS: {
      status: "definido_posteriormente",
      observacao:
        "alíquota e base de cálculo serão definidas por Lei Ordinária",
    },
  },
  2029: {
    PIS: { status: "extinto", observacao: "extinto" },
    COFINS: { status: "extinto", observacao: "extinto" },
    CBS: {
      status: "definido_posteriormente",
      observacao:
        "alíquotas serão definidas por resolução do Senado, seguindo limites da Lei Complementar",
    },
    ICMS: {
      status: "reduzido",
      aliquota: 90,
      observacao: "90% da carga original",
    },
    ISS: {
      status: "reduzido",
      aliquota: 90,
      observacao: "90% da carga original",
    },
    IBS: {
      status: "ativo",
      aliquota: 10,
      observacao: "10% da carga cheia prevista",
    },
    IPI: {
      status: "reduzido",
      observacao:
        "alíquota mantida a 0% para produtos exceto os com incentivos na Zona Franca",
    },
    IS: {
      status: "ativo",
      observacao:
        "alíquota e bases de cálculo definidas por Lei Ordinária (produtos seletivos)",
    },
  },
  2030: {
    PIS: { status: "extinto", observacao: "extinto" },
    COFINS: { status: "extinto", observacao: "extinto" },
    CBS: {
      status: "definido_posteriormente",
      observacao:
        "alíquotas definidas por resolução do Senado, conforme Lei Complementar",
    },
    ICMS: {
      status: "reduzido",
      aliquota: 80,
      observacao: "80% da carga original",
    },
    ISS: {
      status: "reduzido",
      aliquota: 80,
      observacao: "80% da carga original",
    },
    IBS: {
      status: "ativo",
      aliquota: 20,
      observacao: "20% da carga cheia prevista",
    },
    IPI: {
      status: "reduzido",
      observacao:
        "mantido apenas para produtos com incentivos na Zona Franca",
    },
    IS: {
      status: "ativo",
      observacao: "imposto seletivo em vigor",
    },
  },
  2031: {
    PIS: { status: "extinto", observacao: "extinto" },
    COFINS: { status: "extinto", observacao: "extinto" },
    CBS: {
      status: "definido_posteriormente",
      observacao: "regida por resolução do Senado",
    },
    ICMS: {
      status: "reduzido",
      aliquota: 70,
      observacao: "70% da carga original",
    },
    ISS: {
      status: "reduzido",
      aliquota: 70,
      observacao: "70% da carga original",
    },
    IBS: {
      status: "ativo",
      aliquota: 30,
      observacao: "30% da carga cheia prevista",
    },
    IPI: {
      status: "reduzido",
      observacao: "mantido apenas em situações específicas",
    },
    IS: { status: "ativo" },
  },
  2032: {
    PIS: { status: "extinto" },
    COFINS: { status: "extinto" },
    CBS: {
      status: "definido_posteriormente",
      observacao: "regida por resolução do Senado",
    },
    ICMS: {
      status: "reduzido",
      aliquota: 60,
      observacao: "60% da carga original",
    },
    ISS: {
      status: "reduzido",
      aliquota: 60,
      observacao: "60% da carga original",
    },
    IBS: {
      status: "ativo",
      aliquota: 40,
      observacao: "40% da carga cheia prevista",
    },
    IPI: {
      status: "reduzido",
      observacao: "mantido apenas em situações específicas",
    },
    IS: { status: "ativo" },
  },
  2033: {
    PIS: { status: "extinto" },
    COFINS: { status: "extinto" },
    CBS: {
      status: "definido_posteriormente",
      observacao: "regida por resolução do Senado",
    },
    ICMS: { status: "extinto", observacao: "extinção do ICMS" },
    ISS: { status: "extinto", observacao: "extinção do ISS" },
    IBS: {
      status: "ativo",
      aliquota: 100,
      observacao: "IBS em sua carga integral (100%)",
    },
    IPI: {
      status: "reduzido",
      observacao: "mantido apenas em situações específicas",
    },
    IS: { status: "ativo" },
  },
};
