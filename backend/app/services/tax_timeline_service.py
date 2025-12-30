from typing import Dict, List
from fastapi import HTTPException
from app.schemas.timeline import TaxKey, TaxStatus, TaxConfig, TaxYearConfig

TAX_YEARS: List[int] = [2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033]

TAX_TIMELINE: Dict[int, TaxYearConfig] = {
    2026: {
        TaxKey.PIS: TaxConfig(status=TaxStatus.sem_alteracao),
        TaxKey.COFINS: TaxConfig(status=TaxStatus.sem_alteracao),
        TaxKey.CBS: TaxConfig(status=TaxStatus.novo, aliquota=0.9),
        TaxKey.ICMS: TaxConfig(status=TaxStatus.sem_alteracao),
        TaxKey.ISS: TaxConfig(status=TaxStatus.sem_alteracao),
        TaxKey.IBS: TaxConfig(status=TaxStatus.novo, aliquota=0.1),
        TaxKey.IPI: TaxConfig(status=TaxStatus.sem_alteracao),
        TaxKey.IS: TaxConfig(status=TaxStatus.definido_posteriormente),
    }
}

def list_years() -> List[int]:
    return TAX_YEARS

def get_timeline() -> Dict[int, TaxYearConfig]:
    return TAX_TIMELINE

def get_year_config(ano: int) -> TaxYearConfig:
    if ano not in TAX_TIMELINE:
        raise HTTPException(status_code=404, detail="Ano não encontrado")
    return TAX_TIMELINE[ano]
