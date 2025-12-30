import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
} from "recharts";

const API = "http://127.0.0.1:8000";

/** =========================
 * Types (compatível com backend /simulator/v4/run)
 * ========================= */
type CreditLedgerSummary = {
  credito_gerado: number;
  glosa: number;
  credito_apos_glosa: number;
  credito_apropriado: number;
  saldo_a_apropriar: number;
};

type CreditLedgerByFinalidadeItem = {
  credito_gerado: number;
  glosa: number;
  credito_apos_glosa: number;
  credito_apropriado_no_periodo: number;
};

type CreditLedgerSeriesPoint = {
  period: string; // "YYYY-MM"
  credito_apropriado: number;
};

type CreditLedger = {
  summary: CreditLedgerSummary;
  by_finalidade: Record<string, CreditLedgerByFinalidadeItem>;
  series: CreditLedgerSeriesPoint[];
};

type SimulatorFilters = {
  periodo_inicio: string;
  periodo_fim: string;
  uf_origem: string;
  uf_destino: string;
  ncm: string;
  produto: string;
  cfop: string;
  movimento: string; // "" | ENTRADA | SAIDA
  finalidade: string; // "" | REVENDA | CONSUMO | ATIVO | TRANSFERENCIA | OUTRAS
  regras_json: string;
};

type SimulatorPageProps = {
  periodoInicio?: string;
  periodoFim?: string;
  applyToken?: number;
};

type BreakdownItem = { key: string; value: number };

type FinalidadeItem = {
  finalidade: string;
  entrada_base: number;
  credito_potencial: number;
  glosa: number;
  credito_aproveitado: number;
  credito_apropriado_no_periodo: number;
};

type SeriesPointV4 = {
  period: string;
  saida_receita: number;
  entrada_base: number;
  atual_total: number;
  reforma_bruta: number;
  credito_aproveitado: number;
  reforma_liquida: number;
  impacto_caixa_estimado: number;
};

type CreditLedger = {
  // mantemos como any para não travar com mudanças rápidas de DTO
  [k: string]: any;
};

type SimulatorV4Response = {
  status: { exists: boolean; path: string; rows: number };
  filtros: Record<string, any>;
  cenario: Record<string, any>;

  base: { rows: number; saida_receita: number; entrada_base: number };
  atual: { icms: number; pis: number; cofins: number; carga_total: number };
  reforma: {
    cbs: number;
    ibs: number;
    is: number;
    carga_bruta: number;
    carga_liquida: number;
  };
  creditos: {
    credito_potencial: number;
    glosa: number;
    credito_aproveitado: number;
    credito_apropriado_no_periodo: number;
  };
  caixa: { prazo_medio_dias: number; impacto_caixa_estimado: number };

  breakdown_movimento: BreakdownItem[];
  breakdown_finalidade: FinalidadeItem[];
  series: SeriesPointV4[];

  credit_ledger?: CreditLedger | null;
  // cash_ledger?: any | null; // (quando existir no backend)
};

/** =========================
 * Helpers
 * ========================= */
function safeNumber(v: any) {
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
}

const BRL = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});
function formatMoneyBR(v: number) {
  return BRL.format(safeNumber(v));
}

const NUM0 = new Intl.NumberFormat("pt-BR", {
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
});
function formatAxisNumber(v: any) {
  return NUM0.format(safeNumber(v));
}

function buildQuery(params: Record<string, string | number | undefined | null>) {
  const usp = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v === undefined || v === null) return;
    const s = String(v).trim();
    if (!s) return;
    usp.set(k, s);
  });
  const qs = usp.toString();
  return qs ? `?${qs}` : "";
}

