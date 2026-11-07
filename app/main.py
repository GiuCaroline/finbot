from fastapi import FastAPI

from app.api.rotas import router

app = FastAPI(title="FinBot API", description="Chat educacional de investimentos")
app.include_router(router)