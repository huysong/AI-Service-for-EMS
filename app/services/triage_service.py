import time
import logging
from typing import Optional, List
from app.schemas.ai_analysis import AIAnalysisResult
from app.core.config import settings
from app.services.speech_service import speech_service
from app.services.llm_service import llm_service
from app.services.rule_service import rule_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TriageService")

class TriageService:
    async def analyze_voice_call(
        self, 
        audio_bytes: bytes, 
        call_id: Optional[int] = None, 
        request_id: Optional[str] = None
    ) -> AIAnalysisResult:
        """
        Orchestrates speech-to-text, LLM classification, fallback checks,
        and logs performance metrics.
        """
        total_start = time.perf_counter()

        logger.info(f"Bắt đầu phân tích cuộc gọi. RequestId: {request_id}, EmergencyCallId: {call_id}")

        # 1. Chạy dịch âm thanh sang chữ\
        asr_start = time.perf_counter()
        transcript = await speech_service.transcribe(audio_bytes)
        asr_seconds = time.perf_counter() - asr_start
        
        # 2. Phân tích luật từ khóa Regex (luôn chạy để làm dự phòng/so sánh)
        rule_start = time.perf_counter()
        rule_res = rule_service.rule_based_urgency_classify(transcript)
        rule_urgency = rule_res["urgency"]
        rule_confidence = rule_res["confidence"]
        rule_symptoms = rule_service.extract_symptoms(transcript)
        rule_seconds = time.perf_counter() - rule_start

        # 3. Phân tích bằng LLM
        llm_start = time.perf_counter()
        llm_res = await llm_service.analyze_transcript(transcript)
        llm_seconds = time.perf_counter() - llm_start
        llm_urgency = llm_res["urgency"]
        llm_confidence = llm_res["confidence"]
        llm_symptoms = llm_res["symptoms"]

        # Thứ tự các mức độ khẩn cấp để so sánh
        decision_start = time.perf_counter()
        urgency_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}

        # 4. Kiểm tra ngưỡng tin cậy (Confidence Threshold)
        # Nếu độ tin cậy của mô hình dưới CONFIDENCE_THRESHOLD (60%), chuyển sang dùng luật
        if llm_confidence < settings.CONFIDENCE_THRESHOLD:
            logger.info(
                f"Độ tự tin của mô hình ({llm_confidence}%) thấp hơn ngưỡng {settings.CONFIDENCE_THRESHOLD}%. "
                f"Chuyển sang sử dụng kết quả từ bộ luật từ khóa (Rule-based Fallback)."
            )
            final_urgency = rule_urgency
            final_confidence = rule_confidence
            final_symptoms = rule_symptoms
        else:
            # Nếu LLM có độ tự tin cao, áp dụng Max Triage (chọn mức khẩn cấp lớn nhất để đảm bảo an toàn)
            llm_val = urgency_order.get(llm_urgency.upper(), 0)
            rule_val = urgency_order.get(rule_urgency.upper(), 0)

            if rule_val > llm_val:
                final_urgency = rule_urgency
                final_confidence = rule_confidence
                # Kết hợp triệu chứng từ cả hai nguồn
                final_symptoms = list(set(llm_symptoms + rule_symptoms))
                logger.info(
                    f"-> Áp dụng luật cứu nạn khẩn cấp (Max Triage): Nâng từ {llm_urgency} lên {final_urgency} "
                    f"({final_confidence}%)"
                )
            else:
                final_urgency = llm_urgency
                final_confidence = llm_confidence
                final_symptoms = llm_symptoms
                logger.info(f"-> Sử dụng phân loại của mô hình LLM: {final_urgency} ({final_confidence}%)")

        # Đảm bảo triệu chứng không bị trống
        if not final_symptoms:
            final_symptoms = ["Chưa rõ triệu chứng"]

        decision_seconds = time.perf_counter() - decision_start
        
        # Log hiệu năng chi tiết
        total_seconds = time.perf_counter() - total_start

        logger.info(
            "[Triage Performance] "
            "EmergencyCallId=%s, "
            "RequestId=%s, "
            "ASR=%.2fs, "
            "Rule=%.4fs, "
            "LLM=%.2fs, "
            "Decision=%.4fs, "
            "Total=%.2fs",
            call_id,
            request_id,
            asr_seconds,
            rule_seconds,
            llm_seconds,
            decision_seconds,
            total_seconds
        )
        return AIAnalysisResult(
            transcript=transcript,
            urgency=final_urgency,
            confidence=final_confidence,
            symptoms=final_symptoms
        )

triage_service = TriageService()
