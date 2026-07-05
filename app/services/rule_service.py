import re
import logging
from typing import Dict, Any, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RuleService")

KEYWORDS_MAP = {
    "CRITICAL": [
        r"ngừng thở", r"ngưng thở", r"ngừng tim", r"ngưng tim", r"gãy cổ", 
        r"bất tỉnh", r"hôn mê", r"ngất", r"không biết gì", r"nguy kịch", 
        r"sốc phản vệ", r"vỡ động mạch", r"mất nhiều máu", r"nguy cấp", 
        r"sắp chết", r"không thở được", r"nghẹt thở"
    ],
    "HIGH": [
        r"tai nạn", r"tay nạn", r"gãy xương", r"mất máu", r"chảy máu nhiều", 
        r"đột quỵ", r"nhồi máu cơ tim", r"nhồi máu cơ tiêm", r"đau ngực", 
        r"khó thở", r"bị đâm", r"bị bắn", r"bỏng nặng", r"chấn thương sọ não", 
        r"co giật", r"co dật", r"cấp cứu", r"cấp kiếu"
    ],
    "MEDIUM": [
        r"sốt cao", r"xuất cao", r"gãy tay", r"gãy chân", r"đau bụng", r"ngộ độc", 
        r"bỏng nhẹ", r"vết thương sâu", r"nôn mửa", r"hen suyễn", r"co giật nhẹ", r"co dật nhẹ"
    ],
    "LOW": [
        r"cảm cúm", r"sốt nhẹ", r"xây xát", r"đau đầu", r"đau nhức", 
        r"nhờ tư vấn", r"gọi nhầm", r"gọi trêu", r"thử máy", r"alo"
    ]
}

SYMPTOMS_KEYWORDS = {
    "Bất tỉnh / Hôn mê": ["bất tỉnh", "hôn mê", "ngất", "không biết gì"],
    "Mất nhiều máu / Chảy máu": ["chảy máu", "mất máu", "ra máu", "mẫu chảy"],
    "Ngừng thở / Ngạt thở": ["ngừng thở", "ngưng thở", "ngạt thở", "không thở được"],
    "Chấn thương xương / Gãy xương": ["gãy xương", "gãy chân", "gãy tay", "gãy cổ"],
    "Đột quỵ / Tai biến": ["đột quỵ", "tai biến", "tê liệt", "nhồi máu"],
    "Tai nạn giao thông": ["tai nạn", "tay nạn", "đâm xe", "tông xe", "va chạm"],
    "Bị thương do hung khí": ["bị đâm", "bị bắn", "chém"],
    "Bỏng": ["bỏng", "cháy"],
    "Sốt cao": ["sốt cao", "xuất cao", "co giật", "co dật"]
}

class RuleService:
    def rule_based_urgency_classify(self, text: str) -> Dict[str, Any]:
        """
        Phân loại mức độ khẩn cấp bằng biểu thức chính quy (Regex) làm phương án dự phòng.
        """
        text_lower = text.lower()
        scores = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        
        for level, keywords in KEYWORDS_MAP.items():
            for kw in keywords:
                matches = len(re.findall(kw, text_lower))
                scores[level] += matches * (3 if level == "CRITICAL" else 2 if level == "HIGH" else 1)

        max_score = 0
        predicted_level = "LOW"
        for level, score in scores.items():
            if score > max_score:
                max_score = score
                predicted_level = level

        confidence = 70.0 + min(max_score * 5.0, 25.0) if max_score > 0 else 50.0
        return {"urgency": predicted_level, "confidence": confidence}

    def extract_symptoms(self, text: str) -> List[str]:
        """
        Trích xuất triệu chứng lâm sàng sơ bộ dựa trên từ khóa regex.
        """
        extracted = []
        text_lower = text.lower()
        for symptom, kws in SYMPTOMS_KEYWORDS.items():
            if any(kw in text_lower for kw in kws):
                extracted.append(symptom)
        return extracted

rule_service = RuleService()
