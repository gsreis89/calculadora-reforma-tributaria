# backend/app/services/tax_schedule_service.py
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.tax_schedule import TaxSchedule
from app.schemas.tax_schedule import TaxScheduleCreateUpdate


def get_all(db: Session) -> List[TaxSchedule]:
    return db.query(TaxSchedule).order_by(TaxSchedule.year).all()


def upsert_by_year(db: Session, year: int, data: TaxScheduleCreateUpdate) -> TaxSchedule:
    obj: Optional[TaxSchedule] = (
        db.query(TaxSchedule).filter(TaxSchedule.year == year).first()
    )
    if obj is None:
        obj = TaxSchedule(year=year)
        db.add(obj)

    obj.cbs_rate = data.cbs_rate
    obj.ibs_state_rate = data.ibs_state_rate
    obj.ibs_municipal_rate = data.ibs_municipal_rate
    obj.pis_rate = data.pis_rate
    obj.cofins_rate = data.cofins_rate
    obj.icms_rate = data.icms_rate
    obj.iss_rate = data.iss_rate
    obj.notes = data.notes

    db.commit()
    db.refresh(obj)
    return obj
