from fastapi import FastAPI, Form, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from deep_translator import GoogleTranslator
import uuid
import os
import subprocess

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
    out_srt = os.path.join(OUTPUT_DIR, f"subs_{req_id}.srt")

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

        # tìm file phụ đề tải về
        downloaded_vtt = None
        for f in os.listdir(OUTPUT_DIR):
            if f.startswith(req_id) and f.endswith(".vtt"):
                downloaded_vtt = os.path.join(OUTPUT_DIR, f)
                break

        if not downloaded_vtt:
            return JSONResponse({"error": "Video không có phụ đề auto"}, status_code=400)

        # convert VTT -> SRT
        raw_srt = downloaded_vtt.replace(".vtt", ".srt")
        subprocess.run(["ffmpeg", "-i", downloaded_vtt, raw_srt], check=True)

        # dịch nội dung
        with open(raw_srt, "r", encoding="utf-8") as f:
            lines = f.readlines()

        with open(out_srt, "w", encoding="utf-8") as f:
            for line in lines:
                if "-->" in line or line.strip().isdigit() or line.strip() == "":
                    f.write(line)
                else:
                    try:
                        trans = GoogleTranslator(source="auto", target=target_lang).translate(line.strip())
                    except Exception:
                        trans = line.strip()
                    f.write(trans + "\n")

        return {"srt_url": f"/download/{os.path.basename(out_srt)}"}

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# =======================
# 2. Xử lý file upload
# =======================
@app.post("/upload")
def upload(file: UploadFile = File(...), target_lang: str = Form("vi")):
    req_id = str(uuid.uuid4())[:8]
    input_path = os.path.join(OUTPUT_DIR, f"{req_id}_{file.filename}")
    out_srt = os.path.join(OUTPUT_DIR, f"subs_{req_id}.srt")

    # Lưu file upload
    with open(input_path, "wb") as f:
        f.write(file.file.read())

    try:
        # dùng autosub để tạo subtitle từ audio/video
        # cài autosub trước: pip install autosub
        cmd = ["autosub", input_path, "-o", out_srt, "-S", "en", "-D", target_lang]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            return JSONResponse(
                {"error": "Không tạo được phụ đề từ video", "detail": result.stderr},
                status_code=400
            )

        return {"srt_url": f"/download/{os.path.basename(out_srt)}"}

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/download/{filename}")
def download_file(filename: str):
    file_path = os.path.join(OUTPUT_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="application/x-subrip", filename=filename)
    return JSONResponse(content={"error": "File not found"}, status_code=404)