# generate_scenarios.py
import asyncio
import os
from edge_tts import Communicate

async def generate_audio():
    output_dir = "audio_test_scenarios"
    os.makedirs(output_dir, exist_ok=True)
    
    scenarios = {
        "critical_call.mp3": (
            "Cứu tôi với! Ở đường Lê Văn Lương đang có tai nạn giao thông rất nghiêm trọng. "
            "Một người đi xe máy ngã đập đầu xuống đường bất tỉnh, máu chảy ra rất nhiều ở đầu, "
            "xin hãy cho xe cứu thương tới ngay!"
        ),
        "high_call.mp3": (
            "Alo cấp cứu ạ! Bố tôi tự nhiên bị đau ngực dữ dội, ôm ngực khó thở vã mồ hôi hột, "
            "nghi bị nhồi máu cơ tim, gia đình rất hoảng loạn xin xe cấp cứu gấp!"
        ),
        "medium_call.mp3": (
            "Alo bác sĩ ơi, con tôi bị sốt cao ba mươi chín độ năm từ sáng và đang bị co giật nhẹ, "
            "gia đình cần xe cấp cứu hỗ trợ đưa cháu đi viện ngay ạ!"
        )
    }
    
    print("Starting audio generation using Microsoft Edge TTS (Neural Voices)...")
    for filename, text in scenarios.items():
        filepath = os.path.join(output_dir, filename)
        print(f"Generating {filename}...")
        try:
            # Sử dụng giọng đọc vi-VN-HoaiMyNeural
            communicate = Communicate(text, "vi-VN-HoaiMyNeural")
            await communicate.save(filepath)
            print(f"  -> Saved to: {os.path.abspath(filepath)}")
        except Exception as e:
            print(f"  -> Error generating {filename}: {str(e)}")
            
    print("\nGeneration complete! All files are in the 'audio_test_scenarios' folder.")

if __name__ == "__main__":
    asyncio.run(generate_audio())
