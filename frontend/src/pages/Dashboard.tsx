// frontend/src/pages/Dashboard.tsx
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
  BarChart,
  Bar,
} from "recharts";

const API = "http://127.0.0.1:8000";

/** =========================
 * Types
 * ========================= */
type Status = {
  exists: boolean;
  path: string;
  rows: number;
};

type DashboardPageProps = {
  periodoInicio?: string; // "YYYY-MM-DD" ou ""
  periodoFim?: string; // "YYYY-MM-DD" ou ""
  applyToken?: number; // incrementa ao clicar "Aplicar período" na Topbar
};

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

type Kpis = {
  receita_total: number;
  carga_atual_total: number;
  icms_total: number;
  pis_total: number;
  cofins_total: number;
};

type TimeSeriesPoint = {
  period: string; // "YYYY-MM"
  receita: number;
  icms: number;
  pis: number;
  cofins: number;
};

type DashboardOverview = {
  status: Status;
  summary: Summary;
  kpis?: Kpis;
  timeseries?: TimeSeriesPoint[];
};

type CompareKpis = {
  ano_reforma: number;
  receita_total: number;
  carga_atual_total: number;
  carga_reforma_total: number;
  diferenca_absoluta: number;
  diferenca_percentual: number;
};

type CompareTributo = {
  tributo: string;
  atual: number;
  reforma: number;
};

type CompareTimeSeriesPoint = {
  period: string;
  receita: number;
  atual: number;
  reforma: number;
};

type DashboardCompare = {
  kpis: CompareKpis;
  detalhes: CompareTributo[];
  timeseries: CompareTimeSeriesPoint[];
};

type DashboardFilters = {
  periodo_inicio: string; // "YYYY-MM-DD"
  periodo_fim: string; // "YYYY-MM-DD"
  uf_origem: string;
  uf_destino: string;
  ncm: string;
  produto: string;
  cfop: string;
};

type BreakdownItem = { key: string; value: number };

type DashboardBreakdowns = {
  distinct: { produtos: number; ncm: number; cfop: number };
  movimento: BreakdownItem[];
  top_produtos: BreakdownItem[];
  top_ncm: BreakdownItem[];
  top_cfop: BreakdownItem[];
  top_uf_origem: BreakdownItem[];
  top_uf_destino: BreakdownItem[];
};

// Simulator v4 (Credit Ledger + Cash Ledger)
type CreditLedgerSummary = {
  credito_gerado: number;
  glosa: number;
  credito_apos_glosa: number;
  credito_apropriado: number;
  saldo_a_apropriar: number;
};

type CashLedgerSummary = {
  prazo_medio_dias: number;
  split_percent: number;
  residual_installments: number;
  total_caixa: number;
  total_residual: number;
  pico_caixa: { period: string; value: number } | null;
};

type SimulatorV4RunResponse = {
  credit_ledger?: { summary?: CreditLedgerSummary };
  cash_ledger?: { summary?: CashLedgerSummary };
};

/** =========================
 * Helpers
 * ========================= */
function safeNumber(v: any) {
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
}

// moeda com separador de milhares (pt-BR)
const BRL = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});
function formatMoneyBR(v: number) {
  return BRL.format(safeNumber(v));
}
function formatPercentBR(v: number) {
  const n = safeNumber(v);
  return `${n.toFixed(2).replace(".", ",")}%`;
}

// eixo Y com separador, sem “R$” no tick
const NUM0 = new Intl.NumberFormat("pt-BR", {
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
});
function formatAxisNumber(v: any) {
  return NUM0.format(safeNumber(v));
}

function truncateLabel(s: any, max = 14) {
  const t = String(s ?? "");
  if (t.length <= max) return t;
  return t.slice(0, max - 1) + "…";
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

function SkeletonCard() {
  return (
    <div className="bg-white rounded-xl shadow-sm p-5">
      <div className="h-3 w-24 bg-slate-200 rounded mb-3" />
      <div className="h-6 w-40 bg-slate-200 rounded" />
    </div>
  );
}

function ChartSkeleton(props: { title: string }) {
  return (
    <div className="bg-white rounded-xl shadow-sm p-6">
      <div className="text-sm font-semibold text-slate-800">{props.title}</div>

      <div className="h-[300px] mt-3">
        <div className="h-full w-full rounded-lg bg-slate-100 relative overflow-hidden">
          <div className="absolute inset-0 animate-pulse bg-gradient-to-r from-slate-100 via-slate-200 to-slate-100" />
          <div className="absolute bottom-4 left-4 right-4 flex gap-2">
            <div className="h-2 w-2/12 bg-slate-200 rounded" />
            <div className="h-2 w-3/12 bg-slate-200 rounded" />
            <div className="h-2 w-4/12 bg-slate-200 rounded" />
          </div>
        </div>
      </div>
    </div>
  );
}

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

function InfoPill(props: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs bg-slate-100 text-slate-700">
      {props.children}
    </span>
  );
}

/** =========================
 * Autocomplete (Produto/NCM/CFOP)
 * ========================= */
type SuggestField = "produto" | "ncm" | "cfop";

type AutocompleteProps = {
  field: SuggestField;
  value: string;
  onChangeValue: (v: string) => void;
  placeholder?: string;
  className?: string;
  disabled?: boolean;
  queryParams: Record<string, string | undefined>;
};

