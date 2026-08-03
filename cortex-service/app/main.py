from fastapi import FastAPI


app = FastAPI(title="Cortex Service")


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
