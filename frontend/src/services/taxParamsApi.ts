export type TaxParamTipo = "CBS_PADRAO" | "IBS_PADRAO";

export interface TaxParamItem {
  ano: number;
  uf?: string | null;
  tipo: TaxParamTipo;
  aliquota: number;
  descricao?: string | null;
}

const BASE_URL = "http://127.0.0.1:8000";

export async function listTaxParams(ano?: number) {
  const url = ano ? `${BASE_URL}/tax-params/?ano=${ano}` : `${BASE_URL}/tax-params/`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(await res.text());
  return (await res.json()) as TaxParamItem[];
}

export async function createTaxParam(payload: TaxParamItem) {
  const res = await fetch(`${BASE_URL}/tax-params/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return (await res.json()) as TaxParamItem;
}

export async function deleteTaxParam(ano: number, tipo: TaxParamTipo, uf?: string | null) {
  const params = new URLSearchParams();
  params.set("ano", String(ano));
  params.set("tipo", tipo);
  if (uf) params.set("uf", uf);

  const res = await fetch(`${BASE_URL}/tax-params/?${params.toString()}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(await res.text());
  return true;
}