const AutocompleteInput: React.FC<AutocompleteProps> = ({
  field,
  value,
  onChangeValue,
  placeholder,
  className,
  disabled = false,
  queryParams,
}) => {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);

  const boxRef = useRef<HTMLDivElement | null>(null);
  const debounceRef = useRef<number | null>(null);

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (!boxRef.current) return;
      if (!boxRef.current.contains(e.target as Node)) {
        setOpen(false);
        setActiveIndex(-1);
      }
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  useEffect(() => {
    const q = (value || "").trim();

    // evita “tabela gigante”: sugerir a partir de 2 caracteres
    if (q.length < 2) {
      setItems([]);
      setOpen(false);
      setActiveIndex(-1);
      return;
    }

    if (debounceRef.current) window.clearTimeout(debounceRef.current);

    debounceRef.current = window.setTimeout(async () => {
      try {
        setLoading(true);

        const qs = buildQuery({
          field,
          q,
          limit: 10,
          ...queryParams,
        });

        const r = await fetch(`${API}/dashboard/suggest${qs}`);
        if (!r.ok) {
          setItems([]);
          setOpen(false);
          return;
        }

        // ✅ BACKEND retorna: { items: [...] }
        const json = (await r.json()) as { items?: string[] };
        const list = Array.isArray(json?.items) ? json.items.slice(0, 10) : [];

        setItems(list);
        setOpen(list.length > 0);
        setActiveIndex(-1);
      } catch {
        setItems([]);
        setOpen(false);
      } finally {
        setLoading(false);
      }
    }, 250);

    return () => {
      if (debounceRef.current) window.clearTimeout(debounceRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, field, JSON.stringify(queryParams)]);

  function selectItem(v: string) {
    onChangeValue(v);
    setOpen(false);
    setActiveIndex(-1);
  }

  return (
    <div ref={boxRef} className="relative">
      <input
        disabled={disabled}
        value={value}
        onChange={(e) => onChangeValue(e.target.value)}
        placeholder={placeholder}
        className={className}
        onFocus={() => {
          if (items.length > 0) setOpen(true);
        }}
        onKeyDown={(e) => {
          if (!open || items.length === 0) return;

          if (e.key === "ArrowDown") {
            e.preventDefault();
            setActiveIndex((i) => Math.min(i + 1, items.length - 1));
          } else if (e.key === "ArrowUp") {
            e.preventDefault();
            setActiveIndex((i) => Math.max(i - 1, 0));
          } else if (e.key === "Enter") {
            if (activeIndex >= 0 && activeIndex < items.length) {
              e.preventDefault();
              selectItem(items[activeIndex]);
            }
          } else if (e.key === "Escape") {
            setOpen(false);
            setActiveIndex(-1);
          }
        }}
      />

      {(open || loading) && (loading || items.length > 0) && (
        <div className="absolute z-50 mt-1 w-full bg-white border rounded-md shadow-lg max-h-64 overflow-auto">
          {loading && <div className="px-3 py-2 text-xs text-slate-500">Buscando...</div>}

          {!loading &&
            items.map((it, idx) => (
              <button
                type="button"
                key={`${it}-${idx}`}
                onMouseDown={(e) => e.preventDefault()} // mantém foco no input
                onClick={() => selectItem(it)}
                className={`w-full text-left px-3 py-2 text-sm hover:bg-slate-100 ${
                  idx === activeIndex ? "bg-slate-100" : ""
                }`}
                title={it}
              >
                {it}
              </button>
            ))}
        </div>
      )}
    </div>
  );
};

/** =========================
 * Component
 * ========================= */
export const Dashboard: React.FC<DashboardPageProps> = ({
  periodoInicio = "",
  periodoFim = "",
  applyToken = 0,
}) => {
  // OVERVIEW
  const [data, setData] = useState<DashboardOverview | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  // COMPARE
  const [anoReforma, setAnoReforma] = useState<number>(2027);
  const [compare, setCompare] = useState<DashboardCompare | null>(null);
  const [compareLoading, setCompareLoading] = useState(false);
  const [compareErr, setCompareErr] = useState<string | null>(null);

  // BREAKDOWNS
  const [breakdowns, setBreakdowns] = useState<DashboardBreakdowns | null>(null);
  const [bdLoading, setBdLoading] = useState(false);
  const [bdErr, setBdErr] = useState<string | null>(null);

  // SIMULATOR V4 (Credit/Cash Ledger)
  const [simV4, setSimV4] = useState<SimulatorV4RunResponse | null>(null);
  const [simV4Loading, setSimV4Loading] = useState(false);
  const [simV4Err, setSimV4Err] = useState<string | null>(null);

  // requests (overview/compare/breakdowns)
  const abortRef = useRef<AbortController | null>(null);

  // FILTERS
  const [filters, setFilters] = useState<DashboardFilters>({
    periodo_inicio: "",
    periodo_fim: "",
    uf_origem: "",
    uf_destino: "",
    ncm: "",
    produto: "",
    cfop: "",
  });

  const [appliedFilters, setAppliedFilters] = useState<DashboardFilters>({
    periodo_inicio: "",
    periodo_fim: "",
    uf_origem: "",
    uf_destino: "",
    ncm: "",
    produto: "",
    cfop: "",
  });

  function onChangeFilter(e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) {
    const { name, value } = e.target;
    setFilters((prev) => ({ ...prev, [name]: value }));
  }

  // ✅ Centraliza e paraleliza overview + compare + breakdowns, com cancelamento
  async function loadAll(year: number, f: DashboardFilters) {
    // cancela requests anteriores
    abortRef.current?.abort();
    abortRef.current = new AbortController();
    const { signal } = abortRef.current;

    const qsBase = {
      periodo_inicio: f.periodo_inicio || undefined,
      periodo_fim: f.periodo_fim || undefined,
      uf_origem: f.uf_origem || undefined,
      uf_destino: f.uf_destino || undefined,
      ncm: f.ncm || undefined,
      produto: f.produto || undefined,
      cfop: f.cfop || undefined,
    };

    const qsOverview = buildQuery(qsBase);
    const qsCompare = buildQuery({ ...qsBase, ano_reforma: year });
    const qsBreakdowns = buildQuery({ ...qsBase, limit: 10 });

    setLoading(true);
    setCompareLoading(true);
    setBdLoading(true);

    setErr(null);
    setCompareErr(null);
    setBdErr(null);

    try {
      const [r1, r2, r3] = await Promise.all([
        fetch(`${API}/dashboard/overview${qsOverview}`, { signal }),
        fetch(`${API}/dashboard/compare${qsCompare}`, { signal }),
        fetch(`${API}/dashboard/breakdowns${qsBreakdowns}`, { signal }),
      ]);

      if (!r1.ok) throw new Error(`Falha overview: ${r1.status} ${await r1.text()}`);
      if (!r2.ok) throw new Error(`Falha compare: ${r2.status} ${await r2.text()}`);
      if (!r3.ok) throw new Error(`Falha breakdowns: ${r3.status} ${await r3.text()}`);

      const [j1, j2, j3] = await Promise.all([r1.json(), r2.json(), r3.json()]);

      setData(j1 as DashboardOverview);
      setCompare(j2 as DashboardCompare);
      setBreakdowns(j3 as DashboardBreakdowns);
    } catch (e: any) {
      // Abort não é erro real
      if (e?.name === "AbortError") return;

      console.error(e);
      const msg = e?.message ?? "Erro ao carregar dados.";
      setErr(msg);

      // opcional: limpar para não ficar com dado antigo
      // setData(null);
      // setCompare(null);
      // setBreakdowns(null);
    } finally {
      setLoading(false);
      setCompareLoading(false);
      setBdLoading(false);
    }
  }

  // Mantidas por compatibilidade (não são mais chamadas)
  async function loadOverview(f: DashboardFilters) {
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
      });

      const r = await fetch(`${API}/dashboard/overview${qs}`);
      if (!r.ok) {
        const t = await r.text();
        throw new Error(`Falha ao carregar dashboard: ${r.status} ${t}`);
      }

      const json = (await r.json()) as DashboardOverview;
      setData(json);
    } catch (e: any) {
      console.error(e);
      setErr(e?.message ?? "Erro ao carregar o dashboard.");
      setData(null);
    } finally {
      setLoading(false);
    }
  }

  async function loadCompare(year: number, f: DashboardFilters) {
    try {
      setCompareLoading(true);
      setCompareErr(null);

      const qs = buildQuery({
        ano_reforma: year,
        periodo_inicio: f.periodo_inicio || undefined,
        periodo_fim: f.periodo_fim || undefined,
        uf_origem: f.uf_origem || undefined,
        uf_destino: f.uf_destino || undefined,
        ncm: f.ncm || undefined,
        produto: f.produto || undefined,
        cfop: f.cfop || undefined,
      });

      const r = await fetch(`${API}/dashboard/compare${qs}`);
      if (!r.ok) {
        const t = await r.text();
        throw new Error(`Falha ao carregar comparativo: ${r.status} ${t}`);
      }

      const json = (await r.json()) as DashboardCompare;
      setCompare(json);
    } catch (e: any) {
      console.error(e);
      setCompareErr(e?.message ?? "Erro ao carregar comparativo.");
      setCompare(null);
    } finally {
      setCompareLoading(false);
    }
  }

  async function loadBreakdowns(f: DashboardFilters) {
    try {
      setBdLoading(true);
      setBdErr(null);

      const qs = buildQuery({
        periodo_inicio: f.periodo_inicio || undefined,
        periodo_fim: f.periodo_fim || undefined,
        uf_origem: f.uf_origem || undefined,
        uf_destino: f.uf_destino || undefined,
        ncm: f.ncm || undefined,
        produto: f.produto || undefined,
        cfop: f.cfop || undefined,
        limit: 10,
      });

      const r = await fetch(`${API}/dashboard/breakdowns${qs}`);
      if (!r.ok) {
        const t = await r.text();
        throw new Error(`Falha ao carregar breakdowns: ${r.status} ${t}`);
      }

      const json = (await r.json()) as DashboardBreakdowns;
      setBreakdowns(json);
    } catch (e: any) {
      console.error(e);
      setBdErr(e?.message ?? "Erro ao carregar breakdowns.");
      setBreakdowns(null);
    } finally {
      setBdLoading(false);
    }
  }

  async function loadSimulatorV4(f: DashboardFilters) {
    try {
      setSimV4Loading(true);
      setSimV4Err(null);

      const qs = buildQuery({
        periodo_inicio: f.periodo_inicio || undefined,
        periodo_fim: f.periodo_fim || undefined,
        uf_origem: f.uf_origem || undefined,
        uf_destino: f.uf_destino || undefined,
        ncm: f.ncm || undefined,
        produto: f.produto || undefined,
        cfop: f.cfop || undefined,

        // cenário mínimo para o ledger (ajuste depois via UI)
        prazo_medio_dias: 30,
      });

      const r = await fetch(`${API}/simulator/v4/run${qs}`);
      if (!r.ok) {
        const t = await r.text();
        throw new Error(`Falha ao carregar simulator v4: ${r.status} ${t}`);
      }

      const json = (await r.json()) as SimulatorV4RunResponse;
      setSimV4(json);
    } catch (e: any) {
      console.error(e);
      setSimV4Err(e?.message ?? "Erro ao carregar simulator v4.");
      setSimV4(null);
    } finally {
      setSimV4Loading(false);
    }
  }

  function resetFilters() {
    const empty: DashboardFilters = {
      periodo_inicio: "",
      periodo_fim: "",
      uf_origem: "",
      uf_destino: "",
      ncm: "",
      produto: "",
      cfop: "",
    };
    setFilters(empty);
    setAppliedFilters(empty);
    loadAll(anoReforma, empty);
    loadSimulatorV4(empty);
  }

  function applyFilters() {
    const pi = (filters.periodo_inicio || "").trim();
    const pf = (filters.periodo_fim || "").trim();
    if (pi && pf && pi > pf) {
      alert("Período inválido: 'Início' não pode ser maior que 'Fim'.");
      return;
    }

    const normalized: DashboardFilters = {
      periodo_inicio: pi,
      periodo_fim: pf,
      uf_origem: (filters.uf_origem || "").trim().toUpperCase(),
      uf_destino: (filters.uf_destino || "").trim().toUpperCase(),
      ncm: (filters.ncm || "").trim(),
      produto: (filters.produto || "").trim(),
      cfop: (filters.cfop || "").trim(),
    };

    setAppliedFilters(normalized);
    loadAll(anoReforma, normalized);
    loadSimulatorV4(normalized);
  }

  // primeiro load
  useEffect(() => {
    loadAll(anoReforma, appliedFilters);
    loadSimulatorV4(appliedFilters);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // integração Topbar (período global)
  useEffect(() => {
    if (!applyToken) return;
    if (periodoInicio && periodoFim && periodoInicio > periodoFim) return;

    setFilters((prev) => ({
      ...prev,
      periodo_inicio: periodoInicio || "",
      periodo_fim: periodoFim || "",
    }));

    const nextApplied: DashboardFilters = {
      ...appliedFilters,
      periodo_inicio: periodoInicio || "",
      periodo_fim: periodoFim || "",
    };

    setAppliedFilters(nextApplied);
    loadAll(anoReforma, nextApplied);
    loadSimulatorV4(nextApplied);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [applyToken]);

  const hasBase = !!data?.status?.exists;

  const summaryCards = useMemo(() => {
    const s = data?.summary;
    if (!s?.exists) return null;

    return [
      { label: "Período (base)", value: `${s.min_date ?? "-"} até ${s.max_date ?? "-"}` },
      { label: "Receita total", value: formatMoneyBR(s.receita_total) },
      { label: "Linhas", value: String(s.rows) },
      { label: "UFs Origem", value: String(s.ufs_origem?.length ?? 0) },
      { label: "UFs Destino", value: String(s.ufs_destino?.length ?? 0) },
      { label: "ICMS", value: formatMoneyBR(s.icms_total) },
      { label: "PIS", value: formatMoneyBR(s.pis_total) },
      { label: "COFINS", value: formatMoneyBR(s.cofins_total) },
    ];
  }, [data]);

  const series = useMemo(() => {
    const ts = data?.timeseries ?? [];
    return ts.map((p) => {
      const receita = safeNumber((p as any).receita);
      const icms = safeNumber((p as any).icms);
      const pis = safeNumber((p as any).pis);
      const cofins = safeNumber((p as any).cofins);
      return {
        period: (p as any).period,
        receita,
        icms,
        pis,
        cofins,
        carga_atual: icms + pis + cofins,
      };
    });
  }, [data]);

  const kpis = useMemo(() => {
    if (data?.kpis) return data.kpis;
    const s = data?.summary;
    if (!s?.exists) return null;
    return {
      receita_total: safeNumber(s.receita_total),
      carga_atual_total: safeNumber(s.icms_total) + safeNumber(s.pis_total) + safeNumber(s.cofins_total),
      icms_total: safeNumber(s.icms_total),
      pis_total: safeNumber(s.pis_total),
      cofins_total: safeNumber(s.cofins_total),
    } as Kpis;
  }, [data]);

  const compareSeries = useMemo(() => {
    const ts = compare?.timeseries ?? [];
    return ts.map((p) => ({
      period: (p as any).period,
      receita: safeNumber((p as any).receita),
      atual: safeNumber((p as any).atual),
      reforma: safeNumber((p as any).reforma),
    }));
  }, [compare]);

  const compareDetalhes = useMemo(() => {
    const det = compare?.detalhes ?? [];
    return det.map((d) => ({
      tributo: d.tributo,
      atual: safeNumber(d.atual),
      reforma: safeNumber(d.reforma),
      dif: safeNumber(d.reforma) - safeNumber(d.atual),
    }));
  }, [compare]);

  const activeFiltersLabel = useMemo(() => {
    const parts: string[] = [];

    if (appliedFilters.periodo_inicio || appliedFilters.periodo_fim) {
      parts.push(
        `Período: ${appliedFilters.periodo_inicio || "início"} → ${appliedFilters.periodo_fim || "fim"}`
      );
    }
    if (appliedFilters.uf_origem) parts.push(`UF Origem: ${appliedFilters.uf_origem}`);
    if (appliedFilters.uf_destino) parts.push(`UF Destino: ${appliedFilters.uf_destino}`);
    if (appliedFilters.ncm) parts.push(`NCM: ${appliedFilters.ncm}`);
    if (appliedFilters.produto) parts.push(`Produto: "${appliedFilters.produto}"`);
    if (appliedFilters.cfop) parts.push(`CFOP: ${appliedFilters.cfop}`);

    return parts.length ? parts.join(" • ") : "Sem filtros";
  }, [appliedFilters]);

  const anyLoading = loading || compareLoading || bdLoading || simV4Loading;

  // base params para sugestão (contexto por período/UF)
  const suggestBaseParams = useMemo(() => {
    return {
      periodo_inicio: filters.periodo_inicio || undefined,
      periodo_fim: filters.periodo_fim || undefined,
      uf_origem: (filters.uf_origem || "").trim() ? filters.uf_origem.trim().toUpperCase() : undefined,
      uf_destino: (filters.uf_destino || "").trim() ? filters.uf_destino.trim().toUpperCase() : undefined,
    };
  }, [filters.periodo_inicio, filters.periodo_fim, filters.uf_origem, filters.uf_destino]);

  // pills do “Recorte atual”
  const appliedPills = useMemo(() => {
    const out: string[] = [];
    if (appliedFilters.periodo_inicio || appliedFilters.periodo_fim) {
      out.push(
        `Período: ${appliedFilters.periodo_inicio || "início"} → ${appliedFilters.periodo_fim || "fim"}`
      );
    }
    if (appliedFilters.uf_origem) out.push(`UF Origem: ${appliedFilters.uf_origem}`);
    if (appliedFilters.uf_destino) out.push(`UF Destino: ${appliedFilters.uf_destino}`);
    if (appliedFilters.ncm) out.push(`NCM: ${appliedFilters.ncm}`);
    if (appliedFilters.cfop) out.push(`CFOP: ${appliedFilters.cfop}`);
    if (appliedFilters.produto) out.push(`Produto: ${appliedFilters.produto}`);
    return out;
  }, [appliedFilters]);

  return (
    <div className="w-full px-6 space-y-6">
      {/* HEADER */}
      <header className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-2xl font-semibold text-slate-800">Dashboard</h1>
          <p className="text-sm text-slate-500 mt-1">
            Visão geral da base importada (CSV), indicadores e comparativo da reforma.
          </p>
        </div>

        <button
          onClick={() => {
            loadAll(anoReforma, appliedFilters);
            loadSimulatorV4(appliedFilters);
          }}
          disabled={anyLoading}
          className="inline-flex items-center px-3 py-2 rounded-md text-sm font-medium bg-slate-900 text-white hover:bg-slate-800 disabled:opacity-60"
        >
          {anyLoading ? "Atualizando..." : "Atualizar tudo"}
        </button>
      </header>

      {/* FILTER BAR */}
      <div className="bg-white rounded-xl shadow-sm p-5 space-y-4">
        <SectionTitle
          title="Filtros"
          subtitle={activeFiltersLabel}
          right={
            <div className="flex items-center gap-2">
              <button
                onClick={resetFilters}
                disabled={anyLoading}
                className="inline-flex items-center px-3 py-2 rounded-md text-sm font-medium bg-slate-100 text-slate-800 hover:bg-slate-200 disabled:opacity-60"
              >
                Limpar
              </button>

              <button
                onClick={applyFilters}
                disabled={anyLoading}
                className="inline-flex items-center px-3 py-2 rounded-md text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-60"
              >
                Aplicar
              </button>
            </div>
          }
        />

        {/* Linha 1: Período */}
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

          <div className="md:col-span-2 text-xs text-slate-500">
            Observação: o período da Topbar também é aplicado ao clicar em <b>Aplicar período</b>.
          </div>
        </div>

        {/* Linha 2: UF/NCM/Produto/CFOP */}
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
            <AutocompleteInput
              field="ncm"
              value={filters.ncm}
              onChangeValue={(v) => setFilters((prev) => ({ ...prev, ncm: v }))}
              placeholder="Ex: 12345678"
              className="w-full border rounded-md px-3 py-2 text-sm"
              queryParams={{
                ...suggestBaseParams,
                produto: filters.produto || undefined,
                cfop: filters.cfop || undefined,
              }}
            />
            <div className="text-[10px] text-slate-400 mt-1">Digite 2+ caracteres.</div>
          </div>

          <div>
            <label className="block text-xs text-slate-500 mb-1">Produto</label>
            <AutocompleteInput
              field="produto"
              value={filters.produto}
              onChangeValue={(v) => setFilters((prev) => ({ ...prev, produto: v }))}
              placeholder="Ex: açúcar"
              className="w-full border rounded-md px-3 py-2 text-sm"
              queryParams={{
                ...suggestBaseParams,
                ncm: filters.ncm || undefined,
                cfop: filters.cfop || undefined,
              }}
            />
            <div className="text-[10px] text-slate-400 mt-1">Digite 2+ caracteres.</div>
          </div>

          <div>
            <label className="block text-xs text-slate-500 mb-1">CFOP</label>
            <AutocompleteInput
              field="cfop"
              value={filters.cfop}
              onChangeValue={(v) => setFilters((prev) => ({ ...prev, cfop: v }))}
              placeholder="Ex: 5102"
              className="w-full border rounded-md px-3 py-2 text-sm"
              queryParams={{
                ...suggestBaseParams,
                ncm: filters.ncm || undefined,
                produto: filters.produto || undefined,
              }}
            />
            <div className="text-[10px] text-slate-400 mt-1">Digite 2+ caracteres.</div>
          </div>
        </div>
      </div>

      {/* STATUS + RECORTE */}
      <div className="grid gap-4 lg:grid-cols-3">
        {/* STATUS */}
        <div className="bg-white rounded-xl shadow-sm p-6 lg:col-span-1">
          <SectionTitle title="Status da base" subtitle="Situação do CSV carregado para o dashboard." />
          <div className="mt-4 text-sm text-slate-700">
            {loading ? (
              "Carregando..."
            ) : hasBase ? (
              <>
                <div>
                  <b>Base:</b> OK
                </div>
                <div className="mt-1">
                  <b>Linhas:</b> {data?.status?.rows ?? 0}
                </div>
                <div className="text-xs text-slate-400 break-all mt-3">
                  <b>Arquivo:</b> {data?.status?.path ?? "-"}
                </div>
              </>
            ) : (
              <div>
                <b>Base:</b> ainda não importada. Vá em <b>Base de Dados</b> e faça upload do CSV.
              </div>
            )}
          </div>
        </div>

        {/* RECORTE ATUAL */}
        <div className="bg-white rounded-xl shadow-sm p-6 lg:col-span-2">
          <SectionTitle
            title="Recorte atual"
            subtitle="Confirmação rápida do que está sendo analisado (filtros + base + totais)."
          />

          <div className="mt-4 flex flex-wrap gap-2">
            {appliedPills.length > 0 ? (
              appliedPills.map((p) => <InfoPill key={p}>{p}</InfoPill>)
            ) : (
              <InfoPill>Sem filtros (recorte amplo)</InfoPill>
            )}
          </div>

          <div className="mt-4 grid gap-3 md:grid-cols-4">
            <div className="border rounded-lg p-3">
              <div className="text-[11px] text-slate-500">Período (base)</div>
              <div className="text-sm font-semibold mt-1">
                {data?.summary?.min_date ?? "-"} → {data?.summary?.max_date ?? "-"}
              </div>
            </div>

            <div className="border rounded-lg p-3">
              <div className="text-[11px] text-slate-500">Linhas (recorte)</div>
              <div className="text-sm font-semibold mt-1">{data?.summary?.rows ?? 0}</div>
            </div>

            <div className="border rounded-lg p-3 md:col-span-2">
              <div className="text-[11px] text-slate-500">Receita total (recorte)</div>
              <div className="text-sm font-semibold mt-1">
                {data?.summary?.exists ? formatMoneyBR(safeNumber(data.summary.receita_total)) : formatMoneyBR(0)}
              </div>
            </div>
          </div>

          <div className="mt-3 text-xs text-slate-500">
            UFs (base): origem <b>{data?.summary?.ufs_origem?.join(", ") || "-"}</b> • destino{" "}
            <b>{data?.summary?.ufs_destino?.join(", ") || "-"}</b>
          </div>
        </div>
      </div>

      {/* ERROS */}
      {err && (
        <div className="bg-white rounded-xl shadow-sm p-6">
          <p className="text-sm text-red-600">{err}</p>
          <p className="text-xs text-slate-500 mt-2">
            Dica: DevTools (F12) &gt; Network &gt; GET <b>{API}/dashboard/overview</b>
          </p>
        </div>
      )}

      {compareErr && (
        <div className="bg-white rounded-xl shadow-sm p-6">
          <p className="text-sm text-red-600">{compareErr}</p>
          <p className="text-xs text-slate-500 mt-2">
            Dica: DevTools (F12) &gt; Network &gt; GET <b>{API}/dashboard/compare?ano_reforma={anoReforma}</b>
          </p>
        </div>
      )}

      {bdErr && (
        <div className="bg-white rounded-xl shadow-sm p-6">
          <p className="text-sm text-red-600">{bdErr}</p>
          <p className="text-xs text-slate-500 mt-2">
            Dica: DevTools (F12) &gt; Network &gt; GET <b>{API}/dashboard/breakdowns</b>
          </p>
        </div>
      )}

      {/* EMPTY STATE */}
      {!loading && hasBase && data?.summary?.exists && (data.summary.rows ?? 0) === 0 && (
        <div className="bg-white rounded-xl shadow-sm p-6">
          <div className="text-sm text-slate-700 font-semibold">Nenhum registro encontrado</div>
          <div className="text-sm text-slate-500 mt-1">
            Ajuste os filtros (Período/UF/NCM/Produto/CFOP) e clique em <b>Aplicar</b>.
          </div>
        </div>
      )}

      {/* KPIs (ATUAL) */}
      {loading && (
        <div className="grid gap-4 md:grid-cols-4">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      )}

      {!loading && data?.summary?.exists && kpis && (data.summary.rows ?? 0) > 0 && (
        <div className="grid gap-4 md:grid-cols-4">
          <div className="bg-white rounded-xl shadow-sm p-5">
            <div className="text-xs text-slate-500">Receita total</div>
            <div className="text-xl font-semibold text-slate-900 mt-1">{formatMoneyBR(kpis.receita_total)}</div>
          </div>

          <div className="bg-white rounded-xl shadow-sm p-5">
            <div className="text-xs text-slate-500">Carga atual (ICMS+PIS+COFINS)</div>
            <div className="text-xl font-semibold text-slate-900 mt-1">{formatMoneyBR(kpis.carga_atual_total)}</div>
          </div>

          <div className="bg-white rounded-xl shadow-sm p-5">
            <div className="text-xs text-slate-500">ICMS</div>
            <div className="text-xl font-semibold text-slate-900 mt-1">{formatMoneyBR(kpis.icms_total)}</div>
          </div>

          <div className="bg-white rounded-xl shadow-sm p-5">
            <div className="text-xs text-slate-500">PIS + COFINS</div>
            <div className="text-xl font-semibold text-slate-900 mt-1">
              {formatMoneyBR(kpis.pis_total + kpis.cofins_total)}
            </div>
          </div>
        </div>
      )}

      {/* INSIGHTS (BREAKDOWNS) */}
      <div className="bg-white rounded-xl shadow-sm p-6">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <h2 className="font-semibold text-slate-700">Insights do recorte</h2>
          {bdLoading && <div className="text-xs text-slate-500">Carregando...</div>}
        </div>

        {/* ✅ Skeleton enquanto carrega */}
        {bdLoading ? (
          <div className="grid gap-4 lg:grid-cols-2 mt-6">
            <ChartSkeleton title="Top 10 Produtos (Receita)" />
            <ChartSkeleton title="Top 10 UFs Destino (Receita)" />
            <ChartSkeleton title="Top 10 NCM (Receita)" />
            <ChartSkeleton title="Top 10 CFOP (Receita)" />
          </div>
        ) : breakdowns ? (
          <>
            <div className="grid gap-4 md:grid-cols-4 mt-4">
              <div className="border rounded-lg p-4">
                <div className="text-xs text-slate-500">Produtos distintos</div>
                <div className="text-lg font-semibold mt-1">{breakdowns.distinct.produtos}</div>
              </div>

              <div className="border rounded-lg p-4">
                <div className="text-xs text-slate-500">NCM distintos</div>
                <div className="text-lg font-semibold mt-1">{breakdowns.distinct.ncm}</div>
              </div>

              <div className="border rounded-lg p-4">
                <div className="text-xs text-slate-500">CFOP distintos</div>
                <div className="text-lg font-semibold mt-1">{breakdowns.distinct.cfop}</div>
              </div>

              <div className="border rounded-lg p-4">
                <div className="text-xs text-slate-500">Ticket médio (aprox.)</div>
                <div className="text-lg font-semibold mt-1">
                  {formatMoneyBR((kpis?.receita_total ?? 0) / Math.max(1, data?.summary?.rows ?? 1))}
                </div>
              </div>
            </div>

            <div className="grid gap-4 lg:grid-cols-2 mt-6">
              <div className="border rounded-lg p-4">
                <div className="font-semibold text-slate-700 mb-2">Top 10 Produtos (Receita)</div>
                <div className="h-[260px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={breakdowns.top_produtos}
                      layout="vertical"
                      margin={{ top: 8, right: 12, left: 0, bottom: 8 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis type="number" tickFormatter={formatAxisNumber} tick={{ fontSize: 11 }} />
                      <YAxis
                        type="category"
                        dataKey="key"
                        width={95}
                        tick={{ fontSize: 11 }}
                        tickMargin={4}
                        tickFormatter={(v) => truncateLabel(v, 14)}
                      />
                      <Tooltip content={<TooltipMoney />} />
                      <Bar dataKey="value" name="Receita" isAnimationActive={false} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="border rounded-lg p-4">
                <div className="font-semibold text-slate-700 mb-2">Top 10 UFs Destino (Receita)</div>
                <div className="h-[260px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={breakdowns.top_uf_destino}
                      layout="vertical"
                      margin={{ top: 8, right: 12, left: 0, bottom: 8 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis type="number" tickFormatter={formatAxisNumber} tick={{ fontSize: 11 }} />
                      <YAxis type="category" dataKey="key" width={70} tick={{ fontSize: 11 }} tickMargin={4} />
                      <Tooltip content={<TooltipMoney />} />
                      <Bar dataKey="value" name="Receita" isAnimationActive={false} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="border rounded-lg p-4">
                <div className="font-semibold text-slate-700 mb-2">Top 10 NCM (Receita)</div>
                <div className="h-[260px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={breakdowns.top_ncm}
                      layout="vertical"
                      margin={{ top: 8, right: 12, left: 0, bottom: 8 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis type="number" tickFormatter={formatAxisNumber} tick={{ fontSize: 11 }} />
                      <YAxis type="category" dataKey="key" width={70} tick={{ fontSize: 11 }} tickMargin={4} />
                      <Tooltip content={<TooltipMoney />} />
                      <Bar dataKey="value" name="Receita" isAnimationActive={false} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="border rounded-lg p-4">
                <div className="font-semibold text-slate-700 mb-2">Top 10 CFOP (Receita)</div>
                <div className="h-[260px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={breakdowns.top_cfop}
                      layout="vertical"
                      margin={{ top: 8, right: 12, left: 0, bottom: 8 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis type="number" tickFormatter={formatAxisNumber} tick={{ fontSize: 11 }} />
                      <YAxis type="category" dataKey="key" width={60} tick={{ fontSize: 11 }} tickMargin={4} />
                      <Tooltip content={<TooltipMoney />} />
                      <Bar dataKey="value" name="Receita" isAnimationActive={false} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>

            <div className="border rounded-lg p-4 mt-6">
              <div className="font-semibold text-slate-700 mb-2">Receita por Movimento</div>
              <div className="h-[220px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={breakdowns.movimento} margin={{ top: 8, right: 12, left: 0, bottom: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="key" tick={{ fontSize: 11 }} />
                    <YAxis width={90} tickMargin={6} tickFormatter={formatAxisNumber} tick={{ fontSize: 11 }} />
                    <Tooltip content={<TooltipMoney />} />
                    <Bar dataKey="value" name="Receita" isAnimationActive={false} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </>
        ) : (
          <div className="text-sm text-slate-500 mt-4">Sem dados de breakdown para o recorte atual.</div>
        )}
      </div>

      {/* RESUMO (opcional, mantém como bloco detalhado) */}
      {!loading && summaryCards && (data?.summary?.rows ?? 0) > 0 && (
        <div className="bg-white rounded-xl shadow-sm p-6">
          <SectionTitle title="Resumo do recorte" subtitle="Métricas auxiliares para validação rápida." />
          <div className="grid gap-4 md:grid-cols-4 mt-4">
            {summaryCards.map((c) => (
              <div key={c.label} className="border rounded-lg p-4">
                <div className="text-xs text-slate-500 mb-1">{c.label}</div>
                <div className="text-sm font-semibold">{c.value}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* GRÁFICOS OVERVIEW */}
      {!loading && data?.summary?.exists && series.length > 0 && (
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="bg-white rounded-xl shadow-sm p-6">
            <SectionTitle title="Receita por período" subtitle="Base: vprod" />
            <div className="h-[300px] mt-3">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={series} margin={{ top: 8, right: 12, left: 44, bottom: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="period" minTickGap={24} />
                  <YAxis width={96} tickMargin={8} tickFormatter={formatAxisNumber} tick={{ fontSize: 11 }} />
                  <Tooltip content={<TooltipMoney />} />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="receita"
                    name="Receita"
                    strokeWidth={2}
                    dot={false}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="bg-white rounded-xl shadow-sm p-6">
            <SectionTitle title="Tributos por período" subtitle="ICMS, PIS, COFINS (empilhado)" />
            <div className="h-[300px] mt-3">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={series} margin={{ top: 8, right: 12, left: 44, bottom: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="period" />
                  {/* ✅ CORREÇÃO: YAxis numérico (não category) */}
                  <YAxis width={96} tickMargin={8} tickFormatter={formatAxisNumber} tick={{ fontSize: 11 }} />
                  <Tooltip content={<TooltipMoney />} />
                  <Legend />
                  <Bar dataKey="icms" name="ICMS" stackId="t" isAnimationActive={false} />
                  <Bar dataKey="pis" name="PIS" stackId="t" isAnimationActive={false} />
                  <Bar dataKey="cofins" name="COFINS" stackId="t" isAnimationActive={false} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="text-xs text-slate-500 mt-2">Observação: no MVP, “carga atual” = ICMS + PIS + COFINS.</div>
          </div>
        </div>
      )}

      {/* COMPARATIVO REFORMA */}
      <div className="bg-white rounded-xl shadow-sm p-5">
        <SectionTitle
          title="Comparativo Reforma"
          subtitle="Selecione o ano do cronograma (2026–2033) para simular CBS/IBS no recorte."
          right={
            <div className="flex items-center gap-2">
              <select
                className="border rounded-md px-3 py-2 text-sm"
                value={anoReforma}
                onChange={(e) => {
                  const y = Number(e.target.value);
                  setAnoReforma(y);
                  loadAll(y, appliedFilters);
                }}
              >
                {[2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033].map((y) => (
                  <option key={y} value={y}>
                    {y}
                  </option>
                ))}
              </select>

              <button
                onClick={() => loadAll(anoReforma, appliedFilters)}
                disabled={compareLoading}
                className="inline-flex items-center px-3 py-2 rounded-md text-sm font-medium bg-slate-900 text-white hover:bg-slate-800 disabled:opacity-60"
              >
                {compareLoading ? "Atualizando..." : "Atualizar comparativo"}
              </button>
            </div>
          }
        />

        {/* KPI COMPARATIVO */}
        {compareLoading && (
          <div className="grid gap-4 md:grid-cols-4 mt-4">
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </div>
        )}

        {!compareLoading && compare?.kpis && hasBase && (data?.summary?.rows ?? 0) > 0 && (
          <div className="grid gap-4 md:grid-cols-4 mt-4">
            <div className="bg-slate-50 rounded-xl p-5 border">
              <div className="text-xs text-slate-500">Carga atual</div>
              <div className="text-xl font-semibold text-slate-900 mt-1">{formatMoneyBR(compare.kpis.carga_atual_total)}</div>
            </div>

            <div className="bg-slate-50 rounded-xl p-5 border">
              <div className="text-xs text-slate-500">Carga reforma ({compare.kpis.ano_reforma})</div>
              <div className="text-xl font-semibold text-slate-900 mt-1">{formatMoneyBR(compare.kpis.carga_reforma_total)}</div>
            </div>

            <div className="bg-slate-50 rounded-xl p-5 border">
              <div className="text-xs text-slate-500">Diferença (R$)</div>
              <div className="text-xl font-semibold text-slate-900 mt-1">{formatMoneyBR(compare.kpis.diferenca_absoluta)}</div>
            </div>

            <div className="bg-slate-50 rounded-xl p-5 border">
              <div className="text-xs text-slate-500">Diferença (%)</div>
              <div className="text-xl font-semibold text-slate-900 mt-1">{formatPercentBR(compare.kpis.diferenca_percentual)}</div>
            </div>
          </div>
        )}
      </div>

      {/* GRÁFICOS + TABELA COMPARATIVO */}
      {!compareLoading && compareSeries.length > 0 && (
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="bg-white rounded-xl shadow-sm p-6">
            <SectionTitle title="Carga por período — Atual vs Reforma" subtitle={`Ano reforma: ${anoReforma}`} />
            <div className="h-[300px] mt-3">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={compareSeries} margin={{ top: 8, right: 12, left: 44, bottom: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="period" minTickGap={24} />
                  <YAxis width={96} tickMargin={8} tickFormatter={formatAxisNumber} tick={{ fontSize: 11 }} />
                  <Tooltip content={<TooltipMoney />} />
                  <Legend />
                  <Line type="monotone" dataKey="atual" name="Atual" strokeWidth={2} dot={false} isAnimationActive={false} />
                  <Line type="monotone" dataKey="reforma" name="Reforma" strokeWidth={2} dot={false} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div className="text-xs text-slate-500 mt-2">Observação: no MVP, CBS/IBS estão calculados sobre a receita do período.</div>
          </div>

          <div className="bg-white rounded-xl shadow-sm p-6">
            <SectionTitle title="Detalhes por tributo — Atual vs Reforma" subtitle="Decomposição dos totais." />
            <div className="border rounded-lg overflow-auto mt-3">
              <table className="min-w-[640px] w-full text-sm border-collapse">
                <thead>
                  <tr className="bg-slate-50">
                    <th className="border px-2 py-2 text-left">Tributo</th>
                    <th className="border px-2 py-2 text-right">Atual</th>
                    <th className="border px-2 py-2 text-right">Reforma</th>
                    <th className="border px-2 py-2 text-right">Dif.</th>
                  </tr>
                </thead>
                <tbody>
                  {compareDetalhes.map((d) => (
                    <tr key={d.tributo}>
                      <td className="border px-2 py-2">{d.tributo}</td>
                      <td className="border px-2 py-2 text-right">{formatMoneyBR(d.atual)}</td>
                      <td className="border px-2 py-2 text-right">{formatMoneyBR(d.reforma)}</td>
                      <td className="border px-2 py-2 text-right">{formatMoneyBR(d.dif)}</td>
                    </tr>
                  ))}
                  {compareDetalhes.length === 0 && (
                    <tr>
                      <td className="border px-2 py-3 text-slate-500" colSpan={4}>
                        Sem dados para detalhamento.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            <div className="text-xs text-slate-500 mt-2">Para 2027+: PIS/COFINS ficam 0 no MVP (transição simplificada).</div>
          </div>
        </div>
      )}

      {/* CRÉDITOS + CAIXA (SIMULATOR V4) */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* Créditos */}
        <div className="bg-white rounded-xl shadow-sm p-6">
          <SectionTitle title="Créditos (não cumulatividade)" subtitle="Crédito gerado, glosa, apropriado e saldo a apropriar." />

          {simV4Loading ? (
            <div className="mt-4 text-sm text-slate-500">Carregando...</div>
          ) : simV4Err ? (
            <div className="mt-4 text-sm text-red-600">{simV4Err}</div>
          ) : simV4?.credit_ledger?.summary ? (
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              <div className="border rounded-lg p-4">
                <div className="text-xs text-slate-500">Crédito gerado</div>
                <div className="text-lg font-semibold mt-1">{formatMoneyBR(simV4.credit_ledger.summary.credito_gerado)}</div>
              </div>
              <div className="border rounded-lg p-4">
                <div className="text-xs text-slate-500">Glosa</div>
                <div className="text-lg font-semibold mt-1">{formatMoneyBR(simV4.credit_ledger.summary.glosa)}</div>
              </div>
              <div className="border rounded-lg p-4">
                <div className="text-xs text-slate-500">Crédito apropriado</div>
                <div className="text-lg font-semibold mt-1">{formatMoneyBR(simV4.credit_ledger.summary.credito_apropriado)}</div>
              </div>
              <div className="border rounded-lg p-4">
                <div className="text-xs text-slate-500">Saldo a apropriar</div>
                <div className="text-lg font-semibold mt-1">{formatMoneyBR(simV4.credit_ledger.summary.saldo_a_apropriar)}</div>
              </div>
            </div>
          ) : (
            <div className="mt-4 text-sm text-slate-500">Sem dados de crédito para o recorte atual.</div>
          )}
        </div>

        {/* Caixa */}
        <div className="bg-white rounded-xl shadow-sm p-6">
          <SectionTitle title="Caixa e split payment" subtitle="Simulação de caixa (competência vs caixa), split e residual." />

          {simV4Loading ? (
            <div className="mt-4 text-sm text-slate-500">Carregando...</div>
          ) : simV4Err ? (
            <div className="mt-4 text-sm text-red-600">{simV4Err}</div>
          ) : simV4?.cash_ledger?.summary ? (
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              <div className="border rounded-lg p-4">
                <div className="text-xs text-slate-500">Total caixa</div>
                <div className="text-lg font-semibold mt-1">{formatMoneyBR(simV4.cash_ledger.summary.total_caixa)}</div>
              </div>

              <div className="border rounded-lg p-4">
                <div className="text-xs text-slate-500">Split</div>
                <div className="text-lg font-semibold mt-1">
                  {(safeNumber(simV4.cash_ledger.summary.split_percent) * 100).toFixed(2).replace(".", ",")}%
                </div>
              </div>

              <div className="border rounded-lg p-4">
                <div className="text-xs text-slate-500">Total residual</div>
                <div className="text-lg font-semibold mt-1">{formatMoneyBR(simV4.cash_ledger.summary.total_residual)}</div>
              </div>

              <div className="border rounded-lg p-4">
                <div className="text-xs text-slate-500">Pico de caixa</div>
                <div className="text-sm font-semibold mt-1">
                  {simV4.cash_ledger.summary.pico_caixa
                    ? `${simV4.cash_ledger.summary.pico_caixa.period} • ${formatMoneyBR(
                        simV4.cash_ledger.summary.pico_caixa.value
                      )}`
                    : "-"}
                </div>
              </div>

              <div className="md:col-span-2 text-xs text-slate-500">
                Parcelas residual: <b>{simV4.cash_ledger.summary.residual_installments}</b> • Prazo médio: <b>{simV4.cash_ledger.summary.prazo_medio_dias} dias</b>
              </div>
            </div>
          ) : (
            <div className="mt-4 text-sm text-slate-500">Sem dados de caixa para o recorte atual.</div>
          )}
        </div>
      </div>
    </div>
  );
};
