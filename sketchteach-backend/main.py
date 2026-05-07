from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import requests, json, edge_tts, asyncio, os, re, subprocess, uuid

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_URL  = "http://localhost:11434/api/generate"
AUDIO_DIR   = "/tmp/sketchteach_audio"
ANIM_DIR    = "/root/sketchteach/animations"
VENV_MANIM  = "/root/sketchteach/venv/bin/manim"

os.makedirs(AUDIO_DIR, exist_ok=True)

class Question(BaseModel):
    question: str

# ── LLM ───────────────────────────────────────────────────────────────────────
def ask_ollama(prompt: str, model: str = "qwen2.5:14b") -> str:
    res = requests.post(OLLAMA_URL, json={
        "model": model, "prompt": prompt, "stream": False
    })
    raw = res.json()["response"]
    return re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()

# ── Step 1: explanation ────────────────────────────────────────────────────────
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

# ── Step 2: generate one MP3 per step ─────────────────────────────────────────
async def generate_step_audios(steps: list[dict], session_id: str) -> list[str]:
    paths = []
    for s in steps:
        text = f"Step {s['step']}. {s['title']}. {s['explanation']}"
        path = os.path.join(AUDIO_DIR, f"{session_id}_step{s['step']}.mp3")
        communicate = edge_tts.Communicate(text, voice="en-US-GuyNeural")
        await communicate.save(path)
        paths.append(path)
    return paths

# ── Step 3: get audio duration in seconds ─────────────────────────────────────
def get_audio_duration(path: str) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True
    )
    try:
        return float(result.stdout.strip())
    except:
        return 5.0  # fallback

