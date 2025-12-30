# backend/app/models/tax_schedule.py
from sqlalchemy import Column, Integer, String, Numeric
from app.db.base import Base

class TaxSchedule(Base):
    __tablename__ = "tax_schedule"

    id = Column(Integer, primary_key=True, index=True)
    ano = Column(Integer, nullable=False, index=True)
    uf = Column(String(2), nullable=False, index=True)
    tipo = Column(String(50), nullable=False, index=True)
    aliquota = Column(Numeric(10, 4), nullable=False)
    descricao = Column(String(255), nullable=True)
