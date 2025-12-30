// frontend/src/utils/csvPreview.ts
export type CsvPreview = {
  header: string[];
  rows: Record<string, string>[];
  delimiter: string;
};

function normalizeHeader(h: string): string {
  return (h ?? "")
    .replace(/^\uFEFF/, "") // remove BOM se vier do Excel
    .trim()
    .toLowerCase();
}

function sniffDelimiter(text: string): string {
  // pega um pedaço para amostragem
  const sample = text.slice(0, 50_000);

  // conta ocorrências no header/primeiras linhas
  const semicolonCount = (sample.match(/;/g) || []).length;
  const commaCount = (sample.match(/,/g) || []).length;
  const tabCount = (sample.match(/\t/g) || []).length;

  // Heurística simples e efetiva
  if (semicolonCount >= commaCount && semicolonCount >= tabCount) return ";";
  if (commaCount >= tabCount) return ",";
  return "\t";
}

/**
 * Parser simples para preview:
 * - Detecta delimitador (;, , ou tab)
 * - Não trata aspas complexas (para MVP está ótimo)
 */
export function parseCsvPreview(text: string, maxRows = 20): CsvPreview {
  const delimiter = sniffDelimiter(text);

  const lines = text
    .replace(/\r\n/g, "\n")
    .replace(/\r/g, "\n")
    .split("\n")
    .filter((l) => l.trim().length > 0);

  if (lines.length === 0) {
    return { header: [], rows: [], delimiter };
  }

  const rawHeader = lines[0].split(delimiter).map((h) => h.trim());
  const header = rawHeader.map((h) => normalizeHeader(h)).filter(Boolean);

  const rows: Record<string, string>[] = [];

  for (let i = 1; i < lines.length && rows.length < maxRows; i++) {
    const parts = lines[i].split(delimiter);
    const row: Record<string, string> = {};

    for (let c = 0; c < header.length; c++) {
      row[header[c]] = (parts[c] ?? "").trim();
    }
    rows.push(row);
  }

  return { header, rows, delimiter };
}

export function validateColumns(header: string[], required: string[]) {
  const normHeader = header.map(normalizeHeader);
  const missing = required
    .map((c) => normalizeHeader(c))
    .filter((c) => !normHeader.includes(c));

  return {
    ok: missing.length === 0,
    missing,
  };
}