# ── Step 4: Manim script with embedded audio ───────────────────────────────────
def get_manim_script(steps: list[dict], scene_name: str, audio_paths: list[str]) -> str:
    durations = [get_audio_duration(p) for p in audio_paths]

    prompt = f"""You are an expert Manim animator. Write a Manim Community v0.20 Python script.

CLASS NAME MUST BE EXACTLY: {scene_name}

AUDIO FILES (one per step):
audio_path_1 = "{audio_paths[0]}"
audio_path_2 = "{audio_paths[1]}"
audio_path_3 = "{audio_paths[2]}"
audio_path_4 = "{audio_paths[3]}"

AUDIO DURATIONS:
duration_1 = {durations[0]:.2f}
duration_2 = {durations[1]:.2f}
duration_3 = {durations[2]:.2f}
duration_4 = {durations[3]:.2f}

BACKGROUND: self.camera.background_color = "#FEFCF3"
ALL TEXT must be BLACK or DARK_BLUE. Never WHITE. Never redefine BLACK or DARK_BLUE.

═══════════════════════════════
SCREEN LAYOUT — STRICTLY FOLLOW
═══════════════════════════════

Visible screen: y = +3.5 (top) to y = -3.5 (bottom).
NEVER place anything below DOWN*2.6.

ZONES:
  HEADER      → to_edge(UP, buff=0.3)
  EXPLANATION → move_to(UP*0.9).set_width(10)
  DIAGRAM     → between DOWN*1.5 and DOWN*2.5

═══════════════════════════════
FONT SIZE RULES
═══════════════════════════════

Header:         font_size=24
Explanation:    font_size=19
Diagram labels: font_size=17
Arrow labels:   font_size=15

═══════════════════════════════
TEXT WRAPPING RULE
═══════════════════════════════

Max 50 chars per line. Always split with \\n.
Shorten the explanation to a punchy 2-line version.

Step 1 title:       "{steps[0]['title']}"
Step 1 explanation: "{steps[0]['explanation']}"

Step 2 title:       "{steps[1]['title']}"
Step 2 explanation: "{steps[1]['explanation']}"

Step 3 title:       "{steps[2]['title']}"
Step 3 explanation: "{steps[2]['explanation']}"

Step 4 title:       "{steps[3]['title']}"
Step 4 explanation: "{steps[3]['explanation']}"

═══════════════════════════════
MANDATORY STRUCTURE — NO LOOPS
═══════════════════════════════

DO NOT USE for loops or if/else blocks over steps.
Write each of the 4 steps as a completely separate, explicit block of code.
Each step must have a UNIQUE diagram — never repeat the same shapes.

Follow this exact template for each step:

        # ── STEP 1 ──────────────────────────────
        self.add_sound("{audio_paths[0]}")
        h1 = Text("Step 1: {steps[0]['title']}", font_size=24, color=BLACK, weight=BOLD).to_edge(UP, buff=0.3)
        e1 = Text(
            "short punchy version\\nof step 1 explanation",
            font_size=19, color=DARK_BLUE, line_spacing=1.5
        ).move_to(UP*0.9).set_width(10)
        self.play(Write(h1), run_time=0.8)
        self.play(Write(e1, run_time=1.8))
        # UNIQUE diagram for step 1 here (see diagram guide below)
        self.wait(max(1, {durations[0]:.2f} - 3))
        self.play(*[FadeOut(obj) for obj in self.mobjects])

        # ── STEP 2 ──────────────────────────────
        self.add_sound("{audio_paths[1]}")
        h2 = Text("Step 2: {steps[1]['title']}", font_size=24, color=BLACK, weight=BOLD).to_edge(UP, buff=0.3)
        e2 = Text(
            "short punchy version\\nof step 2 explanation",
            font_size=19, color=DARK_BLUE, line_spacing=1.5
        ).move_to(UP*0.9).set_width(10)
        self.play(Write(h2), run_time=0.8)
        self.play(Write(e2, run_time=1.8))
        # UNIQUE diagram for step 2 here
        self.wait(max(1, {durations[1]:.2f} - 3))
        self.play(*[FadeOut(obj) for obj in self.mobjects])

        # ── STEP 3 ──────────────────────────────
        self.add_sound("{audio_paths[2]}")
        h3 = Text("Step 3: {steps[2]['title']}", font_size=24, color=BLACK, weight=BOLD).to_edge(UP, buff=0.3)
        e3 = Text(
            "short punchy version\\nof step 3 explanation",
            font_size=19, color=DARK_BLUE, line_spacing=1.5
        ).move_to(UP*0.9).set_width(10)
        self.play(Write(h3), run_time=0.8)
        self.play(Write(e3, run_time=1.8))
        # UNIQUE diagram for step 3 here
        self.wait(max(1, {durations[2]:.2f} - 3))
        self.play(*[FadeOut(obj) for obj in self.mobjects])

        # ── STEP 4 ──────────────────────────────
        self.add_sound("{audio_paths[3]}")
        h4 = Text("Step 4: {steps[3]['title']}", font_size=24, color=BLACK, weight=BOLD).to_edge(UP, buff=0.3)
        e4 = Text(
            "short punchy version\\nof step 4 explanation",
            font_size=19, color=DARK_BLUE, line_spacing=1.5
        ).move_to(UP*0.9).set_width(10)
        self.play(Write(h4), run_time=0.8)
        self.play(Write(e4, run_time=1.8))
        # UNIQUE diagram for step 4 here
        self.wait(max(1, {durations[3]:.2f} - 3))
        self.play(*[FadeOut(obj) for obj in self.mobjects])

═══════════════════════════════
DIAGRAM GUIDE — PICK BEST FIT
═══════════════════════════════

NETWORK/TCP/HTTP:
  client = Rectangle(width=2,height=0.8).set_stroke(BLUE,width=2).shift(LEFT*3.5+DOWN*2)
  client_lbl = Text("Client",font_size=17,color=BLUE).move_to(client)
  server = Rectangle(width=2,height=0.8).set_stroke(RED,width=2).shift(RIGHT*3.5+DOWN*2)
  server_lbl = Text("Server",font_size=17,color=RED).move_to(server)
  arr = Arrow(client.get_right(),server.get_left(),color=GREEN,stroke_width=3)
  arr_lbl = Text("SYN",font_size=15,color=GREEN).next_to(arr,UP,buff=0.1)
  self.play(Create(client),Write(client_lbl),Create(server),Write(server_lbl))
  self.play(GrowArrow(arr),Write(arr_lbl))

MEMORY/OS:
  ram = Rectangle(width=5,height=0.8).set_stroke(BLUE,width=2).shift(DOWN*1.9)
  ram_lbl = Text("Physical RAM",font_size=17,color=BLUE).move_to(ram)
  used = Rectangle(width=3.5,height=0.8).set_stroke(RED,width=2).align_to(ram,LEFT).shift(DOWN*1.9)
  used_lbl = Text("Used",font_size=15,color=RED).move_to(used)
  free = Rectangle(width=1.5,height=0.8).set_stroke(GREEN,width=2).next_to(used,RIGHT,buff=0)
  free_lbl = Text("Free",font_size=15,color=GREEN).move_to(free)
  self.play(Create(ram),Write(ram_lbl))
  self.play(Create(used),Write(used_lbl),Create(free),Write(free_lbl))

TREE/DFS/BFS:
  root_c = Circle(radius=0.35).set_stroke(DARK_BLUE,width=2).set_fill(BLUE,opacity=0.15).shift(DOWN*1.6)
  root_lbl = Text("A",font_size=17,color=DARK_BLUE).move_to(root_c)
  left_c = Circle(radius=0.35).set_stroke(DARK_BLUE,width=2).set_fill(BLUE,opacity=0.15).shift(LEFT*1.8+DOWN*2.4)
  left_lbl = Text("B",font_size=17,color=DARK_BLUE).move_to(left_c)
  right_c = Circle(radius=0.35).set_stroke(DARK_BLUE,width=2).set_fill(BLUE,opacity=0.15).shift(RIGHT*1.8+DOWN*2.4)
  right_lbl = Text("C",font_size=17,color=DARK_BLUE).move_to(right_c)
  e1 = Line(root_c.get_bottom(),left_c.get_top(),color=GRAY)
  e2 = Line(root_c.get_bottom(),right_c.get_top(),color=GRAY)
  self.play(Create(root_c),Write(root_lbl))
  self.play(Create(e1),Create(e2))
  self.play(Create(left_c),Write(left_lbl),Create(right_c),Write(right_lbl))

ARRAY/SEARCH/SORT:
  vals = [3,7,1,9,4,6]
  cells = VGroup(*[
      VGroup(Square(side_length=0.6).set_stroke(DARK_BLUE,width=2),
             Text(str(v),font_size=16,color=BLACK)).arrange(ORIGIN)
      for v in vals
  ]).arrange(RIGHT,buff=0.05).shift(DOWN*2)
  self.play(Create(cells))
  mid = SurroundingRectangle(cells[len(vals)//2],color=RED,buff=0.05)
  mid_lbl = Text("MID",font_size=14,color=RED).next_to(mid,UP,buff=0.1)
  self.play(Create(mid),Write(mid_lbl))

STACK/RECURSION:
  for i,f in enumerate(["func(3)","func(2)","func(1)","base"]):
      r = Rectangle(width=3.5,height=0.5).set_stroke(BLUE,width=2).set_fill(BLUE,opacity=0.08)
      r.shift(DOWN*2.4+UP*i*0.52)
      lbl = Text(f,font_size=16,color=DARK_BLUE).move_to(r)
      self.play(Create(r),Write(lbl),run_time=0.35)

PROCESS/FLOW:
  prev_box = None
  for i,(b,c) in enumerate(zip(["Start","Process","Check","End"],[BLUE,GREEN,ORANGE,RED])):
      box = RoundedRectangle(width=2.2,height=0.6,corner_radius=0.1).set_stroke(c,width=2).shift(LEFT*4.5+RIGHT*i*3+DOWN*2)
      lbl = Text(b,font_size=16,color=c).move_to(box)
      self.play(Create(box),Write(lbl),run_time=0.4)
      if prev_box:
          self.play(GrowArrow(Arrow(prev_box.get_right(),box.get_left(),color=GRAY,stroke_width=2)),run_time=0.3)
      prev_box = box

COMPARISON (two options side by side):
  box_a = Rectangle(width=2.5,height=1.2).set_stroke(RED,width=2).shift(LEFT*3+DOWN*2)
  lbl_a = Text("Option A",font_size=17,color=RED).move_to(box_a)
  box_b = Rectangle(width=2.5,height=1.2).set_stroke(GREEN,width=2).shift(RIGHT*3+DOWN*2)
  lbl_b = Text("Option B",font_size=17,color=GREEN).move_to(box_b)
  vs = Text("VS",font_size=22,color=BLACK).move_to(DOWN*2)
  self.play(Create(box_a),Write(lbl_a),Create(box_b),Write(lbl_b),Write(vs))

TIMELINE/SEQUENCE:
  points = ["Phase 1","Phase 2","Phase 3","Phase 4"]
  line = Line(LEFT*5+DOWN*2,RIGHT*5+DOWN*2,color=DARK_BLUE,stroke_width=2)
  self.play(Create(line))
  for i,p in enumerate(points):
      dot = Dot(point=LEFT*4.5+RIGHT*i*3+DOWN*2,color=BLUE,radius=0.12)
      lbl = Text(p,font_size=15,color=DARK_BLUE).next_to(dot,UP,buff=0.15)
      self.play(GrowFromCenter(dot),Write(lbl),run_time=0.5)

═══════════════════════════════
CRITICAL RULES
═══════════════════════════════

1. NO for loops over steps — 4 explicit separate blocks only.
2. NOTHING below DOWN*2.6 — shapes will be invisible off screen.
3. NEVER redefine BLACK or DARK_BLUE — already in Manim.
4. NEVER reference a variable inside its own VGroup definition.
5. font_size: header=24, explanation=19, diagram=17, arrows=15.
6. Each step MUST have a completely UNIQUE diagram.
7. Explanation text: max 2 lines, max 50 chars per line, shortened.
8. ALWAYS end each step with: self.play(*[FadeOut(obj) for obj in self.mobjects])

Steps to teach:
Step 1: {steps[0]['title']} — {steps[0]['explanation']}
Step 2: {steps[1]['title']} — {steps[1]['explanation']}
Step 3: {steps[2]['title']} — {steps[2]['explanation']}
Step 4: {steps[3]['title']} — {steps[3]['explanation']}

Return ONLY Python. No markdown. No backticks. Start with: from manim import *
"""

    raw = ask_ollama(prompt)
    raw = re.sub(r'^```python\s*', '', raw, flags=re.MULTILINE)
    raw = re.sub(r'^```\s*', '', raw, flags=re.MULTILINE)
    return raw.strip()

