# backend/app/api/routes/database_template.py
from fastapi import APIRouter
from fastapi.responses import Response

router = APIRouter(prefix="/database", tags=["Base de Dados"])


TEMPLATE_CSV = """dhemi,uf,uf_dest,vprod,vicms_icms,vpis,vcofins,ncm,produto,cfop,movimento
2024-01-05,AM,SP,1000.00,180.00,16.50,76.00,30049099,Dipirona 500mg,6102,SAIDA
2024-02-10,AM,RJ,2500.00,450.00,41.25,190.00,21069090,Suplemento Alimentar,6101,SAIDA
"""


@router.get("/template-csv")
def download_template_csv():
    return Response(
        content=TEMPLATE_CSV,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="template_nfe_itens.csv"'},
    )
