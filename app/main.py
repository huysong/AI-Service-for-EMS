# app/main.py
from fastapi import FastAPI
from app.api.router import api_router
import uvicorn

app = FastAPI(title="API Speech 2 Text Processing")

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "EMS CAD AI Service is running API v1"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)