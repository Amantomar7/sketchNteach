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

    prompt = f"""You are an expert Manim animator. Write a Manim Community v0.20 Python script.

CLASS NAME MUST BE EXACTLY: {scene_name}

BACKGROUND: self.camera.background_color = "#FEFCF3"
ALL TEXT must be BLACK or DARK_BLUE. Never use WHITE.

═══════════════════════════════
SCREEN LAYOUT — STRICTLY FOLLOW
═══════════════════════════════

The visible screen goes from y = +3.5 (top) to y = -3.5 (bottom).
NEVER place anything below DOWN*2.8 or above UP*3.5.

EXACT ZONES per step:
  TOP    → header text     at to_edge(UP, buff=0.3)        [y ≈ +3.2]
  MIDDLE → explanation     at DOWN*0.3                      [y ≈ -0.3]  
  BOTTOM → diagram shapes  between DOWN*1.6 and DOWN*2.6   [y ≈ -1.6 to -2.6]

═══════════════════════════════
MANDATORY STRUCTURE EVERY STEP
═══════════════════════════════

# 1. HEADER
header = Text("Step N: Title", font_size=28, color=BLACK, weight=BOLD).to_edge(UP, buff=0.3)
self.play(Write(header))

# 2. EXPLANATION — split long text into 2 lines using \\n
# If explanation is longer than 60 chars, split it at a natural break
explanation = Text(
    "First part of explanation\\nSecond part if needed.",
    font_size=21, color=DARK_BLUE, line_spacing=1.5
).move_to(ORIGIN + UP*0.8).set_width(10)
self.play(Write(explanation, run_time=2))
self.wait(0.5)

# 3. DIAGRAM — ALL shapes between DOWN*1.6 and DOWN*2.6 ONLY
# Build shapes SEPARATELY, never reference variable inside its own VGroup
box1 = Rectangle(width=2, height=0.8).set_stroke(BLUE, width=2).shift(LEFT*3 + DOWN*2)
label1 = Text("Label", font_size=20, color=BLUE).move_to(box1)
self.play(Create(box1), Write(label1))

# 4. WAIT + CLEAR
self.wait(2)
self.play(*[FadeOut(obj) for obj in self.mobjects])

═══════════════════════════════
TEXT WRAPPING RULE — CRITICAL
═══════════════════════════════

If an explanation sentence is longer than 55 characters, you MUST split it with \\n.
Examples:
  BAD:  "Thrashing occurs in systems with limited physical memory where the system spends more time."
  GOOD: "Thrashing occurs when limited memory\\ncauses more swapping than actual execution."

  BAD:  "Symptoms include a high page fault rate, decreased CPU utilization, and reduced performance."
  GOOD: "Symptoms: high page fault rate,\\ndecreased CPU and system performance."

Always SHORTEN + SPLIT. Max 55 chars per line. Max 2 lines.

═══════════════════════════════
DIAGRAM GUIDE PER CONCEPT
═══════════════════════════════

NETWORK/TCP/HTTP:
  client = Rectangle(width=2, height=0.8).set_stroke(BLUE,width=2).shift(LEFT*3.5+DOWN*2)
  client_lbl = Text("Client",font_size=20,color=BLUE).move_to(client)
  server = Rectangle(width=2, height=0.8).set_stroke(RED,width=2).shift(RIGHT*3.5+DOWN*2)
  server_lbl = Text("Server",font_size=20,color=RED).move_to(server)
  arr = Arrow(client.get_right(),server.get_left(),color=GREEN,stroke_width=3)
  arr_lbl = Text("SYN",font_size=18,color=GREEN).next_to(arr,UP,buff=0.1)
  self.play(Create(client),Write(client_lbl),Create(server),Write(server_lbl))
  self.play(GrowArrow(arr),Write(arr_lbl))

MEMORY/OS CONCEPTS:
  ram = Rectangle(width=5, height=0.9).set_stroke(BLUE,width=2).shift(DOWN*1.8)
  ram_lbl = Text("Physical RAM",font_size=20,color=BLUE).move_to(ram)
  used = Rectangle(width=3, height=0.9).set_stroke(RED,width=2).align_to(ram,LEFT)
  used_lbl = Text("Used",font_size=18,color=RED).move_to(used)
  free = Rectangle(width=2, height=0.9).set_stroke(GREEN,width=2).next_to(used,RIGHT,buff=0)
  free_lbl = Text("Free",font_size=18,color=GREEN).move_to(free)
  self.play(Create(ram),Write(ram_lbl))
  self.play(Create(used),Write(used_lbl),Create(free),Write(free_lbl))

TREE/DFS/BFS:
  root = Circle(radius=0.35).set_stroke(DARK_BLUE,width=2).set_fill(BLUE,opacity=0.15).shift(UP*0.2+DOWN*1.6)
  root_lbl = Text("A",font_size=22,color=DARK_BLUE).move_to(root)
  left = Circle(radius=0.35).set_stroke(DARK_BLUE,width=2).set_fill(BLUE,opacity=0.15).shift(LEFT*1.8+DOWN*2.4)
  left_lbl = Text("B",font_size=22,color=DARK_BLUE).move_to(left)
  right = Circle(radius=0.35).set_stroke(DARK_BLUE,width=2).set_fill(BLUE,opacity=0.15).shift(RIGHT*1.8+DOWN*2.4)
  right_lbl = Text("C",font_size=22,color=DARK_BLUE).move_to(right)
  e1 = Line(root.get_bottom(),left.get_top(),color=GRAY)
  e2 = Line(root.get_bottom(),right.get_top(),color=GRAY)
  self.play(Create(root),Write(root_lbl))
  self.play(Create(e1),Create(e2))
  self.play(Create(left),Write(left_lbl),Create(right),Write(right_lbl))

ARRAY/SEARCH/SORT:
  values = [3,7,1,9,4,6]
  cells = VGroup(*[
      VGroup(Square(side_length=0.6).set_stroke(DARK_BLUE,width=2),
             Text(str(v),font_size=18,color=BLACK))
      .arrange(ORIGIN) for v in values
  ]).arrange(RIGHT,buff=0.05).shift(DOWN*2)
  self.play(Create(cells))
  mid = SurroundingRectangle(cells[len(values)//2],color=RED,buff=0.05)
  mid_lbl = Text("MID",font_size=16,color=RED).next_to(mid,UP,buff=0.1)
  self.play(Create(mid),Write(mid_lbl))

STACK/RECURSION:
  frames = ["func(3)","func(2)","func(1)","base case"]
  rects = []
  for i,f in enumerate(frames):
      r = Rectangle(width=3.5,height=0.55).set_stroke(BLUE,width=2).set_fill(BLUE,opacity=0.08)
      r.shift(DOWN*1.7 + UP*i*0.57)
      lbl = Text(f,font_size=18,color=DARK_BLUE).move_to(r)
      rects.append((r,lbl))
  for r,lbl in rects:
      self.play(Create(r),Write(lbl),run_time=0.4)

═══════════════════════════════
CRITICAL CODING RULES
═══════════════════════════════

1. NEVER place anything at DOWN*3 or beyond — it will be off screen.
2. NEVER reference a variable inside its own VGroup. Build shapes separately first.
3. NEVER use WHITE text.
4. ALWAYS split explanation text with \\n if over 55 chars per line.
5. ALWAYS clear with: self.play(*[FadeOut(obj) for obj in self.mobjects])
6. Diagram shapes ONLY between DOWN*1.5 and DOWN*2.6.

Now write the complete script for ALL 4 steps. 
Each step: header → explanation (split with \\n) → diagram (in safe zone) → fadeout.

Steps:
{steps_text}

Return ONLY Python code. No markdown. No backticks. Start with: from manim import *
"""

    raw = ask_ollama(prompt)
    raw = re.sub(r'^```python\s*', '', raw, flags=re.MULTILINE)
    raw = re.sub(r'^```\s*', '', raw, flags=re.MULTILINE)
    return raw.strip()
