from fastapi import FastAPI, UploadFile, File
from faster_whisper import WhisperModel
import uvicorn
import tempfile

app = FastAPI()

# ⚡ Load model nhỏ để không tốn RAM (tiny ~ 75MB)
model = WhisperModel("tiny", device="cpu", compute_type="int8")

@app.get("/")
def home():
    return {"message": "Hello, FastAPI on Render 🚀"}

@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    # lưu file tạm
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    # chạy whisper
    segments, _ = model.transcribe(tmp_path)

    text = " ".join([segment.text for segment in segments])
    return {"transcription": text}

# ⚡ Render sẽ chạy lệnh này trong Start Command:
# uvicorn server:app --host 0.0.0.0 --port 10000