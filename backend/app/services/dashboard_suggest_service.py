from __future__ import annotations

import os
from typing import List, Optional, Dict

import pandas as pd

# Ajuste este caminho se o seu projeto usa outro padrão.
# A ideia aqui é: usar o MESMO CSV que o overview usa.
_STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage")
_CURRENT_CSV = os.path.join(_STORAGE_DIR, "base_atual.csv")  # <- troque se necessário


def _get_current_csv_path() -> str:
    """
    1) Se você já mantém um 'current.csv' / 'latest.csv', aponte aqui.
    2) Se o overview devolve status.path, o ideal é você salvar esse path aqui também.
    """
    if os.path.exists(_CURRENT_CSV):
        return _CURRENT_CSV

    # fallback comum em projetos: storage/latest.csv
    alt = os.path.join(_STORAGE_DIR, "latest.csv")
    if os.path.exists(alt):
        return alt

    raise FileNotFoundError(
        "CSV atual não encontrado. Verifique o caminho em dashboard_suggest_service.py "
        "e como o upload salva o arquivo em /storage."
    )


def _pick_column(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    cols_lower = {c.lower(): c for c in df.columns}
    for cand in candidates:
        c = cols_lower.get(cand.lower())
        if c:
            return c
    return None


def _apply_optional_filters(
    df: pd.DataFrame,
    periodo_inicio: Optional[str],
    periodo_fim: Optional[str],
    uf_origem: Optional[str],
    uf_destino: Optional[str],
) -> pd.DataFrame:
    # Ajuste os nomes de coluna de data conforme sua base.
    # Aqui tentamos alguns comuns:
    date_col = _pick_column(df, ["dt_emissao", "data_emissao", "dt_doc", "data", "dt"])
    if date_col:
        # parse seguro
        s = pd.to_datetime(df[date_col], errors="coerce")
        if periodo_inicio:
            df = df[s >= pd.to_datetime(periodo_inicio)]
            s = pd.to_datetime(df[date_col], errors="coerce")
        if periodo_fim:
            df = df[s <= pd.to_datetime(periodo_fim)]
            # s pode ficar desalinhado; mas não precisamos mais dele

    col_uf_origem = _pick_column(df, ["uf_origem", "uforigem", "uf_emit", "uf_remetente", "uf_rem"])
    col_uf_destino = _pick_column(df, ["uf_destino", "ufdestino", "uf_dest", "uf_destinatario", "uf_destin"])

    if uf_origem and col_uf_origem:
        df = df[df[col_uf_origem].astype(str).str.upper() == str(uf_origem).upper()]
    if uf_destino and col_uf_destino:
        df = df[df[col_uf_destino].astype(str).str.upper() == str(uf_destino).upper()]

    return df


def suggest_values(
    field: str,
    q: str,
    limit: int = 10,
    periodo_inicio: Optional[str] = None,
    periodo_fim: Optional[str] = None,
    uf_origem: Optional[str] = None,
    uf_destino: Optional[str] = None,
) -> List[str]:
    field = (field or "").strip().lower()
    q = (q or "").strip()

    allowed = {"produto", "ncm", "cfop"}
    if field not in allowed:
        raise ValueError(f"field inválido: {field}. Use: produto | ncm | cfop")

    csv_path = _get_current_csv_path()

    # leitura (otimização: use dtype=str para evitar inferências lentas)
    df = pd.read_csv(csv_path, dtype=str, low_memory=False)

    # tente mapear a coluna conforme o field
    col_map: Dict[str, List[str]] = {
        "produto": ["produto", "xprod", "descricao_produto", "desc_produto", "produto_desc"],
        "ncm": ["ncm", "cod_ncm"],
        "cfop": ["cfop", "cod_cfop"],
    }

    col = _pick_column(df, col_map[field])
    if not col:
        raise ValueError(
            f"Não encontrei coluna para '{field}' no CSV. "
            f"Colunas disponíveis: {list(df.columns)[:30]}..."
        )

    # opcional: respeitar recorte atual
    df = _apply_optional_filters(df, periodo_inicio, periodo_fim, uf_origem, uf_destino)

    s = df[col].dropna().astype(str).str.strip()
    s = s[s != ""]

    # filtro por texto digitado
    if q:
        # contains case-insensitive
        s = s[s.str.contains(q, case=False, regex=False)]

    # pega únicos, ordena, limita
    vals = sorted(s.unique().tolist())[: int(limit)]
    return vals
