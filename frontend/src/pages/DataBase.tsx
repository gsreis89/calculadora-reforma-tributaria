import React, { useEffect, useMemo, useState } from "react";
import { parseCsvPreview, validateColumns, CsvPreview } from "../utils/csvPreview";

type Summary = {
  exists: boolean;
  path: string;
  rows: number;
  min_date: string | null;
  max_date: string | null;
  ufs_origem: string[];
  ufs_destino: string[];
  receita_total: number;
  icms_total: number;
  pis_total: number;
  cofins_total: number;
};

type Status = {
  exists: boolean;
  path: string;
  rows: number;
};

const REQUIRED_COLUMNS = [
  "dhemi",
  "uf",
  "uf_dest",
  "vprod",
  "vicms_icms",
  "vpis",
  "vcofins",
];

const API = "http://127.0.0.1:8000";

export const DataBase: React.FC = () => {
  const [status, setStatus] = useState<Status | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);

  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const [preview, setPreview] = useState<CsvPreview | null>(null);
  const [validationMissing, setValidationMissing] = useState<string[]>([]);

  const formatMoney = (v: number) => `R$ ${v.toFixed(2).replace(".", ",")}`;

  async function loadStatus() {
    const r = await fetch(`${API}/database/status`);
    const data = (await r.json()) as Status;
    setStatus(data);
  }

  async function loadSummary() {
    const r = await fetch(`${API}/database/summary`);
    const data = (await r.json()) as Summary;
    setSummary(data);
  }

  useEffect(() => {
    loadStatus();
    loadSummary();
  }, []);

  async function handleDownloadTemplate() {
    const r = await fetch(`${API}/database/template-csv`);
    if (!r.ok) {
      setMsg("Não foi possível baixar o template.");
      return;
    }

    const blob = await r.blob();
    const url = window.URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = "template_nfe_itens.csv";
    document.body.appendChild(a);
    a.click();
    a.remove();

    window.URL.revokeObjectURL(url);
  }

  async function handleFileChange(f: File | null) {
    setFile(f);
    setMsg(null);
    setPreview(null);
    setValidationMissing([]);

    if (!f) return;

    if (!f.name.toLowerCase().endsWith(".csv")) {
      setMsg("Selecione um arquivo .csv");
      return;
    }

    const text = await f.text();
    const pv = parseCsvPreview(text, 20);
    setPreview(pv);

    const check = validateColumns(pv.header, REQUIRED_COLUMNS);
    if (!check.ok) {
      setValidationMissing(check.missing);
      setMsg(`CSV inválido. Faltam colunas obrigatórias: ${check.missing.join(", ")}`);
    }
  }

  async function handleUpload() {
    if (!file) {
      setMsg("Selecione um arquivo CSV.");
      return;
    }

    if (validationMissing.length > 0) {
      setMsg(`Corrija o CSV antes de enviar. Faltam: ${validationMissing.join(", ")}`);
      return;
    }

    setLoading(true);
    setMsg(null);

    try {
      const form = new FormData();
      form.append("file", file);

      const r = await fetch(`${API}/database/import-csv`, {
        method: "POST",
        body: form,
      });

      if (!r.ok) {
        let detail = "Falha ao importar CSV";
        try {
          const err = await r.json();
          detail = err?.detail ?? detail;
        } catch {
          const txt = await r.text();
          if (txt) detail = txt;
        }
        throw new Error(detail);
      }

      const ok = await r.json();
      setMsg(`Importação concluída. Linhas importadas: ${ok.imported_rows}`);

      await loadStatus();
      await loadSummary();
    } catch (e: any) {
      console.error(e);
      setMsg(e?.message ?? "Erro ao importar.");
    } finally {
      setLoading(false);
    }
  }

  async function handleClearDatabase() {
    const confirm = window.confirm(
      "Tem certeza que deseja LIMPAR a base? Isso removerá o dataset importado."
    );
    if (!confirm) return;

    setClearing(true);
    setMsg(null);

    try {
      const r = await fetch(`${API}/database/clear-dataset`, { method: "DELETE" });
      if (!r.ok) {
        let detail = "Falha ao limpar a base de dados";
        try {
          const err = await r.json();
          detail = err?.detail ?? detail;
        } catch {
          const txt = await r.text();
          if (txt) detail = txt;
        }
        throw new Error(detail);
      }

      setMsg("Base de dados limpa com sucesso.");

      // limpa estado local do CSV também
      setFile(null);
      setPreview(null);
      setValidationMissing([]);

      await loadStatus();
      await loadSummary();
    } catch (e: any) {
      console.error(e);
      setMsg(e?.message ?? "Erro ao limpar a base de dados.");
    } finally {
      setClearing(false);
    }
  }

  const previewTable = useMemo(() => {
    if (!preview || preview.header.length === 0) return null;

    return (
      <div className="border rounded-lg overflow-auto">
        <table className="min-w-[900px] w-full text-sm border-collapse">
          <thead>
            <tr className="bg-slate-50">
              {preview.header.map((h) => (
                <th key={h} className="border px-2 py-1 text-left whitespace-nowrap">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {preview.rows.map((row, idx) => (
              <tr key={idx}>
                {preview.header.map((h) => (
                  <td key={h} className="border px-2 py-1 whitespace-nowrap">
                    {row[h] ?? ""}
                  </td>
                ))}
              </tr>
            ))}
            {preview.rows.length === 0 && (
              <tr>
                <td className="border px-2 py-2 text-slate-500" colSpan={preview.header.length}>
                  Nenhuma linha detectada (após o cabeçalho).
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    );
  }, [preview]);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-slate-800">Base de Dados</h1>
        <p className="text-sm text-slate-500 mt-1">
          Upload de CSV no layout padrão para habilitar a simulação (base histórica) sem banco.
        </p>
      </header>

      {/* AÇÕES */}
      <div className="bg-white rounded-xl shadow-sm p-6 space-y-3">
        <h2 className="font-semibold text-slate-700">Ações</h2>
        <button
          onClick={handleClearDatabase}
          disabled={clearing}
          className="inline-flex items-center px-4 py-2 rounded-md text-sm font-medium
                     bg-red-600 text-white hover:bg-red-700 disabled:opacity-60"
        >
          {clearing ? "Limpando..." : "Limpar Base de Dados"}
        </button>
        <p className="text-xs text-slate-500">
          Remove o dataset importado (o CSV armazenado no backend).
        </p>
      </div>

      {/* STATUS */}
      <div className="bg-white rounded-xl shadow-sm p-6 space-y-4">
        <h2 className="font-semibold text-slate-700">Status</h2>
        <div className="text-sm text-slate-700">
          {status ? (
            <>
              <div><b>Existe:</b> {status.exists ? "Sim" : "Não"}</div>
              <div><b>Linhas:</b> {status.rows}</div>
              <div className="text-xs text-slate-400 break-all"><b>Arquivo:</b> {status.path}</div>
            </>
          ) : (
            "Carregando..."
          )}
        </div>
      </div>

      {/* RESUMO */}
      <div className="bg-white rounded-xl shadow-sm p-6 space-y-4">
        <h2 className="font-semibold text-slate-700">Resumo do dataset</h2>

        {!summary ? (
          <div className="text-sm text-slate-500">Carregando resumo...</div>
        ) : !summary.exists ? (
          <div className="text-sm text-slate-600">
            Ainda não existe dataset importado. Importe um CSV para gerar o resumo.
          </div>
        ) : (
          <>
            <div className="grid gap-4 md:grid-cols-4">
              <div className="border rounded-lg p-4">
                <div className="text-xs text-slate-500 mb-1">Período</div>
                <div className="text-sm font-semibold">
                  {summary.min_date ?? "-"} até {summary.max_date ?? "-"}
                </div>
              </div>

              <div className="border rounded-lg p-4">
                <div className="text-xs text-slate-500 mb-1">Receita total</div>
                <div className="text-sm font-semibold">{formatMoney(summary.receita_total)}</div>
              </div>

              <div className="border rounded-lg p-4">
                <div className="text-xs text-slate-500 mb-1">UFs Origem</div>
                <div className="text-sm font-semibold">{summary.ufs_origem.length}</div>
              </div>

              <div className="border rounded-lg p-4">
                <div className="text-xs text-slate-500 mb-1">UFs Destino</div>
                <div className="text-sm font-semibold">{summary.ufs_destino.length}</div>
              </div>
            </div>

            <div className="text-sm text-slate-600 space-y-1">
              <div><b>UF Origem:</b> {summary.ufs_origem.join(", ") || "-"}</div>
              <div><b>UF Destino:</b> {summary.ufs_destino.join(", ") || "-"}</div>

              <div className="pt-2">
                <b>Totais tributos (base atual):</b>{" "}
                ICMS {formatMoney(summary.icms_total)} | PIS {formatMoney(summary.pis_total)} | COFINS{" "}
                {formatMoney(summary.cofins_total)}
              </div>

              <div className="text-xs text-slate-400 break-all pt-2">
                <b>Arquivo:</b> {summary.path}
              </div>
            </div>
          </>
        )}
      </div>

      {/* IMPORTAR CSV */}
      <div className="bg-white rounded-xl shadow-sm p-6 space-y-4">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <h2 className="font-semibold text-slate-700">Importar CSV</h2>

          <button
            onClick={handleDownloadTemplate}
            className="inline-flex items-center px-3 py-2 rounded-md text-sm font-medium
                       bg-slate-900 text-white hover:bg-slate-800"
          >
            Baixar template CSV
          </button>
        </div>

        <div className="text-sm text-slate-600">
          <div><b>Colunas obrigatórias:</b> {REQUIRED_COLUMNS.join(", ")}</div>
          <div><b>Opcionais:</b> ncm, produto, cfop, movimento</div>
        </div>

        <input
          type="file"
          accept=".csv"
          onChange={(e) => handleFileChange(e.target.files?.[0] ?? null)}
          className="block w-full text-sm"
        />

        {validationMissing.length > 0 && (
          <div className="text-sm text-red-600">
            Faltam colunas: <b>{validationMissing.join(", ")}</b>
          </div>
        )}

        <button
          onClick={handleUpload}
          disabled={loading || !file || validationMissing.length > 0}
          className="inline-flex items-center px-4 py-2 rounded-md text-sm font-medium
                     bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-60"
        >
          {loading ? "Importando..." : "Importar CSV"}
        </button>

        {msg && <p className="text-sm text-slate-700">{msg}</p>}
      </div>

      {/* PRÉ-VISUALIZAÇÃO */}
      {preview && (
        <div className="bg-white rounded-xl shadow-sm p-6 space-y-3">
          <h2 className="font-semibold text-slate-700">Pré-visualização (até 20 linhas)</h2>
          <p className="text-sm text-slate-500">
            Confirme se as colunas e os valores estão corretos antes de importar.
          </p>
          {previewTable}
        </div>
      )}
    </div>
  );
};
