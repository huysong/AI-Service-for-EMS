# app/services/ai_service.py
# Compatibility wrapper for refactored services

from app.services.triage_service import triage_service as ai_service
from app.services.speech_service import init_speech_model as init_ai_models
