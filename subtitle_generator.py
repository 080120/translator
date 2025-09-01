import sys
import whisper
from deep_translator import GoogleTranslator
import os
import json

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: python subtitle_generator.py <video_path> [lang]"}))
        return
    
    video_path = sys.argv[1]   
    lang = sys.argv[2] if len(sys.argv) > 2 else "vi"

    # Tải model Whisper
    model = whisper.load_model("small")
    result = model.transcribe(video_path, verbose=False)

    # Tạo file .srt cùng tên video
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    srt_filename = f"{base_name}_{lang}.srt"
    srt_path = os.path.join("subs", srt_filename)   # để gọn vào thư mục subs

    os.makedirs("subs", exist_ok=True)

    with open(srt_path, "w", encoding="utf-8") as f:
        for i, segment in enumerate(result["segments"], start=1):
            start = segment["start"]
            end = segment["end"]
            text = segment["text"]

            # Dịch từng đoạn
            translated = GoogleTranslator(source='auto', target=lang).translate(text)

            # Ghi theo chuẩn SRT (song ngữ: gốc + dịch)
            f.write(f"{i}\n")
            f.write(f"{format_time(start)} --> {format_time(end)}\n")
            f.write(text.strip() + "\n")         # Lời gốc
            f.write(translated.strip() + "\n\n") # Lời dịch

    # --- trả JSON để Unity nhận ---
    response = {
        "srt_url": f"/{srt_path}",   # ví dụ: /subs/shin_vi.srt
        "video_url": f"/videos/{os.path.basename(video_path)}"
    }
    print(json.dumps(response, ensure_ascii=False))

def format_time(seconds: float) -> str:
    """Chuyển giây thành định dạng SRT: hh:mm:ss,ms"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"

if __name__ == "__main__":
    main()