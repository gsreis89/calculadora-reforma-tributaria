from fastapi import APIRouter
router = APIRouter()

@router.get("/")
def root():
    return {"message": "API Calculadora da Reforma ativa."}

@router.get("/health")
def health():
    return {"status": "ok"}