# ── Step 5: render Manim ───────────────────────────────────────────────────────
def render_manim(script: str, scene_name: str) -> str:
    script_path = os.path.join(ANIM_DIR, f"{scene_name}.py")
    with open(script_path, "w") as f:
        f.write(script)

    result = subprocess.run(
        [VENV_MANIM, "-ql", "--disable_caching", script_path, scene_name],
        capture_output=True, text=True, cwd=ANIM_DIR
    )

    mp4_pattern = os.path.join(ANIM_DIR, "media", "videos", scene_name, "480p15", f"{scene_name}.mp4")
    if os.path.exists(mp4_pattern):
        return mp4_pattern

    for root, dirs, files in os.walk(os.path.join(ANIM_DIR, "media")):
        for f in files:
            if f == f"{scene_name}.mp4":
                return os.path.join(root, f)

    raise Exception(f"RENDER_ERROR:{result.stderr[-2000:]}")

def fix_script_with_llm(script: str, error: str, scene_name: str) -> str:
    prompt = f"""Fix this Manim script. Return ONLY corrected Python. No markdown, no backticks.

ERROR: {error[:600]}

COMMON FIXES:
- Never reference variable inside its own VGroup definition
- Build shapes separately: box = Rect(); lbl = Text().move_to(box); group = VGroup(box,lbl)
- Nothing below DOWN*2.6
- Use BLACK or DARK_BLUE text only
- self.add_sound(path) takes a file path string

SCRIPT:
{script}

Return fixed Python starting with: from manim import *"""
    raw = ask_ollama(prompt)
    raw = re.sub(r'^```python\s*', '', raw, flags=re.MULTILINE)
    raw = re.sub(r'^```\s*', '', raw, flags=re.MULTILINE)
    return raw.strip()

