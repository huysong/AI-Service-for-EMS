from pydantic import BaseModel, Field
from typing import List, Optional

class AIAnalysisResult(BaseModel):
    ai_transcript: str = Field(..., description="Văn bản dịch từ cuộc gọi")
    ai_urgency_prediction: str = Field(..., description="Mức độ khẩn cấp")
    ai_confidence_score: float = Field(..., description="Độ tự tin của AI (0.00 -> 100.00)")

    service_type_code: str = Field(..., description="Mã loại dịch vụ cứu cứu (Ví dụ: 'MED_ACCIDENT', 'MED_STROKE')")
    extracted_symptoms: List[str] = Field(..., description="Danh sách triệu chứng lâm sàng sơ bộ")
    suggested_equipment: List[str] = Field(..., description="Thiết bị y tế gợi ý cần xe cứu thương chuẩn bị")