# ── Step 3: render Manim ──────────────────────────────────────────────────────
def validate_and_fix_script(script: str, scene_name: str) -> str:
    """Try to compile the script, return it if valid."""
    try:
        compile(script, "<string>", "exec")
        return script
    except SyntaxError as e:
        raise Exception(f"Syntax error in generated script: {e}")

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

    for root, dirs, files in os.walk(os.path.join(ANIM_DIR, "media")):
        for f in files:
            if f == f"{scene_name}.mp4":
                return os.path.join(root, f)

    raise Exception(f"RENDER_ERROR:{result.stderr[-2000:]}")

def fix_script_with_llm(script: str, error: str, scene_name: str) -> str:
    """Ask the model to fix its own broken script."""
    prompt = f"""The following Manim Python script has an error. Fix it and return ONLY the corrected Python code.
No markdown, no backticks, no explanation. Just the fixed code starting with: from manim import *

ERROR:
{error[:800]}

BROKEN SCRIPT:
{script}

COMMON FIXES:
- Never reference a variable inside the VGroup that defines it (memory_diagram[0] inside VGroup(...) that creates memory_diagram)
- Instead build shapes separately first, then group them:
  box1 = Rectangle(...)
  box2 = Rectangle(...).next_to(box1, RIGHT)
  group = VGroup(box1, box2)
- Make sure all Text colors are BLACK or DARK_BLUE (background is light cream #FEFCF3)
- Every object must be added to scene with self.play() or self.add()

Return only the fixed Python code:"""

    raw = ask_ollama(prompt)
    raw = re.sub(r'^```python\s*', '', raw, flags=re.MULTILINE)
    raw = re.sub(r'^```\s*', '', raw, flags=re.MULTILINE)
    return raw.strip()


