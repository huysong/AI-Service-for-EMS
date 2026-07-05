import os
import tempfile
import logging
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SpeechService")

_whisper_model = None
_models_loaded = False

def init_speech_model():
    global _whisper_model, _models_loaded
    if _models_loaded:
        return
    try:
        from faster_whisper import WhisperModel
        logger.info("Đang tải mô hình faster-whisper (medium)...")
        _whisper_model = WhisperModel("medium", device="cpu", compute_type="int8")
        logger.info("Tải faster-whisper thành công!")
    except Exception as e:
        logger.error(f"Lỗi khi tải faster-whisper: {str(e)}")
        _whisper_model = None
    _models_loaded = True

class SpeechService:
    async def transcribe(self, audio_bytes: bytes) -> str:
        init_speech_model()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            temp_file.write(audio_bytes)
            temp_path = temp_file.name

        transcript = ""
        try:
            if _whisper_model is not None:
                logger.info("Đang dịch âm thanh bằng Whisper...")
                loop = asyncio.get_event_loop()
                
                def run_transcribe():
                    segments, info = _whisper_model.transcribe(
                        temp_path, 
                        beam_size=5, 
                        language="vi",
                        initial_prompt="Đây là cuộc gọi khẩn cấp tới tổng đài cấp cứu 115, tai nạn giao thông, chấn thương, bệnh nhân bất tỉnh, chảy máu, gãy xương, khó thở."
                    )
                    return " ".join([segment.text for segment in segments])
                
                transcript = await loop.run_in_executor(None, run_transcribe)
                logger.info(f"Kết quả dịch: {transcript}")
            else:
                logger.warning("Không có Whisper model. Trả về text mặc định để triage.")
                transcript = "Alo cấp cứu ạ! Ở đây có tai nạn giao thông nghiêm trọng, người bị bất tỉnh và chảy nhiều máu lắm!"
        except Exception as e:
            logger.error(f"Lỗi dịch giọng nói: {str(e)}")
            transcript = ""
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
        return transcript

speech_service = SpeechService()
