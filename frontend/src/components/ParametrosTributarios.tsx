import React, { useEffect, useMemo, useState } from "react";
import {
  createTaxParam,
  deleteTaxParam,
  listTaxParams,
  TaxParamItem,
  TaxParamTipo,
} from "../services/taxParamsApi";

const anosPadrao = [2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033];

export default function ParametrosTributarios() {
  const [anoFiltro, setAnoFiltro] = useState<number>(2026);
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [items, setItems] = useState<TaxParamItem[]>([]);

  const [form, setForm] = useState<TaxParamItem>({
    ano: 2026,
    uf: "AM",
    tipo: "CBS_PADRAO",
    aliquota: 0.009,
    descricao: "Cadastro manual",
  });

  async function carregar() {
    try {
      setLoading(true);
      setErro(null);
      const data = await listTaxParams(anoFiltro);
      setItems(data);
    } catch (e: any) {
      setErro(e?.message ?? "Erro ao carregar parâmetros.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    carregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [anoFiltro]);

  const grouped = useMemo(() => {
    const sorted = [...items].sort((a, b) => {
      const au = (a.uf ?? "BR").toUpperCase();
      const bu = (b.uf ?? "BR").toUpperCase();
      if (a.ano !== b.ano) return a.ano - b.ano;
      if (au !== bu) return au.localeCompare(bu);
      return a.tipo.localeCompare(b.tipo);
    });
    return sorted;
  }, [items]);

  function handleChange(
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>
  ) {
    const { name, value } = e.target;

    if (name === "ano") {
      setForm((p) => ({ ...p, ano: Number(value) }));
      return;
    }
    if (name === "aliquota") {
      setForm((p) => ({ ...p, aliquota: Number(String(value).replace(",", ".")) }));
      return;
    }
    if (name === "uf") {
      setForm((p) => ({ ...p, uf: value ? value.toUpperCase() : null }));
      return;
    }
    if (name === "tipo") {
      setForm((p) => ({ ...p, tipo: value as TaxParamTipo }));
      return;
    }
    if (name === "descricao") {
      setForm((p) => ({ ...p, descricao: value }));
      return;
    }
  }

  async function salvar() {
    try {
      setLoading(true);
      setErro(null);

      const payload: TaxParamItem = {
        ...form,
        uf: form.uf ? form.uf.toUpperCase() : null,
      };

      await createTaxParam(payload);
      await carregar();
    } catch (e: any) {
      setErro(e?.message ?? "Erro ao salvar parâmetro.");
    } finally {
      setLoading(false);
    }
  }

  async function remover(item: TaxParamItem) {
    try {
      setLoading(true);
      setErro(null);
      await deleteTaxParam(item.ano, item.tipo, item.uf ?? null);
      await carregar();
    } catch (e: any) {
      setErro(e?.message ?? "Erro ao remover parâmetro.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-2xl shadow p-5">
        <h2 className="text-xl font-semibold">Parâmetros Tributários</h2>
        <p className="text-sm text-slate-500 mt-1">
          Cadastre CBS/IBS por ano e UF. Se não existir para a UF, o backend usa o
          fallback (geral/BR e depois um default).
        </p>
      </div>

      <div className="bg-white rounded-2xl shadow p-5 space-y-4">
        <div className="flex flex-wrap gap-3 items-end">
          <div>
            <label className="text-sm text-slate-600">Filtrar Ano</label>
            <select
              className="block border rounded-lg px-3 py-2"
              value={anoFiltro}
              onChange={(e) => setAnoFiltro(Number(e.target.value))}
            >
              {anosPadrao.map((a) => (
                <option key={a} value={a}>
                  {a}
                </option>
              ))}
            </select>
          </div>

          <div className="ml-auto">
            <button
              className="px-4 py-2 rounded-lg bg-slate-900 text-white disabled:opacity-60"
              onClick={carregar}
              disabled={loading}
            >
              {loading ? "Carregando..." : "Recarregar"}
            </button>
          </div>
        </div>

        {erro && <div className="text-red-600 text-sm">{erro}</div>}

        <div className="border rounded-xl p-4 space-y-3">
          <div className="font-medium">Novo cadastro</div>

          <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
            <div>
              <label className="text-sm text-slate-600">Ano</label>
              <select
                name="ano"
                className="block w-full border rounded-lg px-3 py-2"
                value={form.ano}
                onChange={handleChange}
              >
                {anosPadrao.map((a) => (
                  <option key={a} value={a}>
                    {a}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-sm text-slate-600">UF (opcional)</label>
              <input
                name="uf"
                className="block w-full border rounded-lg px-3 py-2"
                value={form.uf ?? ""}
                onChange={handleChange}
                placeholder="AM, SP... ou vazio"
              />
            </div>

            <div>
              <label className="text-sm text-slate-600">Tipo</label>
              <select
                name="tipo"
                className="block w-full border rounded-lg px-3 py-2"
                value={form.tipo}
                onChange={handleChange}
              >
                <option value="CBS_PADRAO">CBS_PADRAO</option>
                <option value="IBS_PADRAO">IBS_PADRAO</option>
              </select>
            </div>

            <div>
              <label className="text-sm text-slate-600">Alíquota (decimal)</label>
              <input
                name="aliquota"
                className="block w-full border rounded-lg px-3 py-2"
                value={form.aliquota}
                onChange={handleChange}
                placeholder="0.088"
              />
              <div className="text-xs text-slate-500 mt-1">
                Ex: 0.088 = 8,8%
              </div>
            </div>

            <div>
              <label className="text-sm text-slate-600">Descrição</label>
              <input
                name="descricao"
                className="block w-full border rounded-lg px-3 py-2"
                value={form.descricao ?? ""}
                onChange={handleChange}
                placeholder="Opcional"
              />
            </div>
          </div>

          <button
            className="px-4 py-2 rounded-lg bg-emerald-600 text-white disabled:opacity-60"
            onClick={salvar}
            disabled={loading}
          >
            {loading ? "Salvando..." : "Salvar parâmetro"}
          </button>
        </div>

        <div className="border rounded-xl overflow-hidden">
          <div className="px-4 py-3 bg-slate-50 font-medium">Cadastros</div>

          <div className="overflow-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-white sticky top-0">
                <tr className="text-left border-b">
                  <th className="px-4 py-3">Ano</th>
                  <th className="px-4 py-3">UF</th>
                  <th className="px-4 py-3">Tipo</th>
                  <th className="px-4 py-3">Alíquota</th>
                  <th className="px-4 py-3">Descrição</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody>
                {grouped.map((it, idx) => (
                  <tr key={idx} className="border-b">
                    <td className="px-4 py-3">{it.ano}</td>
                    <td className="px-4 py-3">{(it.uf ?? "BR").toUpperCase()}</td>
                    <td className="px-4 py-3">{it.tipo}</td>
                    <td className="px-4 py-3">{it.aliquota}</td>
                    <td className="px-4 py-3">{it.descricao ?? ""}</td>
                    <td className="px-4 py-3 text-right">
                      <button
                        className="px-3 py-1 rounded-lg border hover:bg-slate-50 disabled:opacity-60"
                        onClick={() => remover(it)}
                        disabled={loading}
                      >
                        Remover
                      </button>
                    </td>
                  </tr>
                ))}

                {grouped.length === 0 && (
                  <tr>
                    <td className="px-4 py-6 text-slate-500" colSpan={6}>
                      Nenhum parâmetro cadastrado para o filtro atual.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
