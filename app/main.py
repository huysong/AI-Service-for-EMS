# app/main.py
import os

from fastapi import FastAPI
from app.api.router import api_router
import uvicorn

app = FastAPI(title="API Speech 2 Text Processing")

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "EMS CAD AI Service is running API v1"}


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port
    )