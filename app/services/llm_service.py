import os
import json
import logging
import httpx
from typing import Dict, Any
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LLMService")

class LLMService:
    def __init__(self):
        self.prompt_cache = None

    def _load_prompt(self) -> str:
        if self.prompt_cache:
            return self.prompt_cache
        
        path = settings.PROMPT_FILE_PATH
        # Try finding relative to project root or absolute
        if not os.path.exists(path):
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            path = os.path.join(base_dir, settings.PROMPT_FILE_PATH)
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.prompt_cache = f.read().strip()
                logger.info(f"Loaded system prompt from {path} successfully.")
                return self.prompt_cache
        except Exception as e:
            logger.error(f"Failed to read prompt file from {path}: {str(e)}")
            return (
                "Bạn là bác sĩ tổng đài điều phối cấp cứu 115 Việt Nam.\n"
                "Hãy đọc đoạn hội thoại của người dân và phân tích tình trạng cấp cứu.\n"
                "Chỉ trả về kết quả ở định dạng JSON duy nhất với cấu trúc sau:\n"
                "{\n"
                '  "urgency": "CRITICAL" hoặc "HIGH" hoặc "MEDIUM" hoặc "LOW",\n'
                '  "confidence": 90,\n'
                '  "symptoms": ["triệu chứng 1", "triệu chứng 2"]\n'
                "}"
            )

    async def analyze_transcript(self, transcript: str) -> Dict[str, Any]:
        """
        Sends the transcript to LM Studio and parses the JSON response.
        """
        if not transcript.strip():
            return {
                "urgency": "LOW",
                "confidence": 50.0,
                "symptoms": []
            }

        try:
            system_prompt = self._load_prompt()
            merged_content = f"{system_prompt}\n\nĐoạn hội thoại cuộc gọi cần phân tích:\n{transcript}"
            
            payload = {
                "model": settings.LMSTUDIO_MODEL,
                "messages": [
                    {"role": "user", "content": merged_content}
                ],
                "temperature": settings.LMSTUDIO_TEMPERATURE,
                "max_tokens": settings.LMSTUDIO_MAX_TOKENS
            }

            logger.info(f"Gửi yêu cầu phân tích sang LM Studio ({settings.LMSTUDIO_API_URL})...")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    settings.LMSTUDIO_API_URL,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=60.0
                )
                
                if response.status_code != 200:
                    raise Exception(f"LM Studio API trả về lỗi {response.status_code}: {response.text}")
                
                response_json = response.json()
                content_str = response_json["choices"][0]["message"]["content"].strip()
                
                try:
                    result_json = json.loads(content_str)
                except json.JSONDecodeError:
                    start_idx = content_str.find("{")
                    end_idx = content_str.rfind("}")
                    if start_idx != -1 and end_idx != -1:
                        result_json = json.loads(content_str[start_idx:end_idx+1])
                    else:
                        raise ValueError("Không tìm thấy cấu trúc JSON hợp lệ trong phản hồi.")

                urgency = result_json.get("urgency", "LOW")
                confidence = float(result_json.get("confidence", 90.0))
                symptoms = result_json.get("symptoms", [])

                return {
                    "urgency": urgency,
                    "confidence": confidence,
                    "symptoms": symptoms
                }

        except Exception as e:
            logger.error(f"Lỗi phân loại bằng LLM (LM Studio): {str(e)}")
            return {
                "urgency": "LOW",
                "confidence": 0.0,
                "symptoms": []
            }

llm_service = LLMService()