const TooltipMoney: React.FC<any> = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;

  return (
    <div className="bg-white border rounded-lg shadow-sm px-3 py-2 text-xs text-slate-700">
      <div className="font-semibold mb-1">{label}</div>
      <div className="space-y-1">
        {payload.map((p: any) => (
          <div key={p.dataKey} className="flex justify-between gap-6">
            <span className="text-slate-500">{p.name}</span>
            <span className="font-semibold">{formatMoneyBR(safeNumber(p.value))}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

function SectionTitle(props: { title: string; subtitle?: string; right?: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-3 flex-wrap">
      <div>
        <h2 className="text-base font-semibold text-slate-800">{props.title}</h2>
        {props.subtitle && <p className="text-xs text-slate-500 mt-1">{props.subtitle}</p>}
      </div>
      {props.right ? <div className="shrink-0">{props.right}</div> : null}
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="bg-white rounded-xl shadow-sm p-5">
      <div className="h-3 w-24 bg-slate-200 rounded mb-3" />
      <div className="h-6 w-40 bg-slate-200 rounded" />
    </div>
  );
}

/** =========================
 * Component
 * ========================= */
export const Simulator: React.FC<SimulatorPageProps> = ({
  periodoInicio = "",
  periodoFim = "",
  applyToken = 0,
}) => {
  const abortRef = useRef<AbortController | null>(null);

  const [data, setData] = useState<SimulatorV4Response | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const [filters, setFilters] = useState<SimulatorFilters>({
    periodo_inicio: "",
    periodo_fim: "",
    uf_origem: "",
    uf_destino: "",
    ncm: "",
    produto: "",
    cfop: "",
    movimento: "",
    finalidade: "",
    regras_json: "",
  });

  const [applied, setApplied] = useState<SimulatorFilters>({
    periodo_inicio: "",
    periodo_fim: "",
    uf_origem: "",
    uf_destino: "",
    ncm: "",
    produto: "",
    cfop: "",
    movimento: "",
    finalidade: "",
    regras_json: "",
  });

  function onChangeFilter(e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) {
    const { name, value } = e.target;
    setFilters((prev) => ({ ...prev, [name]: value }));
  }

  async function loadRun(f: SimulatorFilters) {
    abortRef.current?.abort();
    abortRef.current = new AbortController();
    const { signal } = abortRef.current;

    try {
      setLoading(true);
      setErr(null);

      const qs = buildQuery({
        periodo_inicio: f.periodo_inicio || undefined,
        periodo_fim: f.periodo_fim || undefined,
        uf_origem: f.uf_origem || undefined,
        uf_destino: f.uf_destino || undefined,
        ncm: f.ncm || undefined,
        produto: f.produto || undefined,
        cfop: f.cfop || undefined,
        movimento: f.movimento || undefined,
        finalidade: f.finalidade || undefined,
        regras_json: f.regras_json || undefined,
      });

      const r = await fetch(`${API}/simulator/v4/run${qs}`, { signal });
      if (!r.ok) {
        const t = await r.text();
        throw new Error(`Falha ao rodar simulador: ${r.status} ${t}`);
      }

      const json = (await r.json()) as SimulatorV4Response;
      setData(json);
    } catch (e: any) {
      if (e?.name === "AbortError") return;
      console.error(e);
      setErr(e?.message ?? "Erro ao rodar simulador.");
      setData(null);
    } finally {
      setLoading(false);
    }
  }

  function applyFilters() {
    const pi = (filters.periodo_inicio || "").trim();
    const pf = (filters.periodo_fim || "").trim();
    if (pi && pf && pi > pf) {
      alert("Período inválido: 'Início' não pode ser maior que 'Fim'.");
      return;
    }

    // regras_json: opcionalmente valida se é JSON
    const rj = (filters.regras_json || "").trim();
    if (rj) {
      try {
        const obj = JSON.parse(rj);
        if (!Array.isArray(obj)) {
          alert("regras_json deve ser um JSON de lista (array). Ex: [{...},{...}]");
          return;
        }
      } catch {
        alert("regras_json inválido: JSON malformado.");
        return;
      }
    }

    const normalized: SimulatorFilters = {
      periodo_inicio: pi,
      periodo_fim: pf,
      uf_origem: (filters.uf_origem || "").trim().toUpperCase(),
      uf_destino: (filters.uf_destino || "").trim().toUpperCase(),
      ncm: (filters.ncm || "").trim(),
      produto: (filters.produto || "").trim(),
      cfop: (filters.cfop || "").trim(),
      movimento: (filters.movimento || "").trim().toUpperCase(),
      finalidade: (filters.finalidade || "").trim().toUpperCase(),
      regras_json: rj,
    };

    setApplied(normalized);
    loadRun(normalized);
  }

  function resetFilters() {
    const empty: SimulatorFilters = {
      periodo_inicio: "",
      periodo_fim: "",
      uf_origem: "",
      uf_destino: "",
      ncm: "",
      produto: "",
      cfop: "",
      movimento: "",
      finalidade: "",
      regras_json: "",
    };
    setFilters(empty);
    setApplied(empty);
    loadRun(empty);
  }

  // primeiro load
  useEffect(() => {
    loadRun(applied);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // integração Topbar (período global)
  useEffect(() => {
    if (!applyToken) return;
    if (periodoInicio && periodoFim && periodoInicio > periodoFim) return;
  
  const cl = sim?.credit_ledger ?? null;

    setFilters((prev) => ({
      ...prev,
      periodo_inicio: periodoInicio || "",
      periodo_fim: periodoFim || "",
    }));

    const nextApplied: SimulatorFilters = {
      ...applied,
      periodo_inicio: periodoInicio || "",
      periodo_fim: periodoFim || "",
    };

    setApplied(nextApplied);
    loadRun(nextApplied);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [applyToken]);

  const hasBase = !!data?.status?.exists;

  const kpiCards = useMemo(() => {
    if (!data?.status?.exists) return null;
    const rows = safeNumber(data.base?.rows);
    if (rows <= 0) return null;

    return {
      cargaAtual: safeNumber(data.atual?.carga_total),
      bruta: safeNumber(data.reforma?.carga_bruta),
      creditoApropriado: safeNumber(data.creditos?.credito_apropriado_no_periodo),
      liquida: safeNumber(data.reforma?.carga_liquida),
      caixa: safeNumber(data.caixa?.impacto_caixa_estimado),
    };
  }, [data]);

  const chartSeries = useMemo(() => {
    const ts = (data?.series ?? []).map((p) => ({
      period: p.period,
      atual_total: safeNumber(p.atual_total),
      reforma_bruta: safeNumber(p.reforma_bruta),
      reforma_liquida: safeNumber(p.reforma_liquida),
      credito_aproveitado: safeNumber(p.credito_aproveitado),
    }));
    return ts;
  }, [data]);


// -------------------------
// Credit Ledger (derivados)
// -------------------------
const creditLedger = data?.credit_ledger ?? null;

const creditSummary = creditLedger?.summary ?? null;

const creditByFinalidade = React.useMemo(() => {
  const obj = creditLedger?.by_finalidade ?? {};
  if (!obj || typeof obj !== "object") return [];
  return Object.entries(obj).map(([finalidade, v]: any) => ({
    finalidade,
    credito_gerado: safeNumber(v?.credito_gerado),
    glosa: safeNumber(v?.glosa),
    credito_apos_glosa: safeNumber(v?.credito_apos_glosa),
    credito_apropriado_no_periodo: safeNumber(v?.credito_apropriado_no_periodo),
  }));
}, [creditLedger]);

const creditSeries = React.useMemo(() => {
  const arr = creditLedger?.series ?? [];
  if (!Array.isArray(arr)) return [];
  return arr.map((p: any) => ({
    period: String(p?.period ?? ""),
    credito_apropriado: safeNumber(p?.credito_apropriado),
  }));
}, [creditLedger]);


  return (
    <div className="w-full space-y-6">
      {/* HEADER */}
      <header className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-2xl font-semibold text-slate-800">Simulador v4</h1>
          <p className="text-sm text-slate-500 mt-1">
            Simulação de CBS/IBS/IS com crédito (por finalidade), glosa e apropriação de ativo.
          </p>
        </div>

        <button
          onClick={() => loadRun(applied)}
          disabled={loading}
          className="inline-flex items-center px-3 py-2 rounded-md text-sm font-medium bg-slate-900 text-white hover:bg-slate-800 disabled:opacity-60"
        >
          {loading ? "Atualizando..." : "Atualizar"}
        </button>
      </header>

      {/* FILTER BAR */}
      <div className="bg-white rounded-xl shadow-sm p-5 space-y-4">
        <SectionTitle
          title="Filtros (Simulador)"
          subtitle="Use o período da Topbar ou ajuste filtros específicos aqui."
          right={
            <div className="flex items-center gap-2">
              <button
                onClick={resetFilters}
                disabled={loading}
                className="inline-flex items-center px-3 py-2 rounded-md text-sm font-medium bg-slate-100 text-slate-800 hover:bg-slate-200 disabled:opacity-60"
              >
                Limpar
              </button>

              <button
                onClick={applyFilters}
                disabled={loading}
                className="inline-flex items-center px-3 py-2 rounded-md text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-60"
              >
                Aplicar
              </button>
            </div>
          }
        />

        <div className="grid gap-3 md:grid-cols-2">
          <div>
            <label className="block text-xs text-slate-500 mb-1">Período início</label>
            <input
              type="date"
              name="periodo_inicio"
              value={filters.periodo_inicio}
              onChange={onChangeFilter}
              className="w-full border rounded-md px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label className="block text-xs text-slate-500 mb-1">Período fim</label>
            <input
              type="date"
              name="periodo_fim"
              value={filters.periodo_fim}
              onChange={onChangeFilter}
              className="w-full border rounded-md px-3 py-2 text-sm"
            />
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-5">
          <div>
            <label className="block text-xs text-slate-500 mb-1">UF Origem</label>
            <input
              name="uf_origem"
              value={filters.uf_origem}
              onChange={onChangeFilter}
              placeholder="Ex: AM"
              className="w-full border rounded-md px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label className="block text-xs text-slate-500 mb-1">UF Destino</label>
            <input
              name="uf_destino"
              value={filters.uf_destino}
              onChange={onChangeFilter}
              placeholder="Ex: SP"
              className="w-full border rounded-md px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label className="block text-xs text-slate-500 mb-1">NCM</label>
            <input
              name="ncm"
              value={filters.ncm}
              onChange={onChangeFilter}
              placeholder="Ex: 87083090"
              className="w-full border rounded-md px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label className="block text-xs text-slate-500 mb-1">Produto</label>
            <input
              name="produto"
              value={filters.produto}
              onChange={onChangeFilter}
              placeholder="Ex: filtro"
              className="w-full border rounded-md px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label className="block text-xs text-slate-500 mb-1">CFOP</label>
            <input
              name="cfop"
              value={filters.cfop}
              onChange={onChangeFilter}
              placeholder="Ex: 6102"
              className="w-full border rounded-md px-3 py-2 text-sm"
            />
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-3">
          <div>
            <label className="block text-xs text-slate-500 mb-1">Movimento</label>
            <select
              name="movimento"
              value={filters.movimento}
              onChange={onChangeFilter}
              className="w-full border rounded-md px-3 py-2 text-sm"
            >
              <option value="">(Todos)</option>
              <option value="ENTRADA">ENTRADA</option>
              <option value="SAIDA">SAÍDA</option>
            </select>
          </div>

          <div>
            <label className="block text-xs text-slate-500 mb-1">Finalidade</label>
            <select
              name="finalidade"
              value={filters.finalidade}
              onChange={onChangeFilter}
              className="w-full border rounded-md px-3 py-2 text-sm"
            >
              <option value="">(Todas)</option>
              <option value="REVENDA">REVENDA</option>
              <option value="CONSUMO">CONSUMO</option>
              <option value="ATIVO">ATIVO</option>
              <option value="TRANSFERENCIA">TRANSFERÊNCIA</option>
              <option value="OUTRAS">OUTRAS</option>
            </select>
          </div>

          <div>
            <label className="block text-xs text-slate-500 mb-1">Regras (JSON)</label>
            <textarea
              name="regras_json"
              value={filters.regras_json}
              onChange={onChangeFilter}
              placeholder='Ex: [{"match":"cfop_prefix","value":"11","finalidade":"REVENDA","perc_credit":1.0}]'
              className="w-full border rounded-md px-3 py-2 text-sm h-[40px]"
            />
          </div>
        </div>
      </div>

      {/* STATUS / ERROS */}
      {err && (
        <div className="bg-white rounded-xl shadow-sm p-6">
          <p className="text-sm text-red-600">{err}</p>
          <p className="text-xs text-slate-500 mt-2">
            Dica: DevTools (F12) &gt; Network &gt; GET <b>{API}/simulator/v4/run</b>
          </p>
        </div>
      )}

      {!loading && hasBase && data?.base?.rows === 0 && (
        <div className="bg-white rounded-xl shadow-sm p-6">
          <div className="text-sm text-slate-700 font-semibold">Nenhum registro encontrado</div>
          <div className="text-sm text-slate-500 mt-1">
            Ajuste os filtros (Período/UF/NCM/Produto/CFOP) e clique em <b>Aplicar</b>.
          </div>
        </div>
      )}

      {/* KPI Cards */}
      {loading && (
        <div className="grid gap-4 md:grid-cols-4">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      )}

      {!loading && hasBase && kpiCards && (
        <div className="grid gap-4 md:grid-cols-5">
          <div className="bg-white rounded-xl shadow-sm p-5">
            <div className="text-xs text-slate-500">Carga atual (ICMS+PIS+COFINS)</div>
            <div className="text-xl font-semibold text-slate-900 mt-1">{formatMoneyBR(kpiCards.cargaAtual)}</div>
          </div>

          <div className="bg-white rounded-xl shadow-sm p-5">
            <div className="text-xs text-slate-500">Reforma (bruta)</div>
            <div className="text-xl font-semibold text-slate-900 mt-1">{formatMoneyBR(kpiCards.bruta)}</div>
          </div>

          <div className="bg-white rounded-xl shadow-sm p-5">
            <div className="text-xs text-slate-500">Crédito apropriado no período</div>
            <div className="text-xl font-semibold text-slate-900 mt-1">{formatMoneyBR(kpiCards.creditoApropriado)}</div>
          </div>

          <div className="bg-white rounded-xl shadow-sm p-5">
            <div className="text-xs text-slate-500">Reforma (líquida)</div>
            <div className="text-xl font-semibold text-slate-900 mt-1">{formatMoneyBR(kpiCards.liquida)}</div>
          </div>

          <div className="bg-white rounded-xl shadow-sm p-5">
            <div className="text-xs text-slate-500">Impacto caixa (estimado)</div>
            <div className="text-xl font-semibold text-slate-900 mt-1">{formatMoneyBR(kpiCards.caixa)}</div>
          </div>
        </div>
      )}

      {/* Série mensal */}
      {!loading && hasBase && chartSeries.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm p-6">
          <SectionTitle
            title="Série mensal — Carga Atual vs Reforma"
            subtitle="Reforma líquida já considera crédito apropriado no período (ATIVO em 1/N)."
          />

          <div className="h-[320px] mt-4">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartSeries} margin={{ top: 8, right: 12, left: 44, bottom: 8 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="period" minTickGap={24} />
                <YAxis width={96} tickMargin={8} tickFormatter={formatAxisNumber} tick={{ fontSize: 11 }} />
                <Tooltip content={<TooltipMoney />} />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="atual_total"
                  name="Atual"
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                />
                <Line
                  type="monotone"
                  dataKey="reforma_bruta"
                  name="Reforma (bruta)"
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                />
                <Line
                  type="monotone"
                  dataKey="reforma_liquida"
                  name="Reforma (líquida)"
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

{/* Credit Ledger (formatado) */}
{!loading && hasBase && creditLedger && (
  <div className="bg-white rounded-xl shadow-sm p-6">
    <SectionTitle
      title="Credit Ledger"
      subtitle="Resumo de crédito gerado, glosa, apropriado e saldo a apropriar."
    />

    {/* Cards resumo */}
    <div className="grid gap-4 md:grid-cols-5 mt-4">
      <div className="bg-slate-50 rounded-xl p-5 border">
        <div className="text-xs text-slate-500">Crédito gerado</div>
        <div className="text-xl font-semibold text-slate-900 mt-1">
          {formatMoneyBR(safeNumber(creditSummary?.credito_gerado))}
        </div>
      </div>

      <div className="bg-slate-50 rounded-xl p-5 border">
        <div className="text-xs text-slate-500">Glosa</div>
        <div className="text-xl font-semibold text-slate-900 mt-1">
          {formatMoneyBR(safeNumber(creditSummary?.glosa))}
        </div>
      </div>

      <div className="bg-slate-50 rounded-xl p-5 border">
        <div className="text-xs text-slate-500">Crédito após glosa</div>
        <div className="text-xl font-semibold text-slate-900 mt-1">
          {formatMoneyBR(safeNumber(creditSummary?.credito_apos_glosa))}
        </div>
      </div>

      <div className="bg-slate-50 rounded-xl p-5 border">
        <div className="text-xs text-slate-500">Crédito apropriado</div>
        <div className="text-xl font-semibold text-slate-900 mt-1">
          {formatMoneyBR(safeNumber(creditSummary?.credito_apropriado))}
        </div>
      </div>

      <div className="bg-slate-50 rounded-xl p-5 border">
        <div className="text-xs text-slate-500">Saldo a apropriar</div>
        <div className="text-xl font-semibold text-slate-900 mt-1">
          {formatMoneyBR(safeNumber(creditSummary?.saldo_a_apropriar))}
        </div>
      </div>
    </div>

    {/* Tabela por finalidade */}
    <div className="border rounded-lg overflow-auto mt-6">
      <table className="min-w-[980px] w-full text-sm border-collapse">
        <thead>
          <tr className="bg-slate-50">
            <th className="border px-2 py-2 text-left">Finalidade</th>
            <th className="border px-2 py-2 text-right">Crédito gerado</th>
            <th className="border px-2 py-2 text-right">Glosa</th>
            <th className="border px-2 py-2 text-right">Após glosa</th>
            <th className="border px-2 py-2 text-right">Apropriado no período</th>
          </tr>
        </thead>
        <tbody>
          {creditByFinalidade.map((it) => (
            <tr key={it.finalidade}>
              <td className="border px-2 py-2">{it.finalidade}</td>
              <td className="border px-2 py-2 text-right">{formatMoneyBR(it.credito_gerado)}</td>
              <td className="border px-2 py-2 text-right">{formatMoneyBR(it.glosa)}</td>
              <td className="border px-2 py-2 text-right">{formatMoneyBR(it.credito_apos_glosa)}</td>
              <td className="border px-2 py-2 text-right">{formatMoneyBR(it.credito_apropriado_no_periodo)}</td>
            </tr>
          ))}

          {creditByFinalidade.length === 0 && (
            <tr>
              <td className="border px-2 py-3 text-slate-500" colSpan={5}>
                Sem dados por finalidade.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>

    {/* Série (aging / apropriação mês a mês) */}
    {creditSeries.length > 0 && (
      <div className="bg-white rounded-xl shadow-sm p-6 mt-6 border">
        <SectionTitle
          title="Apropriação mensal (crédito apropriado)"
          subtitle="Base para aging e saldo a apropriar por mês."
        />

        <div className="h-[260px] mt-4">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={creditSeries} margin={{ top: 8, right: 12, left: 44, bottom: 8 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="period" minTickGap={24} />
              <YAxis width={96} tickMargin={8} tickFormatter={formatAxisNumber} tick={{ fontSize: 11 }} />
              <Tooltip content={<TooltipMoney />} />
              <Legend />
              <Line
                type="monotone"
                dataKey="credito_apropriado"
                name="Crédito apropriado"
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    )}
  </div>
)}

      {/* Breakdown por Finalidade */}
      {!loading && hasBase && (data?.breakdown_finalidade?.length ?? 0) > 0 && (
        <div className="bg-white rounded-xl shadow-sm p-6">
          <SectionTitle title="Créditos por Finalidade" subtitle="Entrada base e crédito (potencial, glosa e apropriado)." />

          <div className="border rounded-lg overflow-auto mt-4">
            <table className="min-w-[980px] w-full text-sm border-collapse">
              <thead>
                <tr className="bg-slate-50">
                  <th className="border px-2 py-2 text-left">Finalidade</th>
                  <th className="border px-2 py-2 text-right">Entrada base</th>
                  <th className="border px-2 py-2 text-right">Crédito potencial</th>
                  <th className="border px-2 py-2 text-right">Glosa</th>
                  <th className="border px-2 py-2 text-right">Crédito aproveitado</th>
                  <th className="border px-2 py-2 text-right">Apropriado no período</th>
                </tr>
              </thead>
              <tbody>
                {(data?.breakdown_finalidade ?? []).map((it) => (
                  <tr key={it.finalidade}>
                    <td className="border px-2 py-2">{it.finalidade}</td>
                    <td className="border px-2 py-2 text-right">{formatMoneyBR(safeNumber(it.entrada_base))}</td>
                    <td className="border px-2 py-2 text-right">{formatMoneyBR(safeNumber(it.credito_potencial))}</td>
                    <td className="border px-2 py-2 text-right">{formatMoneyBR(safeNumber(it.glosa))}</td>
                    <td className="border px-2 py-2 text-right">{formatMoneyBR(safeNumber(it.credito_aproveitado))}</td>
                    <td className="border px-2 py-2 text-right">{formatMoneyBR(safeNumber(it.credito_apropriado_no_periodo))}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Empty base */}
      {!loading && !hasBase && (
        <div className="bg-white rounded-xl shadow-sm p-6">
          <div className="text-sm text-slate-700 font-semibold">Base ainda não importada</div>
          <div className="text-sm text-slate-500 mt-1">
            Vá em <b>Base de Dados</b> e faça upload do CSV. Depois, volte ao Simulador.
          </div>
        </div>
      )}
    </div>
  );
};
