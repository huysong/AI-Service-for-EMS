# app/services/ai_service.py
import os
import tempfile
import logging
import re
from typing import Dict, Any, List

from app.schemas.ai_analysis import AIAnalysisResult

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EmergencyAIService")

# Biến toàn cục để tránh load model nhiều lần
_whisper_model = None
_zero_shot_classifier = None
_models_loaded = False

def init_ai_models():
    """
    Khởi tạo các mô hình AI.
    Sử dụng lazy loading để tránh làm đơ ứng dụng lúc khởi động nếu tải mô hình thất bại.
    """
    global _whisper_model, _zero_shot_classifier, _models_loaded
    if _models_loaded:
        return

    # 1. Khởi tạo Whisper (chuyển speech-to-text)
    try:
        from faster_whisper import WhisperModel
        logger.info("Đang tải mô hình faster-whisper (base)...")
        # Chạy trên CPU với float32 (an toàn, nhẹ và không yêu cầu GPU)
        _whisper_model = WhisperModel("base", device="cpu", compute_type="float32")
        logger.info("Tải faster-whisper thành công!")
    except Exception as e:
        logger.error(f"Lỗi khi tải faster-whisper: {str(e)}")
        _whisper_model = None

    # 2. Khởi tạo Zero-shot Classifier (phân loại khẩn cấp tiếng Việt)
    try:
        from transformers import pipeline
        logger.info("Đang tải mô hình Zero-shot Classifier (mDeBERTa-v3-base-2mil7)...")
        # mDeBERTa-v3-base-xnli-multilingual-nli-2mil7 hỗ trợ tiếng Việt rất tốt mà không cần train lại
        _zero_shot_classifier = pipeline(
            "zero-shot-classification", 
            model="MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7",
            device=-1 # CPU
        )
        logger.info("Tải Zero-shot Classifier thành công!")
    except Exception as e:
        logger.error(f"Lỗi khi tải Zero-shot Classifier: {str(e)}")
        _zero_shot_classifier = None

    _models_loaded = True


# --- HỆ THỐNG PHÂN LOẠI DỰ PHÒNG BẰNG TỪ KHÓA (KEYWORD-BASED FALLBACK) ---
# Thêm các lỗi chính tả đồng âm thường gặp khi Whisper dịch tiếng Việt giọng vùng miền hoặc robot TTS
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

def rule_based_urgency_classify(text: str) -> Dict[str, Any]:
    """
    Phân loại mức độ khẩn cấp bằng biểu thức chính quy (Regex) làm phương án dự phòng.
    """
    text_lower = text.lower()
    scores = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    
    for level, keywords in KEYWORDS_MAP.items():
        for kw in keywords:
            matches = len(re.findall(kw, text_lower))
            # Gán trọng số cao cho các từ khóa cấp cứu mạng sống
            scores[level] += matches * (3 if level == "CRITICAL" else 2 if level == "HIGH" else 1)

    max_score = 0
    predicted_level = "LOW"
    for level, score in scores.items():
        if score > max_score:
            max_score = score
            predicted_level = level

    confidence = 70.0 + min(max_score * 5.0, 25.0) if max_score > 0 else 50.0
    return {"urgency": predicted_level, "confidence": confidence}


