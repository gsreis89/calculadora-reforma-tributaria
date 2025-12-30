from app.schemas.simulation import SimulationRequest, SimulationResponse, SimulationTributeDetail
from app.schemas.timeline import TaxKey
from .tax_timeline_service import get_year_config

def simulate_taxes(req: SimulationRequest) -> SimulationResponse:
    year_cfg = get_year_config(req.ano)

    carga_antes = req.receita_total * 0.18
    carga_cbs = req.receita_total * 0.01
    carga_ibs = req.receita_total * 0.005
    carga_depois = carga_cbs + carga_ibs

    margem_antes = req.receita_total - (req.receita_total * 0.70) - carga_antes
    margem_depois = req.receita_total - (req.receita_total * 0.70) - carga_depois

    detalhes = [
        SimulationTributeDetail(tributo=TaxKey.CBS, carga_antes=0, carga_depois=carga_cbs),
        SimulationTributeDetail(tributo=TaxKey.IBS, carga_antes=0, carga_depois=carga_ibs),
    ]

    return SimulationResponse(
        empresa_id=req.empresa_id,
        cenario_id=req.cenario_id,
        ano=req.ano,
        periodo_inicio=req.periodo_inicio,
        periodo_fim=req.periodo_fim,
        receita_total=req.receita_total,
        carga_total_antes=carga_antes,
        carga_total_depois=carga_depois,
        margem_antes=margem_antes,
        margem_depois=margem_depois,
        detalhes_por_tributo=detalhes
    )
