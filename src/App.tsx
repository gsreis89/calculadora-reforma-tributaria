// frontend/src/App.tsx
import React, { useState } from "react";
import { Routes, Route, Navigate } from "react-router-dom";

import { MainLayout, PageKey } from "./layout/MainLayout";
import SimulacaoManual from "./SimulacaoManual";

function Shell() {
  const [currentPage, setCurrentPage] = useState<PageKey>("dashboard");

  return <MainLayout currentPage={currentPage} onChangePage={setCurrentPage} />;
}

export default function App() {
  return (
    <Routes>
      {/* Layout principal (Sidebar + Topbar + páginas) */}
      <Route path="/" element={<Shell />} />

      {/* Se quiser manter a simulação manual “separada” como rota */}
      <Route path="/simulacao-manual" element={<SimulacaoManual />} />

      {/* fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
