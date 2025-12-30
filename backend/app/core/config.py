# backend/app/core/config.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def create_app() -> FastAPI:
    app = FastAPI(
        title="API Calculadora da Reforma",
        version="0.3.0",
    )

    # CORS (desenvolvimento)
    #app.add_middleware(
        #CORSMiddleware,
       # allow_origins=["*"],
        #allow_credentials=True,
       # allow_methods=["*"],
        #allow_headers=["*"],
    #)


        # CORS (desenvolvimento)
    app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    )

    # Importa aqui para evitar import circular
    from app.api.routes import api_router
    app.include_router(api_router)

    return app
