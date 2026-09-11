from fastapi import FastAPI


app = FastAPI(
    title="F1 Telemetry API",
    description="Backend API for the F1 telemetry dashboard.",
    version="0.1.0",
)


@app.get("/")
async def root():
    return {
        "name": "F1 Telemetry API",
        "status": "online",
        "version": "0.1.0",
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
    }