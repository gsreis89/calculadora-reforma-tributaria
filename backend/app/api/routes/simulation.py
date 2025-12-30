from fastapi import APIRouter
from app.schemas.simulation import SimulationRequest, SimulationResponse
from app.services.simulation_service import simulate_taxes

router = APIRouter(prefix="/simulate", tags=["simulation"])

@router.post("", response_model=SimulationResponse)
def simulate(req: SimulationRequest):
    return simulate_taxes(req)
