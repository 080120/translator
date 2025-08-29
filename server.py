from fastapi import FastAPI, Form
from fastapi.responses import FileResponse
from faster_whisper import WhisperModel
from deep_translator import GoogleTranslator
import subprocess, uuid, os, json

app = FastAPI()
model = WhisperModel("small", device="cpu")   # model nhỏ cho nhanh

WORK_DIR = "outputs"
os.makedirs(WORK_DIR, exist_ok=True)

def download_youtube_audio(url, out_path):
    cmd = f'yt-dlp -f bestaudio --extract-audio --audio-format mp3 -o "{out_path}" "{url}"'
    subprocess.run(cmd, shell=True, check=True)

@app.post("/process")
def process(youtube_url: str = Form(...), target_lang: str = Form("vi")):
    job_id = str(uuid.uuid4())
    out_audio = f"{WORK_DIR}/{job_id}.mp3"
    out_srt = f"{WORK_DIR}/{job_id}_{target_lang}.srt"

    # tải audio
    download_youtube_audio(youtube_url, out_audio)

    # nhận dạng
    segments, info = model.transcribe(out_audio)

    # dịch + ghi srt
    gt = GoogleTranslator(source="auto", target=target_lang)
    with open(out_srt, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments, 1):
            start = seg.start; end = seg.end
            f.write(f"{i}\n")
            f.write(f"{sec_to_time(start)} --> {sec_to_time(end)}\n")
            original = seg.text.strip()
            trans = gt.translate(original)
            f.write(f"{original}\n{trans}\n\n")

    return {"srt_url": f"/download/{job_id}_{target_lang}.srt"}

@app.get("/download/{filename}")
def download(filename: str):
    return FileResponse(f"{WORK_DIR}/{filename}")

def sec_to_time(sec):
    h = int(sec // 3600); m = int((sec % 3600) // 60)
    s = int(sec % 60); ms = int((sec - int(sec))*1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"