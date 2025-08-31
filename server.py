from fastapi import FastAPI, Form
from fastapi.responses import FileResponse, JSONResponse
from deep_translator import GoogleTranslator
import uuid
import os

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

# === endpoint mới: tạo file SRT ===
@app.post("/process")
def process(youtube_url: str = Form(...), target_lang: str = Form("vi")):
    req_id = str(uuid.uuid4())[:8]
    srt_filename = f"subs_{req_id}.srt"
    srt_path = os.path.join(OUTPUT_DIR, srt_filename)

    # ⚡ Ở đây em gắn code tải subtitle từ youtube_url + dịch -> file SRT
    # Demo: ghi file SRT giả
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("1\n00:00:00,000 --> 00:00:02,000\nXin chào thế giới!\n")

    return {"srt_url": f"/download/{srt_filename}"}

@app.get("/download/{filename}")
def download_file(filename: str):
    file_path = os.path.join(OUTPUT_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="application/x-subrip", filename=filename)
    return JSONResponse(content={"error": "File not found"}, status_code=404)