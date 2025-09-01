from fastapi import FastAPI, Form
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

@app.post("/process")
def process(youtube_url: str = Form(...), target_lang: str = Form("vi")):
    """
    B1: tải subtitle auto từ YouTube bằng yt-dlp
    B2: dịch subtitle sang target_lang
    B3: lưu file .srt và trả link tải
    """
    req_id = str(uuid.uuid4())[:8]
    raw_srt = os.path.join(OUTPUT_DIR, f"raw_{req_id}.srt")
    out_srt = os.path.join(OUTPUT_DIR, f"subs_{req_id}.srt")

    try:
        # --- B1: tải subtitle (auto-gen nếu có) ---
        cmd = [
            "yt-dlp",
            "--write-auto-subs",
            "--sub-lang", "en",
            "--skip-download",
            "-o", f"{OUTPUT_DIR}/{req_id}.%(ext)s",
            youtube_url
        ]
        subprocess.run(cmd, check=True)

        # tìm file phụ đề tải về
        downloaded_srt = None
        for f in os.listdir(OUTPUT_DIR):
            if f.startswith(req_id) and f.endswith(".vtt"):
                downloaded_srt = os.path.join(OUTPUT_DIR, f)
                break

        if not downloaded_srt:
            return JSONResponse({"error": "Không tìm thấy phụ đề YouTube"}, status_code=400)

        # --- B2: convert VTT -> SRT ---
        raw_srt = downloaded_srt.replace(".vtt", ".srt")
        subprocess.run(["ffmpeg", "-i", downloaded_srt, raw_srt], check=True)

        # --- B3: dịch nội dung ---
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


@app.get("/download/{filename}")
def download_file(filename: str):
    file_path = os.path.join(OUTPUT_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="application/x-subrip", filename=filename)
    return JSONResponse(content={"error": "File not found"}, status_code=404)