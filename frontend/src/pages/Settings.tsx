import React from "react";

export const Settings: React.FC = () => {
  return (
    <div className="space-y-4">
      <h3 className="text-base font-semibold text-slate-800">Configurações</h3>
      <p className="text-xs text-slate-500">
        Área reservada para ajustes futuros (usuários, temas, integrações).
      </p>

      <div className="bg-white rounded-xl shadow-sm p-4 text-xs text-slate-600">
        <p>
          Nesta versão de protótipo, as configurações ainda não estão
          implementadas. Assim que a API e as regras estiverem mais maduras,
          podemos trazer:
        </p>
        <ul className="list-disc list-inside mt-2 space-y-1">
          <li>Gestão de usuários e permissões</li>
          <li>Preferências de layout e idioma</li>
          <li>Parâmetros globais da simulação</li>
        </ul>
      </div>
    </div>
  );
};