def get_fallback_script(steps: list[dict], scene_name: str, audio_paths: list[str], durations: list[float]) -> str:
    colors = ["BLUE", "GREEN", "ORANGE", "PURE_RED"]
    blocks = []
    for i, s in enumerate(steps):
        c = colors[i % len(colors)]
        title_safe = s['title'].replace('"', "'")
        explanation_safe = s['explanation'].replace('"', "'")
        # Split explanation at midpoint for two lines
        words = explanation_safe.split()
        mid = len(words) // 2
        line1 = " ".join(words[:mid])
        line2 = " ".join(words[mid:])
        dur = durations[i] if i < len(durations) else 5.0
        wait_time = max(1.0, dur - 3.0)
        audio_path = audio_paths[i] if i < len(audio_paths) else ""
        blocks.append(f"""
        # Step {s['step']}
        self.add_sound("{audio_path}")
        header_{i} = Text("Step {s['step']}: {title_safe}", font_size=28, color=BLACK, weight=BOLD).to_edge(UP, buff=0.3)
        explanation_{i} = Text("{line1}\\n{line2}", font_size=21, color=DARK_BLUE, line_spacing=1.5).move_to(UP*0.9).set_width(10)
        box_{i} = RoundedRectangle(width=6, height=1.0, corner_radius=0.2).set_stroke({c}, width=3).shift(DOWN*2)
        box_lbl_{i} = Text("{title_safe}", font_size=22, color={c}, weight=BOLD).move_to(box_{i})
        self.play(Write(header_{i}), run_time=0.8)
        self.play(Write(explanation_{i}, run_time=1.8))
        self.play(Create(box_{i}), Write(box_lbl_{i}))
        self.wait({wait_time:.1f})
        self.play(*[FadeOut(obj) for obj in self.mobjects])
""")

    return f"""from manim import *
class {scene_name}(Scene):
    def construct(self):
        self.camera.background_color = "#FEFCF3"
{"".join(blocks)}
"""

