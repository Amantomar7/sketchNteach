from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import requests, json, edge_tts, asyncio, os, re, subprocess, tempfile, uuid

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_URL  = "http://localhost:11434/api/generate"
AUDIO_PATH  = "/tmp/sketchteach_audio.mp3"
ANIM_DIR    = "/root/sketchteach/animations"
VENV_PYTHON = "/root/sketchteach/venv/bin/python"
VENV_MANIM  = "/root/sketchteach/venv/bin/manim"

class Question(BaseModel):
    question: str

# ── LLM helper ────────────────────────────────────────────────────────────────
def ask_ollama(prompt: str, model: str = "qwen2.5:14b") -> str:
    res = requests.post(OLLAMA_URL, json={
        "model": model, "prompt": prompt, "stream": False
    })
    raw = res.json()["response"]
    return re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()

# ── Step 1: get explanation ───────────────────────────────────────────────────
def get_explanation(question: str) -> list[dict]:
    prompt = f"""You are a CS/math teacher. Explain the concept in exactly 4 steps.
Return ONLY a valid JSON array. No markdown, no backticks.
[
  {{"step":1,"title":"short title","explanation":"one clear sentence"}},
  {{"step":2,"title":"short title","explanation":"one clear sentence"}},
  {{"step":3,"title":"short title","explanation":"one clear sentence"}},
  {{"step":4,"title":"short title","explanation":"one clear sentence"}}
]
Question: {question}"""
    raw = ask_ollama(prompt)
    match = re.search(r'\[.*\]', raw, re.DOTALL)
    txt = re.sub(r',\s*([}\]])', r'\1', match.group())
    return json.loads(txt)

# ── Step 2: get Manim script ──────────────────────────────────────────────────
def get_manim_script(steps: list[dict], scene_name: str) -> str:
    steps_text = "\n".join([
        f"Step {s['step']}: {s['title']} — {s['explanation']}"
        for s in steps
    ])

    prompt = f"""You are an expert Manim animator. Write a Manim Community v0.20 Python script that creates a rich, educational whiteboard animation explaining the following concept step by step.

CLASS NAME MUST BE: {scene_name}

CRITICAL RULES:
- Background: self.camera.background_color = "#FEFCF3"
- Every step MUST have a COMPLETELY DIFFERENT and UNIQUE diagram. Never reuse the same shapes.
- Each step must FadeOut ALL previous content before showing next step.
- Use rich, concept-specific visuals — not just circles and arrows.
- Labels and text must be BLACK or DARK_BLUE (background is light cream).
- Animate everything — use Create, Write, DrawBorderThenFill, GrowArrow, GrowFromCenter.
- Add labels to every shape so viewer knows what it represents.

CONCEPT-SPECIFIC DRAWING GUIDE (use the right one for each step):

FOR NETWORK/TCP/HTTP concepts:
  # Labeled boxes for client and server
  client = RoundedRectangle(width=2.5, height=1.2, corner_radius=0.2).set_stroke(BLUE, width=3).shift(LEFT*4)
  client_label = Text("Client", color=BLUE, font_size=28).move_to(client)
  server = RoundedRectangle(width=2.5, height=1.2, corner_radius=0.2).set_stroke(RED, width=3).shift(RIGHT*4)
  server_label = Text("Server", color=RED, font_size=28).move_to(server)
  # Animated packet arrow with label
  packet = Arrow(start=client.get_right(), end=server.get_left(), color=GREEN, stroke_width=4)
  packet_label = Text("SYN", font_size=22, color=GREEN).next_to(packet, UP)
  self.play(DrawBorderThenFill(client), Write(client_label))
  self.play(DrawBorderThenFill(server), Write(server_label))
  self.play(GrowArrow(packet), Write(packet_label))

FOR TREE/GRAPH/DFS/BFS concepts:
  # Draw actual tree with nodes and edges
  root = Circle(radius=0.4).set_stroke(DARK_BLUE, width=3).set_fill(BLUE, opacity=0.2).shift(UP*2)
  root_label = Text("A", color=DARK_BLUE, font_size=28).move_to(root)
  left = Circle(radius=0.4).set_stroke(DARK_BLUE, width=3).set_fill(BLUE, opacity=0.2).shift(LEFT*2)
  left_label = Text("B", color=DARK_BLUE, font_size=28).move_to(left)
  right = Circle(radius=0.4).set_stroke(DARK_BLUE, width=3).set_fill(BLUE, opacity=0.2).shift(RIGHT*2)
  right_label = Text("C", color=DARK_BLUE, font_size=28).move_to(right)
  edge1 = Line(root.get_bottom(), left.get_top(), color=GRAY)
  edge2 = Line(root.get_bottom(), right.get_top(), color=GRAY)
  # Highlight traversal path
  highlight = Circle(radius=0.4).set_fill(YELLOW, opacity=0.5).move_to(root)

FOR ARRAY/SEARCH/SORT concepts:
  # Draw array cells with index labels
  values = [3, 1, 4, 1, 5, 9, 2, 6]
  cells = VGroup(*[
      VGroup(
          Square(side_length=0.7).set_stroke(DARK_BLUE, width=2),
          Text(str(v), font_size=22, color=BLACK)
      ).arrange(ORIGIN)
      for v in values
  ]).arrange(RIGHT, buff=0.05).shift(UP)
  indices = VGroup(*[
      Text(str(i), font_size=16, color=GRAY).next_to(cells[i], DOWN, buff=0.1)
      for i in range(len(values))
  ])
  # Highlight pointer
  pointer = Triangle().scale(0.2).set_fill(RED, opacity=1).rotate(PI).next_to(cells[3], UP)

FOR STACK/RECURSION concepts:
  # Draw stack frames building up
  frames = ["main()", "func(4)", "func(3)", "func(2)", "func(1)"]
  rects = VGroup(*[
      VGroup(
          RoundedRectangle(width=3, height=0.6, corner_radius=0.1).set_stroke(BLUE, width=2).set_fill(BLUE, opacity=0.1),
          Text(f, font_size=20, color=DARK_BLUE)
      ).arrange(ORIGIN)
      for f in frames
  ]).arrange(UP, buff=0.05).shift(DOWN)

FOR PROCESS/FLOW concepts:
  # Draw flowchart with decision diamonds
  box1 = RoundedRectangle(width=3, height=0.9, corner_radius=0.2).set_stroke(BLUE, width=2).shift(UP*2)
  label1 = Text("Start", font_size=24, color=BLUE).move_to(box1)
  diamond = Square(side_length=1.2).rotate(PI/4).set_stroke(ORANGE, width=2).shift(UP*0.3)
  d_label = Text("Check?", font_size=18, color=ORANGE).move_to(diamond)
  yes_arrow = Arrow(start=diamond.get_right(), end=diamond.get_right()+RIGHT*1.5, color=GREEN)
  yes_label = Text("Yes", font_size=18, color=GREEN).next_to(yes_arrow, UP)

ANIMATION SEQUENCE PER STEP:
1. Show step number + title at top (small, e.g. font_size=28)
2. Animate the main diagram piece by piece (not all at once)
3. Highlight the KEY element of this step (change color, add glow, move pointer)
4. self.wait(2)
5. FadeOut ALL objects before next step

Now write the complete script for these steps. Make each step visually distinct and rich:
{steps_text}

Return ONLY valid Python code. No markdown fences. No explanation. Start directly with: from manim import *
"""

    raw = ask_ollama(prompt)
    raw = re.sub(r'^```python\s*', '', raw, flags=re.MULTILINE)
    raw = re.sub(r'^```\s*', '', raw, flags=re.MULTILINE)
    return raw.strip()

