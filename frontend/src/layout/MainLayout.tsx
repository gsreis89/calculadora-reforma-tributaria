import React, { useCallback, useState } from "react";
import { Sidebar } from "../components/Sidebar";
import { Topbar } from "../components/Topbar";

import { Dashboard } from "../pages/Dashboard";
import { Simulator } from "../pages/Simulator";
import { DataBase } from "../pages/DataBase";
// ... outros imports

export type PageKey =
  | "dashboard"
  | "simulator"
  | "scenarios"
  | "database"
  | "tax_params"
  | "settings";

export const MainLayout = ({ currentPage, onChangePage }: any) => {
  // =========================
  // Estado global (Topbar)
  // =========================
  const [periodoInicio, setPeriodoInicio] = useState<string>("");
  const [periodoFim, setPeriodoFim] = useState<string>("");

  // Token para “aplicar” (forçar páginas a recarregar quando clicar no botão)
  const [applyToken, setApplyToken] = useState<number>(0);
  const [applying, setApplying] = useState(false);

  const onAplicarPeriodo = useCallback(() => {
    // validação simples
    if (periodoInicio && periodoFim && periodoInicio > periodoFim) {
      alert("Período inválido: 'Início' não pode ser maior que 'Fim'.");
      return;
    }
    setApplying(true);
    // Só incrementa token (as páginas que usam token recarregam)
    setApplyToken((t) => t + 1);
    // UX: desativa botão por um instante
    window.setTimeout(() => setApplying(false), 250);
  }, [periodoInicio, periodoFim]);

  const renderPage = () => {
    switch (currentPage) {
      case "dashboard":
        return (
          <Dashboard
            periodoInicio={periodoInicio}
            periodoFim={periodoFim}
            applyToken={applyToken}
          />
        );
      case "simulator":
      return (
        <Simulator
          periodoInicio={periodoInicio}
          periodoFim={periodoFim}
          applyToken={applyToken}
        />
      );
      case "database":
        return <DataBase />;
      default:
        return (
          <div className="bg-white rounded-xl shadow-sm p-6">
            Em construção.
          </div>
        );
    }
  };

  return (
    <div className="min-h-screen flex bg-slate-100">
      <Sidebar currentPage={currentPage} onChangePage={onChangePage} />

      <div className="flex-1 flex flex-col">
        <Topbar
          periodoInicio={periodoInicio}
          periodoFim={periodoFim}
          onChangePeriodoInicio={setPeriodoInicio}
          onChangePeriodoFim={setPeriodoFim}
          onAplicar={onAplicarPeriodo}
          applying={applying}
        />

        <main className="p-6">{renderPage()}</main>
      </div>
    </div>
  );
};
