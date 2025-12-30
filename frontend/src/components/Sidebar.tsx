import React from "react";
import { useNavigate } from "react-router-dom";
import { PageKey } from "../layout/MainLayout";
import {
  Calculator,
  Database,
  Settings as SettingsIcon,
  LayoutDashboard,
  SlidersHorizontal,
  Percent,
} from "lucide-react";

interface SidebarProps {
  currentPage: PageKey;
  onChangePage: (page: PageKey) => void;
}

type Item = {
  key: PageKey;
  label: string;
  icon: React.ReactNode;
  /** rota do React Router (HashRouter) */
  to: string;
};

const items: Item[] = [
  { key: "dashboard", label: "Dashboard", icon: <LayoutDashboard size={18} />, to: "/dashboard" },
  { key: "simulator", label: "Simulador", icon: <Calculator size={18} />, to: "/simulator-v4" },
  { key: "scenarios", label: "Cenários", icon: <SlidersHorizontal size={18} />, to: "/cenarios" },
  { key: "database", label: "Base de Dados", icon: <Database size={18} />, to: "/database" },
  { key: "tax_params", label: "Parâmetros Tributários", icon: <Percent size={18} />, to: "/tax-params" },
  { key: "settings", label: "Configurações", icon: <SettingsIcon size={18} />, to: "/settings" },
];

export const Sidebar: React.FC<SidebarProps> = ({ currentPage, onChangePage }) => {
  const navigate = useNavigate();

  function go(item: Item) {
    // Mantém seu estado atual (MainLayout) e também navega via HashRouter.
    onChangePage(item.key);
    navigate(item.to);
  }

  return (
    <aside className="w-64 bg-slate-900 text-slate-100 flex flex-col">
      <div className="px-6 py-4 border-b border-slate-800">
        <h1 className="text-lg font-semibold">Calculadora da Reforma</h1>
        <p className="text-xs text-slate-400">Simulador Tributário • Grupo Real</p>
      </div>

      <nav className="flex-1 py-4 space-y-1">
        {items.map((item) => (
          <button
            key={item.key}
            onClick={() => go(item)}
            className={`w-full flex items-center gap-2 px-4 py-2 text-sm text-left hover:bg-slate-800 ${
              currentPage === item.key ? "bg-slate-800 font-semibold" : ""
            }`}
          >
            {item.icon}
            <span>{item.label}</span>
          </button>
        ))}
      </nav>
    </aside>
  );
};
