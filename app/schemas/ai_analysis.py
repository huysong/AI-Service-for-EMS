from pydantic import BaseModel, Field
from typing import List

class AIAnalysisResult(BaseModel):
    transcript: str = Field(..., description="Văn bản dịch từ cuộc gọi")
    urgency: str = Field(..., description="Mức độ khẩn cấp (CRITICAL, HIGH, MEDIUM, LOW)")
    confidence: float = Field(..., description="Độ tự tin của AI (0.0 -> 100.0)")
    symptoms: List[str] = Field(default_factory=list, description="Danh sách triệu chứng lâm sàng sơ bộ")
