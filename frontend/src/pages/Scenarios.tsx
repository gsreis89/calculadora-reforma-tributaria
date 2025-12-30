import React from "react";

export const Scenarios: React.FC = () => {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-base font-semibold text-slate-800">Cenários</h3>
        <button className="px-3 py-1.5 text-sm rounded-md bg-slate-900 text-white">
          Novo Cenário
        </button>
      </div>

      <div className="bg-white rounded-xl shadow-sm p-4">
        <table className="w-full text-xs text-left">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-2 py-2">Nome</th>
              <th className="px-2 py-2">Tipo</th>
              <th className="px-2 py-2">Atualizado em</th>
              <th className="px-2 py-2">Ações</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-t">
              <td className="px-2 py-2 text-slate-700">Cenário Base</td>
              <td className="px-2 py-2">OFICIAL</td>
              <td className="px-2 py-2">-</td>
              <td className="px-2 py-2 space-x-2">
                <button className="text-xs text-slate-700 underline">
                  Ver
                </button>
                <button className="text-xs text-slate-700 underline">
                  Editar
                </button>
                <button className="text-xs text-red-500 underline">
                  Excluir
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
};
