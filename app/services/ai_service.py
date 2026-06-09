# app/services/ai_service.py
from app.schemas.ai_analysis import AIAnalysisResult

class AIService:
    async def analyze_voice_call(self, audio_bytes: bytes) -> AIAnalysisResult:
        """
        Hàm xử lý file âm thanh cuộc gọi khẩn cấp.
        Hiện tại: Trả về kịch bản mock chuẩn hóa theo cấu trúc DB v1.
        Sau này: Tích hợp mô hình offline (Whisper/Vosk) tại đây.
        """
        # Giả lập xử lý đọc file âm thanh...
        
        return AIAnalysisResult(
            ai_transcript="Alo cấp cứu ạ! Ở dưới đường Lê Văn Lương đang có tai nạn giao thông nghiêm trọng, một người bị bất tỉnh, máu chảy nhiều lắm, hình như gãy cả xương cổ nữa!",
            ai_urgency_prediction="CRITICAL",  # Khớp với ENUM/VARCHAR trong DB
            ai_confidence_score=94.50,         # Khớp với NUMERIC(5,2)
            
            service_type_code="MED_ACCIDENT",  # Khớp với unique type_code của bảng service_types
            extracted_symptoms=["Bất tỉnh", "Mất nhiều máu", "Chấn thương cổ"],
            suggested_equipment=[
                "Cervical_Collar", 
                "Spine_Board",
                "Trauma_Kit",
                "Oxygen_Tank"
            ]
        )

ai_service = AIService()