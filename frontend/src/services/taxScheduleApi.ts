// frontend/src/taxScheduleApi.ts

export interface TaxSchedule {
  ano: number;
  cbs_aliquota: number;
  ibs_aliquota: number;
}

const API_BASE = "http://127.0.0.1:8000";

export async function listTaxSchedules(): Promise<TaxSchedule[]> {
  const resp = await fetch(`${API_BASE}/tax-schedule/`, {
    method: "GET",
  });

  if (!resp.ok) {
    const text = await resp.text();
    console.error("Erro ao listar tax_schedule:", resp.status, text);
    throw new Error("Erro ao listar cronograma de CBS/IBS");
  }

  const data = (await resp.json()) as TaxSchedule[];
  return data;
}

export async function saveTaxSchedule(
  payload: TaxSchedule
): Promise<TaxSchedule> {
  // vamos usar POST /tax-schedule/ que cria ou substitui o ano
  const resp = await fetch(`${API_BASE}/tax-schedule/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!resp.ok) {
    const text = await resp.text();
    console.error("Erro ao salvar tax_schedule:", resp.status, text);
    throw new Error("Erro ao salvar cronograma de CBS/IBS");
  }

  const data = (await resp.json()) as TaxSchedule;
  return data;
}
