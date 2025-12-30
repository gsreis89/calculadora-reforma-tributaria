// frontend/src/pages/SimulacaoManual.tsx
import React, { useMemo, useState } from "react";
import {
  simularManual,
  SimulacaoManualPayload,
  SimulacaoManualResponse,
} from "../simulacaoManualApi";

const initialForm: SimulacaoManualPayload = {
  ano: 2026,
  valor_produto: 0,
  bc_icms: 0,
  bc_pis: 0,
  bc_cofins: 0,
  aliq_icms_atual: 0.04,
  aliq_pis_atual: 0.0165,
  aliq_cofins_atual: 0.076,
  uf_origem: "AM",
  uf_destino: "SP",
  ncm: null,
  produto: null,
  movimento: null,
  cfop: null,
};

function money(v: number) {
  return `R$ ${Number(v || 0).toFixed(2).replace(".", ",")}`;
}
function percent(v: number) {
  return `${Number(v || 0).toFixed(2).replace(".", ",")}%`;
}

export const SimulacaoManual: React.FC = () => {
  const [form, setForm] = useState<SimulacaoManualPayload>(initialForm);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SimulacaoManualResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const { name, value } = e.target;

    const numberFields: (keyof SimulacaoManualPayload)[] = [
      "ano",
      "valor_produto",
      "bc_icms",
      "bc_pis",
      "bc_cofins",
      "aliq_icms_atual",
      "aliq_pis_atual",
      "aliq_cofins_atual",
    ];

    if (numberFields.includes(name as any)) {
      const num = value === "" ? 0 : Number(value);
      setForm((prev) => ({ ...prev, [name]: Number.isFinite(num) ? num : 0 } as any));
      return;
    }

    const nullableFields: (keyof SimulacaoManualPayload)[] = [
      "ncm",
      "produto",
      "movimento",
      "cfop",
    ];

    if (nullableFields.includes(name as any)) {
      setForm((prev) => ({ ...prev, [name]: value.trim() === "" ? null : value } as any));
      return;
    }

    setForm((prev) => ({ ...prev, [name]: value } as any));
  }

  async function handleSimular() {
    try {
      setLoading(true);
      setError(null);
      const data = await simularManual(form);
      setResult(data);
    } catch (err: any) {
      console.error(err);
      setResult(null);
      setError(err?.message ?? "Erro ao executar simulação manual.");
    } finally {
      setLoading(false);
    }
  }

  const detalhes = useMemo(() => {
    if (!result) return [];
    return [
      { tributo: "ICMS", atual: result.valor_icms_atual, reforma: result.valor_icms_reforma },
      { tributo: "PIS", atual: result.valor_pis_atual, reforma: result.valor_pis_reforma },
      { tributo: "COFINS", atual: result.valor_cofins_atual, reforma: result.valor_cofins_reforma },
      { tributo: "CBS", atual: 0, reforma: result.valor_cbs },
      { tributo: "IBS", atual: 0, reforma: result.valor_ibs },
    ];
  }, [result]);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-slate-800">
          Simulador — Simulação Manual
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Sem banco. Você informa bases e alíquotas atuais; CBS/IBS vêm da tabela (JSON) com fallback.
        </p>
      </header>

      <div className="bg-white rounded-xl shadow-sm p-6 space-y-4">
        <h2 className="font-semibold text-slate-700">Parâmetros</h2>

        <div className="grid gap-4 md:grid-cols-3">
          <div>
            <label className="block text-sm text-slate-600 mb-1">Ano</label>
            <input
              type="number"
              name="ano"
              min={2026}
              max={2033}
              value={form.ano}
              onChange={handleChange}
              className="w-full border rounded-md px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label className="block text-sm text-slate-600 mb-1">Valor do produto (R$)</label>
            <input
              type="number"
              name="valor_produto"
              value={form.valor_produto}
              onChange={handleChange}
              className="w-full border rounded-md px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label className="block text-sm text-slate-600 mb-1">BC ICMS (R$)</label>
            <input
              type="number"
              name="bc_icms"
              value={form.bc_icms}
              onChange={handleChange}
              className="w-full border rounded-md px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label className="block text-sm text-slate-600 mb-1">BC PIS (R$)</label>
            <input
              type="number"
              name="bc_pis"
              value={form.bc_pis}
              onChange={handleChange}
              className="w-full border rounded-md px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label className="block text-sm text-slate-600 mb-1">BC COFINS (R$)</label>
            <input
              type="number"
              name="bc_cofins"
              value={form.bc_cofins}
              onChange={handleChange}
              className="w-full border rounded-md px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label className="block text-sm text-slate-600 mb-1">Alíquota ICMS (decimal)</label>
            <input
              type="number"
              step="0.0001"
              name="aliq_icms_atual"
              value={form.aliq_icms_atual}
              onChange={handleChange}
              className="w-full border rounded-md px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label className="block text-sm text-slate-600 mb-1">Alíquota PIS (decimal)</label>
            <input
              type="number"
              step="0.0001"
              name="aliq_pis_atual"
              value={form.aliq_pis_atual}
              onChange={handleChange}
              className="w-full border rounded-md px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label className="block text-sm text-slate-600 mb-1">Alíquota COFINS (decimal)</label>
            <input
              type="number"
              step="0.0001"
              name="aliq_cofins_atual"
              value={form.aliq_cofins_atual}
              onChange={handleChange}
              className="w-full border rounded-md px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label className="block text-sm text-slate-600 mb-1">UF Origem</label>
            <input
              name="uf_origem"
              value={form.uf_origem}
              onChange={handleChange}
              className="w-full border rounded-md px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label className="block text-sm text-slate-600 mb-1">UF Destino</label>
            <input
              name="uf_destino"
              value={form.uf_destino}
              onChange={handleChange}
              className="w-full border rounded-md px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label className="block text-sm text-slate-600 mb-1">NCM (opcional)</label>
            <input
              name="ncm"
              value={form.ncm ?? ""}
              onChange={handleChange}
              className="w-full border rounded-md px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label className="block text-sm text-slate-600 mb-1">CFOP (opcional)</label>
            <input
              name="cfop"
              value={form.cfop ?? ""}
              onChange={handleChange}
              className="w-full border rounded-md px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label className="block text-sm text-slate-600 mb-1">Movimento (opcional)</label>
            <input
              name="movimento"
              value={form.movimento ?? ""}
              onChange={handleChange}
              className="w-full border rounded-md px-3 py-2 text-sm"
            />
          </div>

          <div className="md:col-span-3">
            <label className="block text-sm text-slate-600 mb-1">Produto (opcional)</label>
            <input
              name="produto"
              value={form.produto ?? ""}
              onChange={handleChange}
              className="w-full border rounded-md px-3 py-2 text-sm"
            />
          </div>
        </div>

        <button
          onClick={handleSimular}
          disabled={loading}
          className="mt-2 inline-flex items-center px-4 py-2 rounded-md text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-60"
        >
          {loading ? "Calculando..." : "Rodar simulação manual"}
        </button>

        {error && <p className="text-sm text-red-600">{error}</p>}
      </div>

      {result && (
        <div className="bg-white rounded-xl shadow-sm p-6 space-y-6">
          <h2 className="font-semibold text-slate-700">Resultado — Ano {result.ano}</h2>

          <div className="grid gap-4 md:grid-cols-4">
            <div className="border rounded-lg p-4">
              <div className="text-xs text-slate-500 mb-1">Carga atual</div>
              <div className="text-lg font-semibold">{money(result.carga_total_atual)}</div>
            </div>

            <div className="border rounded-lg p-4">
              <div className="text-xs text-slate-500 mb-1">Carga reforma</div>
              <div className="text-lg font-semibold">{money(result.carga_total_reforma)}</div>
            </div>

            <div className="border rounded-lg p-4">
              <div className="text-xs text-slate-500 mb-1">Diferença absoluta</div>
              <div className="text-lg font-semibold">{money(result.diferenca_absoluta)}</div>
            </div>

            <div className="border rounded-lg p-4">
              <div className="text-xs text-slate-500 mb-1">Diferença percentual</div>
              <div className="text-lg font-semibold">{percent(result.diferenca_percentual)}</div>
            </div>
          </div>

          <div>
            <h3 className="font-semibold text-slate-700 mb-2">Detalhamento</h3>
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="bg-slate-50">
                  <th className="border px-2 py-1 text-left">Tributo</th>
                  <th className="border px-2 py-1 text-right">Atual</th>
                  <th className="border px-2 py-1 text-right">Reforma</th>
                </tr>
              </thead>
              <tbody>
                {detalhes.map((d) => (
                  <tr key={d.tributo}>
                    <td className="border px-2 py-1">{d.tributo}</td>
                    <td className="border px-2 py-1 text-right">{money(d.atual)}</td>
                    <td className="border px-2 py-1 text-right">{money(d.reforma)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
