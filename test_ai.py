# test_ai.py
import asyncio
import os
import sys
from app.services.ai_service import ai_service

# Ép console Windows sử dụng UTF-8 để in tiếng Việt không bị lỗi charmap
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

async def test_real_audio_scenarios():
    audio_dir = "audio_test_scenarios"
    files = {
        "critical_call.mp3": "CRITICAL",
        "high_call.mp3": "HIGH",
        "medium_call.mp3": "MEDIUM"
    }

    print("\n--- Testing Generated Vietnamese Audio Scenarios (Whisper + Classifier) ---")
    
    for filename, expected_level in files.items():
        filepath = os.path.join(audio_dir, filename)
        if not os.path.exists(filepath):
            print(f"[WARNING] File not found: {filepath}")
            continue
            
        print(f"\nProcessing file: {filename} (Expected: {expected_level})")
        try:
            with open(filepath, "rb") as f:
                audio_bytes = f.read()

            result = await ai_service.analyze_voice_call(audio_bytes, call_id=999, request_id="TEST-REQ-123")
            
            print(f"=== RESULT FOR {filename} ===")
            print(f"Transcript: \"{result.transcript}\"")
            print(f"Urgency: {result.urgency} (Expected: {expected_level})")
            print(f"Confidence: {result.confidence}%")
            print(f"Symptoms: {result.symptoms}")
            
        except Exception as e:
            print(f"[ERROR] Failed to process {filename}: {str(e)}")

async def main():
    await test_real_audio_scenarios()

if __name__ == "__main__":
    asyncio.run(main())
