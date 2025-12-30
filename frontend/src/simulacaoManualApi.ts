// frontend/src/simulacaoManualApi.js

export interface SimulacaoManualPayload {
  ano: number;
  valor_produto: number;
  bc_icms: number;
  bc_pis: number;
  bc_cofins: number;
  aliq_icms_atual: number;
  aliq_pis_atual: number;
  aliq_cofins_atual: number;
  uf_origem: string;
  uf_destino: string;
  ncm?: string | null;
  produto?: string | null;
  movimento?: string | null;
  cfop?: string | null;
}

export interface SimulacaoManualResponse {
  ano: number;
  valor_produto: number;
  base_icms: number;
  valor_icms_atual: number;
  valor_icms_reforma: number;
  valor_pis_atual: number;
  valor_pis_reforma: number;
  valor_cofins_atual: number;
  valor_cofins_reforma: number;
  valor_cbs: number;
  valor_ibs: number;
  carga_total_atual: number;
  carga_total_reforma: number;
  diferenca_absoluta: number;
  diferenca_percentual: number;
}

// Função que chama a API FastAPI
export async function simularManual(
  payload: SimulacaoManualPayload
): Promise<SimulacaoManualResponse> {
  const response = await fetch("http://127.0.0.1:8000/simulacao-manual", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const text = await response.text();
    console.error("Erro na API:", response.status, text);
    throw new Error("Erro ao chamar a API de simulação manual");
  }

  const data = (await response.json()) as SimulacaoManualResponse;
  return data;
}
