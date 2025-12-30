from typing import Optional
from sqlalchemy.orm import Session

from app.models.tax_param import TaxParam


def upsert_tax_param(db: Session, ano: int, uf: str, tipo: str, aliquota: float, descricao: str | None):
    uf = uf.upper().strip()
    tipo = tipo.upper().strip()

    existing = (
        db.query(TaxParam)
        .filter(TaxParam.ano == ano, TaxParam.uf == uf, TaxParam.tipo == tipo)
        .first()
    )

    if existing:
        existing.aliquota = aliquota
        existing.descricao = descricao
        db.commit()
        db.refresh(existing)
        return existing

    obj = TaxParam(ano=ano, uf=uf, tipo=tipo, aliquota=aliquota, descricao=descricao)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def list_tax_params(db: Session, ano: Optional[int] = None, uf: Optional[str] = None, tipo: Optional[str] = None):
    q = db.query(TaxParam)

    if ano is not None:
        q = q.filter(TaxParam.ano == ano)
    if uf:
        q = q.filter(TaxParam.uf == uf.upper().strip())
    if tipo:
        q = q.filter(TaxParam.tipo == tipo.upper().strip())

    return q.order_by(TaxParam.ano.asc(), TaxParam.uf.asc(), TaxParam.tipo.asc()).all()


def get_rate(db: Session, ano: int, uf: str, tipo: str, default: float | None = None, required: bool = True) -> float:
    uf = uf.upper().strip()
    tipo = tipo.upper().strip()

    row = (
        db.query(TaxParam)
        .filter(TaxParam.ano == ano, TaxParam.uf == uf, TaxParam.tipo == tipo)
        .first()
    )

    if row:
        return float(row.aliquota)

    if default is not None:
        return float(default)

    if required:
        raise ValueError(f"Parâmetro não cadastrado: ano={ano}, uf={uf}, tipo={tipo}")

    return 0.0