def get_fallback_script(steps: list[dict], scene_name: str) -> str:
    step_blocks = []
    colors = ["BLUE", "GREEN", "ORANGE", "PURE_RED"]
    shapes = ["RoundedRectangle(width=7, height=1.5, corner_radius=0.2)",
              "RoundedRectangle(width=7, height=1.5, corner_radius=0.2)",
              "RoundedRectangle(width=7, height=1.5, corner_radius=0.2)",
              "RoundedRectangle(width=7, height=1.5, corner_radius=0.2)"]

    for i, s in enumerate(steps):
        color = colors[i % len(colors)]
        # Safely escape quotes in text
        title_safe = s['title'].replace('"', "'")
        explanation_safe = s['explanation'].replace('"', "'")[:80]
        step_blocks.append(f"""
        # ── Step {s['step']} ──
        header_{i} = Text("Step {s['step']}: {title_safe}", font_size=30, color=BLACK, weight=BOLD).to_edge(UP, buff=0.3)
        explanation_{i} = Text(
            "{explanation_safe}",
            font_size=21, color=DARK_BLUE, line_spacing=1.4
        ).next_to(header_{i}, DOWN, buff=0.4).set_width(11)
        shape_{i} = {shapes[i]}.set_stroke({color}, width=3).shift(DOWN*2.2)
        shape_label_{i} = Text("{title_safe}", font_size=24, color={color}, weight=BOLD).move_to(shape_{i})
        self.play(Write(header_{i}))
        self.play(Write(explanation_{i}, run_time=2.5))
        self.play(Create(shape_{i}), Write(shape_label_{i}))
        self.wait(2)
        self.play(*[FadeOut(obj) for obj in self.mobjects])
""")

    blocks_code = "\n".join(step_blocks)
    return f"""from manim import *
class {scene_name}(Scene):
    def construct(self):
        self.camera.background_color = "#FEFCF3"
{blocks_code}
"""

@app.post("/explain")
async def explain(q: Question):
    scene_name = "SketchScene_" + uuid.uuid4().hex[:8]

    # 1. Get explanation
    steps = get_explanation(q.question)

    # 2. Get Manim script
    script = get_manim_script(steps, scene_name)

    # 3. Try rendering with up to 2 auto-fix retries
    video_path = None
    last_error = ""
    for attempt in range(3):
        try:
            loop = asyncio.get_event_loop()
            video_path = await loop.run_in_executor(None, render_manim, script, scene_name)
            break  # success
        except Exception as e:
            last_error = str(e)
            if "RENDER_ERROR:" in last_error and attempt < 2:
                print(f"Attempt {attempt+1} failed, asking LLM to fix...")
                error_detail = last_error.replace("RENDER_ERROR:", "")
                # Use new scene name for retry
                scene_name = "SketchScene_" + uuid.uuid4().hex[:8]
                if attempt == 1:
                    # Second failure — use reliable fallback
                    script = get_fallback_script(steps, scene_name)
                else:
                    script = fix_script_with_llm(script, error_detail, scene_name)
            else:
                # Use fallback on final attempt
                scene_name = "SketchScene_" + uuid.uuid4().hex[:8]
                script = get_fallback_script(steps, scene_name)
                try:
                    video_path = await loop.run_in_executor(None, render_manim, script, scene_name)
                except:
                    raise Exception("All render attempts failed")
                break

    # 4. Generate audio in parallel with last render attempt
    await generate_audio(steps)

    latest_video_path["path"] = video_path

    return {
        "steps": steps,
        "video_url": f"/video/{scene_name}",
        "audio_url": "/audio"
    }
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