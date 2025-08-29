from fastapi import FastAPI
from deep_translator import GoogleTranslator

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Hello, FastAPI on Render 🚀"}

@app.get("/translate")
def translate(text: str, target: str = "vi"):
    translated = GoogleTranslator(source="auto", target=target).translate(text)
    return {"original": text, "translated": translated, "target_lang": target}