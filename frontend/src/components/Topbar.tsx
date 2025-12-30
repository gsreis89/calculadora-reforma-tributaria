// frontend/src/components/Topbar.tsx
import React, { useMemo } from "react";

type TopbarProps = {
  periodoInicio: string; // "YYYY-MM-DD" ou ""
  periodoFim: string;    // "YYYY-MM-DD" ou ""
  onChangePeriodoInicio: (v: string) => void;
  onChangePeriodoFim: (v: string) => void;
  onAplicar: () => void;
  applying?: boolean;
};

export const Topbar: React.FC<TopbarProps> = ({
  periodoInicio,
  periodoFim,
  onChangePeriodoInicio,
  onChangePeriodoFim,
  onAplicar,
  applying = false,
}) => {
  const periodoLabel = useMemo(() => {
    if (!periodoInicio && !periodoFim) return "Período: todos";
    if (periodoInicio && !periodoFim) return `Período: ${periodoInicio} em diante`;
    if (!periodoInicio && periodoFim) return `Período: até ${periodoFim}`;
    return `Período: ${periodoInicio} até ${periodoFim}`;
  }, [periodoInicio, periodoFim]);

  return (
    <div className="bg-white border-b">
      <div className="px-6 py-3 flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-3 flex-wrap">
          {/* Mantive placeholders visuais para Empresa/Cenário (você pode ligar depois) */}
          <select className="border rounded-md px-3 py-2 text-sm bg-white" disabled>
            <option>Empresa Exemplo</option>
          </select>

          {/* Período (funcional) */}
          <div className="flex items-center gap-2">
            <input
              type="date"
              value={periodoInicio}
              onChange={(e) => onChangePeriodoInicio(e.target.value)}
              className="border rounded-md px-3 py-2 text-sm"
            />
            <span className="text-sm text-slate-500">até</span>
            <input
              type="date"
              value={periodoFim}
              onChange={(e) => onChangePeriodoFim(e.target.value)}
              className="border rounded-md px-3 py-2 text-sm"
            />
          </div>

          <select className="border rounded-md px-3 py-2 text-sm bg-white" disabled>
            <option>Cenário Base</option>
          </select>

          <div className="text-xs text-slate-500">{periodoLabel}</div>
        </div>

        <button
          onClick={onAplicar}
          disabled={applying}
          className="inline-flex items-center px-4 py-2 rounded-md text-sm font-medium
                     bg-slate-900 text-white hover:bg-slate-800 disabled:opacity-60"
        >
          {applying ? "Aplicando..." : "Aplicar período"}
        </button>
      </div>
    </div>
  );
};