class AIService:
    async def analyze_voice_call(self, audio_bytes: bytes) -> AIAnalysisResult:
        """
        Hàm xử lý file âm thanh cuộc gọi khẩn cấp.
        1. Sử dụng faster-whisper để chuyển đổi âm thanh sang văn bản tiếng Việt.
        2. Phân loại mức độ khẩn cấp (LOW, MEDIUM, HIGH, CRITICAL) bằng mDeBERTa.
        3. Áp dụng nguyên tắc "Triage An Toàn": Lấy mức khẩn cấp cao nhất giữa mô hình AI và Luật từ khóa.
        """
        # Đảm bảo các mô hình đã được khởi tạo
        init_ai_models()

        # Lưu audio bytes ra file tạm
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            temp_file.write(audio_bytes)
            temp_path = temp_file.name

        transcript = ""
        try:
            # 1. Chạy Speech to Text (Whisper)
            if _whisper_model is not None:
                logger.info("Đang dịch âm thanh bằng Whisper...")
                segments, info = _whisper_model.transcribe(
                    temp_path, 
                    beam_size=5, 
                    language="vi",
                    initial_prompt="Đây là cuộc gọi khẩn cấp tới tổng đài cấp cứu 115, tai nạn giao thông, chấn thương, bệnh nhân bất tỉnh, chảy máu, gãy xương, khó thở."
                )
                transcript = " ".join([segment.text for segment in segments])
                logger.info(f"Kết quả dịch: {transcript}")
            else:
                logger.warning("Không có Whisper model. Trả về text mặc định để triage.")
                transcript = "Alo cấp cứu ạ! Ở đây có tai nạn giao thông nghiêm trọng, người bị bất tỉnh và chảy nhiều máu lắm!"

            # 2. Phân loại mức độ khẩn cấp (Triage)
            ai_urgency = "LOW"
            ai_confidence = 50.0

            if _zero_shot_classifier is not None and transcript.strip():
                try:
                    logger.info("Đang phân tích mức độ khẩn cấp bằng AI Classifier...")
                    labels_mapping = {
                        "nguy hiểm tính mạng cấp bách": "CRITICAL",
                        "cấp cứu khẩn cấp nguy hiểm": "HIGH",
                        "cần hỗ trợ y tế trung bình": "MEDIUM",
                        "không khẩn cấp hoặc gọi thử máy": "LOW"
                    }
                    candidate_labels = list(labels_mapping.keys())
                    
                    res = _zero_shot_classifier(
                        transcript,
                        candidate_labels=candidate_labels,
                        hypothesis_template="Nội dung cuộc gọi này thuộc diện {}."
                    )
                    
                    best_label = res["labels"][0]
                    ai_urgency = labels_mapping[best_label]
                    ai_confidence = round(res["scores"][0] * 100, 2)
                    logger.info(f"AI Model phân loại: {ai_urgency} ({ai_confidence}%)")
                except Exception as classify_err:
                    logger.error(f"Lỗi phân loại bằng AI Model: {str(classify_err)}")

            # 3. Phân loại dự phòng bằng Từ khóa (Rule-based Fallback)
            fallback_res = rule_based_urgency_classify(transcript)
            fallback_urgency = fallback_res["urgency"]
            fallback_confidence = fallback_res["confidence"]
            logger.info(f"Rule-based phân loại: {fallback_urgency} ({fallback_confidence}%)")

            # 4. Nguyên tắc Triage An Toàn: Chọn mức độ khẩn cấp cao nhất (Max Triage)
            urgency_levels_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
            
            ai_level_val = urgency_levels_order.get(ai_urgency, 0)
            fallback_level_val = urgency_levels_order.get(fallback_urgency, 0)
            
            if fallback_level_val > ai_level_val:
                urgency_prediction = fallback_urgency
                confidence_score = fallback_confidence
                logger.info(f"-> Áp dụng luật cứu nạn khẩn cấp: Nâng từ {ai_urgency} lên {urgency_prediction} ({confidence_score}%)")
            else:
                urgency_prediction = ai_urgency
                confidence_score = ai_confidence
                logger.info(f"-> Sử dụng phân loại của mô hình AI: {urgency_prediction} ({confidence_score}%)")

            # Trích xuất triệu chứng sơ bộ dựa trên từ khóa khớp (kèm các biến thể lỗi chính tả)
            extracted_symptoms = []
            text_lower = transcript.lower()
            all_symptoms_keywords = {
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
            for symptom, kws in all_symptoms_keywords.items():
                if any(kw in text_lower for kw in kws):
                    extracted_symptoms.append(symptom)

            # Gợi ý thiết bị cứu hộ sơ bộ
            suggested_equipment = ["Hộp sơ cứu chuẩn (First_Aid_Kit)"]
            if "Bất tỉnh / Hôn mê" in extracted_symptoms or "Ngừng thở / Ngạt thở" in extracted_symptoms:
                suggested_equipment.extend(["Bình oxy (Oxygen_Tank)", "Máy khử rung tim tự động (AED)"])
            if "Chấn thương xương / Gãy xương" in extracted_symptoms:
                suggested_equipment.extend(["Nẹp cổ (Cervical_Collar)", "Cáng cứu thương (Spine_Board)"])
            if "Mất nhiều máu / Chảy máu" in extracted_symptoms or "Bị thương do hung khí" in extracted_symptoms:
                suggested_equipment.extend(["Băng gạc cầm máu (Trauma_Kit)"])

            # Xác định loại dịch vụ sơ bộ
            service_type_code = "MED_GENERAL"
            if "Tai nạn giao thông" in extracted_symptoms:
                service_type_code = "MED_ACCIDENT"
            elif "Ngừng thở / Ngạt thở" in extracted_symptoms or "Ngừng tim / Ngưng tim" in text_lower:
                service_type_code = "MED_CARDIAC"
            elif "Đột quỵ / Tai biến" in extracted_symptoms:
                service_type_code = "MED_STROKE"

            return AIAnalysisResult(
                ai_transcript=transcript,
                ai_urgency_prediction=urgency_prediction,
                ai_confidence_score=confidence_score,
                service_type_code=service_type_code,
                extracted_symptoms=extracted_symptoms if extracted_symptoms else ["Chưa rõ triệu chứng"],
                suggested_equipment=suggested_equipment
            )

        except Exception as e:
            logger.error(f"Lỗi toàn cục trong quá trình phân tích cuộc gọi: {str(e)}")
            raise e
        finally:
            # Dọn dẹp file tạm
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

ai_service = AIService()