# ── Step 3: render Manim ──────────────────────────────────────────────────────
def render_manim(script: str, scene_name: str) -> str:
    script_path = os.path.join(ANIM_DIR, f"{scene_name}.py")
    with open(script_path, "w") as f:
        f.write(script)

    result = subprocess.run(
        [VENV_MANIM, "-ql", "--disable_caching", script_path, scene_name],
        capture_output=True, text=True, cwd=ANIM_DIR
    )

    # Find rendered MP4
    mp4_pattern = os.path.join(ANIM_DIR, "media", "videos", scene_name, "480p15", f"{scene_name}.mp4")
    if os.path.exists(mp4_pattern):
        return mp4_pattern

    # Fallback search
    for root, dirs, files in os.walk(os.path.join(ANIM_DIR, "media")):
        for f in files:
            if f == f"{scene_name}.mp4":
                return os.path.join(root, f)

    raise Exception(f"Manim render failed:\n{result.stderr[-1000:]}")

# ── Step 4: generate audio ────────────────────────────────────────────────────
async def generate_audio(steps: list[dict]) -> str:
    text = " ".join([
        f"Step {s['step']}. {s['title']}. {s['explanation']}"
        for s in steps
    ])
    communicate = edge_tts.Communicate(text, voice="en-US-GuyNeural")
    await communicate.save(AUDIO_PATH)
    return AUDIO_PATH

# ── API ───────────────────────────────────────────────────────────────────────
latest_video_path = {}

@app.post("/explain")
async def explain(q: Question):
    scene_name = "SketchScene_" + uuid.uuid4().hex[:8]

    # 1. Get explanation
    steps = get_explanation(q.question)

    # 2. Get Manim script from LLM
    script = get_manim_script(steps, scene_name)

    # 3. Render animation + generate audio in parallel
    loop = asyncio.get_event_loop()
    video_path, _ = await asyncio.gather(
        loop.run_in_executor(None, render_manim, script, scene_name),
        generate_audio(steps)
    )

    latest_video_path["path"] = video_path
    token = scene_name

    return {
        "steps": steps,
        "video_url": f"/video/{token}",
        "audio_url": "/audio"
    }

@app.get("/video/{token}")
def get_video(token: str):
    path = latest_video_path.get("path")
    if not path or not os.path.exists(path):
        return {"error": "Video not found"}
    return FileResponse(path, media_type="video/mp4")

@app.get("/audio")
def get_audio():
    return FileResponse(AUDIO_PATH, media_type="audio/mpeg")

@app.get("/")
def root():
    return {"status": "SketchTeach backend running"}