# app/api/router.py
from fastapi import APIRouter
from app.api.endpoints import ai_controller

api_router = APIRouter()

api_router.include_router(ai_controller.router, prefix="/ai", tags=["AI Emergency Analysis"])