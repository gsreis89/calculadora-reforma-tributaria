from fastapi import APIRouter
from . import health, simulation_manual, tax_params, database, dashboard, dashboard_compare, simulator_v2, simulator_v4

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(simulation_manual.router)
api_router.include_router(tax_params.router)
api_router.include_router(database.router)
api_router.include_router(dashboard.router)
api_router.include_router(dashboard_compare.router)
api_router.include_router(simulator_v2.router)
api_router.include_router(simulator_v4.router)
