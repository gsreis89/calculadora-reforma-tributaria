import React, { useState } from "react";
import { MainLayout, PageKey } from "./layout/MainLayout";

export default function App() {
  const [currentPage, setCurrentPage] = useState<PageKey>("dashboard");

  return <MainLayout currentPage={currentPage} onChangePage={setCurrentPage} />;
}
