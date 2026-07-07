# app/api/endpoints/ai_controller.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from app.schemas.ai_analysis import AIAnalysisResult
from app.services.ai_service import ai_service
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.services.ai_service import ai_service
from app.core.database import get_db
from fastapi.security import APIKeyHeader
from app.core.config import settings

router = APIRouter()

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

async def verify_api_key(api_key: str = Depends(api_key_header)):
    if api_key != settings.AI_API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Yêu cầu bị từ chối: API Key không hợp lệ"
        )

@router.post("/analyze-call", response_model=AIAnalysisResult, dependencies=[Depends(verify_api_key)])
async def analyze_emergency_call(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    try:

        await db.execute(text("SELECT 1"))
    except Exception as db_err:
        raise HTTPException(
            status_code=500, 
            detail=f"Không thể kết nối đến Cơ sở dữ liệu PostgreSQL: {str(db_err)}"
        )

    valid_extensions = ('.wav', '.mp3', '.m4a', '.ogg', 'txt')
    if not file.filename.lower().endswith(valid_extensions):
        raise HTTPException(
            status_code=400, 
            detail=f"Hệ thống chỉ tiếp nhận các định dạng âm thanh: {', '.join(valid_extensions)}"
        )
        
    try:

        audio_bytes = await file.read()
        
        request_id = str(uuid.uuid4())
        result = await ai_service.analyze_voice_call(audio_bytes, request_id=request_id)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi hệ thống nội bộ: {str(e)}")