# ── API ────────────────────────────────────────────────────────────────────────
latest_video_path = {}

@app.post("/explain")
async def explain(q: Question):
    session_id = uuid.uuid4().hex[:8]
    scene_name = "SketchScene_" + session_id

    # 1. Get explanation
    steps = get_explanation(q.question)

    # 2. Generate per-step audio files
    audio_paths = await generate_step_audios(steps, session_id)
    durations = [get_audio_duration(p) for p in audio_paths]

    # 3. Get Manim script with audio paths embedded
    script = get_manim_script(steps, scene_name, audio_paths)

    # 4. Render with retry logic
    video_path = None
    for attempt in range(3):
        try:
            loop = asyncio.get_event_loop()
            video_path = await loop.run_in_executor(None, render_manim, script, scene_name)
            break
        except Exception as e:
            last_error = str(e)
            scene_name = "SketchScene_" + uuid.uuid4().hex[:8]
            if attempt == 0 and "RENDER_ERROR:" in last_error:
                print(f"Attempt {attempt+1} failed, asking LLM to fix...")
                script = fix_script_with_llm(script, last_error.replace("RENDER_ERROR:", ""), scene_name)
            else:
                print(f"Using fallback script...")
                script = get_fallback_script(steps, scene_name, audio_paths, durations)
            if attempt == 2:
                loop = asyncio.get_event_loop()
                video_path = await loop.run_in_executor(None, render_manim, script, scene_name)

    latest_video_path["path"] = video_path

    return {
        "steps": steps,
        "video_url": f"/video/{scene_name}",
    }

@app.get("/video/{token}")
def get_video(token: str):
    path = latest_video_path.get("path")
    if not path or not os.path.exists(path):
        return {"error": "Video not found"}
    return FileResponse(path, media_type="video/mp4")

@app.get("/")
def root():
    return {"status": "SketchTeach backend running"}