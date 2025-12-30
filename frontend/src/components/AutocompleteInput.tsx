import React, { useEffect, useRef, useState } from "react";

type Props = {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  className?: string;

  // backend
  apiUrl: string;              // ex: http://127.0.0.1:8000
  field: "produto" | "ncm" | "cfop";
  limit?: number;

  // filtros atuais para “contextualizar” a sugestão
  queryParams?: Record<string, string | undefined>;
};

export const AutocompleteInput: React.FC<Props> = ({
  value,
  onChange,
  placeholder,
  className,
  apiUrl,
  field,
  limit = 10,
  queryParams = {},
}) => {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeIndex, setActiveIndex] = useState<number>(-1);

  const boxRef = useRef<HTMLDivElement | null>(null);
  const debounceRef = useRef<number | null>(null);

  function buildQS(params: Record<string, any>) {
    const usp = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v === undefined || v === null) return;
      const s = String(v).trim();
      if (!s) return;
      usp.set(k, s);
    });
    return usp.toString() ? `?${usp.toString()}` : "";
  }

  useEffect(() => {
    // fecha ao clicar fora
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
    if (!q) {
      setItems([]);
      setOpen(false);
      setActiveIndex(-1);
      return;
    }

    if (debounceRef.current) window.clearTimeout(debounceRef.current);

    debounceRef.current = window.setTimeout(async () => {
      try {
        setLoading(true);

        const qs = buildQS({
          field,
          q,
          limit,
          ...queryParams,
        });

        const r = await fetch(`${apiUrl}/dashboard/suggest${qs}`);
        if (!r.ok) return;

        const json = (await r.json()) as string[];
        setItems((json || []).slice(0, limit));
        setOpen(true);
        setActiveIndex(-1);
      } finally {
        setLoading(false);
      }
    }, 250);

    return () => {
      if (debounceRef.current) window.clearTimeout(debounceRef.current);
    };
  }, [value, field, limit, apiUrl, JSON.stringify(queryParams)]);

  function selectItem(v: string) {
    onChange(v);
    setOpen(false);
    setActiveIndex(-1);
  }

  return (
    <div ref={boxRef} className="relative">
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
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

      {open && (loading || items.length > 0) && (
        <div className="absolute z-50 mt-1 w-full bg-white border rounded-md shadow-lg max-h-64 overflow-auto">
          {loading && (
            <div className="px-3 py-2 text-xs text-slate-500">Buscando...</div>
          )}

          {!loading && items.map((it, idx) => (
            <button
              type="button"
              key={`${it}-${idx}`}
              onMouseDown={(e) => e.preventDefault()} // evita perder foco antes do click
              onClick={() => selectItem(it)}
              className={`w-full text-left px-3 py-2 text-sm hover:bg-slate-100 ${
                idx === activeIndex ? "bg-slate-100" : ""
              }`}
              title={it}
            >
              {it}
            </button>
          ))}

          {!loading && items.length === 0 && (
            <div className="px-3 py-2 text-xs text-slate-500">Sem sugestões</div>
          )}
        </div>
      )}
    </div>
  );
};
