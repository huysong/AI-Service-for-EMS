# app/worker.py
import asyncio
import json
import logging
import httpx
import os
import uuid
from redis import Redis
from dotenv import load_dotenv

# Load env variables
load_dotenv()

from app.services.ai_service import ai_service, init_ai_models

# Cấu hình logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AIWorker")

# Cấu hình Redis
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
redis_client = Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)

# Cấu hình Callback URL về Spring Boot Backend
SPRING_BOOT_CALLBACK_URL = os.getenv("SPRING_BOOT_CALLBACK_URL", "http://localhost:8080/api/v1/calls/callback")

async def download_audio(url: str) -> bytes:
    """
    Tải file âm thanh từ URL tĩnh do Spring Boot cung cấp.
    """
    async with httpx.AsyncClient() as client:
        logger.info(f"Đang tải file âm thanh từ: {url}")
        response = await client.get(url)
        if response.status_code != 200:
            raise Exception(f"Không thể tải file âm thanh. HTTP status: {response.status_code}")
        return response.content

async def send_callback(call_id: int, transcript: str, urgency: str, confidence: float, symptoms: list):
    """
    Gửi kết quả phân tích AI ngược lại Spring Boot qua HTTP POST Callback
    """
    from app.core.config import settings
    
    payload = {
        "call_id": call_id,
        "transcript": transcript,
        "urgency": urgency,
        "confidence": confidence,
        "symptoms": symptoms
    }
    
    headers = {
        "Content-Type": "application/json",
        "X-Callback-Key": settings.SPRING_BOOT_CALLBACK_KEY
    }
    
    async with httpx.AsyncClient() as client:
        logger.info(f"Đang gửi callback kết quả cho cuộc gọi {call_id} về Spring Boot...")
        response = await client.post(SPRING_BOOT_CALLBACK_URL, json=payload, headers=headers)
        logger.info(f"Phản hồi từ Spring Boot: {response.status_code}")
        if response.status_code not in (200, 204):
            logger.error(f"Gửi callback thất bại. Chi tiết: {response.text}")


async def process_queue():
    """
    Vòng lặp vô hạn lắng nghe hàng đợi Redis và xử lý bằng các mô hình AI.
    """
    logger.info("Đang khởi tạo các mô hình AI (Whisper & Zero-shot Classifier)...")
    init_ai_models()
    logger.info(f"AI Worker khởi chạy thành công. Lắng nghe queue 'emergency:ai:queue' tại {REDIS_HOST}:{REDIS_PORT}...")
    
    while True:
        try:
            # BRPOP từ Redis queue (block 5 giây nếu hàng đợi trống)
            job = redis_client.brpop("emergency:ai:queue", timeout=5)
            if job:
                queue_name, message_bytes = job
                message_str = message_bytes.decode("utf-8")
                logger.info(f"Nhận được job từ hàng đợi: {message_str}")
                
                # Parse JSON message
                job_data = json.loads(message_str)
                call_id = job_data.get("call_id")
                audio_url = job_data.get("audio_url")
                
                if not call_id or not audio_url:
                    logger.warning("Tin nhắn thiếu trường dữ liệu 'call_id' hoặc 'audio_url'. Bỏ qua.")
                    continue
                
                request_id = str(uuid.uuid4())
                
                # 1. Tải audio file
                audio_bytes = await download_audio(audio_url)
                
                # 2. Chạy dịch và phân loại bằng AI
                result = await ai_service.analyze_voice_call(
                    audio_bytes,
                    call_id=call_id,
                    request_id=request_id
                )
                
                # 3. Gửi callback cập nhật dữ liệu về Spring Boot
                await send_callback(
                    call_id=call_id,
                    transcript=result.transcript,
                    urgency=result.urgency,
                    confidence=result.confidence,
                    symptoms=result.symptoms
                )

                
        except Exception as e:
            logger.error(f"Lỗi trong vòng lặp Worker: {str(e)}", exc_info=True)
            # Tránh lặp lỗi quá nhanh làm tràn log
            await asyncio.sleep(2)

if __name__ == "__main__":
    try:
        asyncio.run(process_queue())
    except KeyboardInterrupt:
        logger.info("Worker dừng hoạt động bởi người dùng.")
