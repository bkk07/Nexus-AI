from fastapi import FastAPI

from app.api.routes.ai_routes import ai_router


app = FastAPI(title="Cortex AI Service")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


app.include_router(ai_router, prefix="/internal")