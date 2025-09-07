from fastapi import FastAPI, Form, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from deep_translator import GoogleTranslator
from faster_whisper import WhisperModel
import uuid
import os
import subprocess
import re

app = FastAPI()

OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)


@app.get("/")
def home():
    return {"message": "Hello, FastAPI on Render 🚀"}


@app.get("/translate")
def translate(text: str, target: str = "vi"):
    translated = GoogleTranslator(source="auto", target=target).translate(text)
    return {"original": text, "translated": translated, "target_lang": target}


# =======================
# 1. Xử lý YouTube URL
# =======================
@app.post("/process")
def process(youtube_url: str = Form(...), target_lang: str = Form("vi")):
    req_id = str(uuid.uuid4())[:8]
    out_original = os.path.join(OUTPUT_DIR, f"subs_{req_id}_original.srt")
    out_translated = os.path.join(OUTPUT_DIR, f"subs_{req_id}_translated.srt")

    try:
        cmd = [
            "yt-dlp",
            "--write-auto-subs",
            "--sub-lang", "en",
            "--skip-download",
            "-o", f"{OUTPUT_DIR}/{req_id}.%(ext)s",
            youtube_url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            return JSONResponse(
                {"error": "Không lấy được phụ đề từ YouTube", "detail": result.stderr},
                status_code=400
            )

        downloaded_vtt = None
        for f in os.listdir(OUTPUT_DIR):
            if f.startswith(req_id) and f.endswith(".vtt"):
                downloaded_vtt = os.path.join(OUTPUT_DIR, f)
                break

        if not downloaded_vtt:
            return JSONResponse({"error": "Video không có phụ đề auto"}, status_code=400)

        # convert VTT -> SRT (bản gốc)
        subprocess.run(["ffmpeg", "-i", downloaded_vtt, out_original], check=True)

        # dịch nội dung -> bản dịch
        with open(out_original, "r", encoding="utf-8") as f:
            lines = f.readlines()

        with open(out_translated, "w", encoding="utf-8") as f:
            for line in lines:
                if "-->" in line or line.strip().isdigit() or line.strip() == "":
                    f.write(line)
                else:
                    try:
                        trans = GoogleTranslator(source="auto", target=target_lang).translate(line.strip())
                    except Exception:
                        trans = line.strip()
                    f.write(trans + "\n")

        return {
            "srt_original_url": f"/download/{os.path.basename(out_original)}",
            "srt_translated_url": f"/download/{os.path.basename(out_translated)}"
        }

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# =======================
# 2. Xử lý file upload (faster-whisper)
# =======================
@app.post("/upload")
def upload(file: UploadFile = File(...), target_lang: str = Form("vi")):
    req_id = str(uuid.uuid4())[:8]
    safe_name = safe_filename(file.filename)
    video_filename = f"{req_id}_{safe_name}"
    input_path = os.path.join(OUTPUT_DIR, video_filename)

    out_original = os.path.join(OUTPUT_DIR, f"subs_{req_id}_original.srt")
    out_translated = os.path.join(OUTPUT_DIR, f"subs_{req_id}_translated.srt")

    # Lưu file upload
    with open(input_path, "wb") as f:
        f.write(file.file.read())

    try:
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        segments, _ = model.transcribe(input_path)

        # Ghi phụ đề gốc
        with open(out_original, "w", encoding="utf-8") as f_o, \
             open(out_translated, "w", encoding="utf-8") as f_t:
            for i, seg in enumerate(segments, start=1):
                start, end, text = seg.start, seg.end, seg.text.strip()

                f_o.write(f"{i}\n")
                f_o.write(f"{format_time(start)} --> {format_time(end)}\n")
                f_o.write(text + "\n\n")

                trans_text = text
                if target_lang != "en":
                    try:
                        trans_text = GoogleTranslator(source="auto", target=target_lang).translate(text)
                    except Exception:
                        pass

                f_t.write(f"{i}\n")
                f_t.write(f"{format_time(start)} --> {format_time(end)}\n")
                f_t.write(trans_text + "\n\n")

        return {
            "video_url": f"/download/{os.path.basename(video_filename)}",
            "srt_original_url": f"/download/{os.path.basename(out_original)}",
            "srt_translated_url": f"/download/{os.path.basename(out_translated)}"
        }

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


def format_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def safe_filename(name: str) -> str:
    name = re.sub(r"[^\w\d-]", "_", name)
    return name


@app.get("/download/{filename}")
def download_file(filename: str):
    file_path = os.path.join(OUTPUT_DIR, filename)
    if os.path.exists(file_path):
        if filename.endswith(".srt"):
            media_type = "application/x-subrip"
        elif filename.endswith(".mp4"):
            media_type = "video/mp4"
        else:
            media_type = "application/octet-stream"
        return FileResponse(file_path, media_type=media_type, filename=filename)
    return JSONResponse(content={"error": "File not found"}, status_code=404)