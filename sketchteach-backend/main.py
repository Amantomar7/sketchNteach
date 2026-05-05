from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import requests, json, edge_tts, asyncio, os, re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_URL = "http://localhost:11434/api/generate"
AUDIO_PATH = "/tmp/explanation.mp3"

class Question(BaseModel):
    question: str

def ask_ollama(prompt: str) -> str:
    res = requests.post(OLLAMA_URL, json={
        "model": "deepseek-r1:7b",
        "prompt": prompt,
        "stream": False
    })
    raw = res.json()["response"]
    clean = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    return clean

def get_explanation(question: str) -> list[dict]:
    prompt = f"""
You are a CS/math teacher. Explain the following concept clearly in exactly 4 steps.
Return ONLY a valid JSON array, no extra text, no markdown, no backticks.
Format:
[
  {{"step": 1, "title": "short title", "explanation": "one sentence explanation"}},
  ...
]

Question: {question}
"""
    raw = ask_ollama(prompt)
    match = re.search(r'\[.*\]', raw, re.DOTALL)
    if match:
        return json.loads(match.group())
    return json.loads(raw)

def get_sketch_plan(steps: list[dict]) -> list[dict]:
    steps_text = "\n".join([f"Step {s['step']}: {s['title']} - {s['explanation']}" for s in steps])
    prompt = f"""
You are a whiteboard diagram planner. Given these explanation steps, return drawing instructions as JSON.
Return ONLY a valid JSON array, no extra text, no markdown, no backticks.
Each item must have:
- "step": step number
- "shapes": list of shape objects with "type" (rect/circle/arrow/text/line), "x", "y", "w" (width, optional), "h" (height, optional), "r" (radius, optional), "text" (optional), "from" (optional, [x,y] for arrow), "to" (optional, [x,y] for arrow)

Steps:
{steps_text}
"""
    raw = ask_ollama(prompt)
    match = re.search(r'\[.*\]', raw, re.DOTALL)
    if match:
        return json.loads(match.group())
    return json.loads(raw)

async def generate_audio(text: str):
    communicate = edge_tts.Communicate(text, voice="en-US-GuyNeural")
    await communicate.save(AUDIO_PATH)

@app.post("/explain")
async def explain(q: Question):
    steps = get_explanation(q.question)
    sketch = get_sketch_plan(steps)
    full_text = " ".join([f"Step {s['step']}. {s['title']}. {s['explanation']}" for s in steps])
    await generate_audio(full_text)
    return {
        "steps": steps,
        "sketch": sketch,
        "audio_url": "/audio"
    }

@app.get("/audio")
def get_audio():
    return FileResponse(AUDIO_PATH, media_type="audio/mpeg")

@app.get("/")
def root():
    return {"status": "SketchTeach backend running"}