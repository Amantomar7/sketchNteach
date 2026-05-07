# 🎓 SketchTeach — AI Whiteboard Tutor

> **Ask a question. Watch it get drawn. Hear it explained.**

SketchTeach is an AI-powered educational tool that takes any CS or math concept and teaches it through **synchronized Manim whiteboard animations + voice narration** — like having a professor draw on a board just for you, in real time.

Built for the **AMD Hackathon — Track 1: AI Agents & Agentic Workflows**, powered entirely on **AMD Instinct MI300X** GPUs via the AMD Developer Cloud.

---

## ✨ Demo

Type _"Explain how DFS traversal works"_ and SketchTeach will:

1. 🧠 **Understand** your question using **Qwen2.5:14b** on AMD MI300X
2. 📝 **Break it down** into 4 clear teaching steps
3. 🎬 **Write a Manim animation script** tailored to the concept (trees, arrays, flowcharts, client-server diagrams...)
4. 🖊️ **Render a whiteboard-style video** with smooth animations
5. 🎙️ **Generate voice narration** per step using edge-tts
6. 🔊 **Bake audio into the video** — perfectly synced, step by step
7. 🖥️ **Play everything** in a clean React UI with live step highlighting

---

## 🏗️ Architecture

```
User Question
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│                  FastAPI Backend (AMD GPU Node)          │
│                                                         │
│  ┌──────────────────┐      ┌───────────────────────┐    │
│  │  Explainer Agent │      │  Animator Agent        │    │
│  │  Qwen2.5:14b     │─────▶│  Qwen2.5:14b           │    │
│  │  → 4 step JSON   │      │  → Manim Python script │    │
│  └──────────────────┘      └──────────┬────────────┘    │
│                                       │                 │
│                        ┌──────────────▼─────────────┐   │
│                        │   Manim Renderer            │   │
│                        │   (MP4 with baked audio)    │   │
│                        └──────────────┬─────────────┘   │
│                                       │                 │
│  ┌────────────────────────────────────▼───────────────┐ │
│  │  Voice Agent — edge-tts (per-step MP3 files)       │ │
│  │  + ffprobe duration detection for sync             │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
              React Frontend (Local Machine)
         Video + Live Step Highlights + Scrub Sync
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **LLM** | Qwen2.5:14b via Ollama |
| **Animation** | Manim Community v0.20 |
| **Voice / TTS** | edge-tts (en-US-GuyNeural) |
| **Audio sync** | ffprobe duration detection |
| **Backend** | FastAPI + Python 3.12 + asyncio |
| **Frontend** | React 18 |
| **GPU** | AMD Instinct MI300X (ROCm) |
| **Inference** | AMD Developer Cloud |

---

## 🚀 Getting Started

### Prerequisites

- AMD Developer Cloud GPU node (MI300X) with ROCm
- Python 3.12+
- Node.js 18+
- FFmpeg + ffprobe

### 1. GPU Node Setup

```bash
# Clone the repo
git clone https://github.com/yourusername/sketchteach.git
cd sketchteach

# Install system dependencies
apt install -y python3.12-venv libcairo2-dev libpango1.0-dev ffmpeg

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install fastapi uvicorn requests edge-tts python-multipart manim

# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull the model (~9GB)
ollama pull qwen2.5:14b

# Start the backend
cd backend
uvicorn main:app --host 0.0.0.0 --port 8001
```

### 2. SSH Tunnel (connect local machine to GPU node)

Open a new terminal on your **local machine**:

```bash
ssh -L 3001:localhost:8001 root@YOUR_NODE_IP
```

Keep this window open — it's the tunnel.

### 3. Frontend Setup (Local Machine)

```bash
cd frontend/sketchteach-ui
npm install
npm start
```

Open [http://localhost:3000](http://localhost:3000) and start asking questions!

---

## 📁 Project Structure

```
sketchteach/
├── backend/
│   └── main.py                  # FastAPI — explanation, animation, TTS, sync
├── frontend/
│   └── sketchteach-ui/
│       └── src/
│           └── App.js           # React UI — video, step highlights, scrub sync
├── animations/
│   └── media/                   # Manim renders output here
└── README.md
```

---

## 🎯 AMD GPU Advantage

SketchTeach leverages the **AMD Instinct MI300X** in two key ways:

**Fast LLM Inference via ROCm**
Qwen2.5:14b runs on the MI300X's 192GB HBM3 memory via Ollama + ROCm. The model generates both a structured 4-step explanation AND a complete Manim Python animation script in seconds — tasks that would be impossibly slow on CPU.

**Parallel Pipeline**
The backend uses `asyncio.gather()` to run Manim rendering and TTS generation concurrently, fully utilizing the GPU node. Total time from question to playable video: **~30–60 seconds**.

---

## 🔮 Agentic Workflow — How It Works

SketchTeach uses a **3-agent pipeline** coordinated by FastAPI:

### Agent 1 — Explainer
```
Input:  Raw user question
Prompt: "Explain X in exactly 4 steps as structured JSON"
Output: [{step, title, explanation}, ...]
Model:  Qwen2.5:14b
```

### Agent 2 — Animator
```
Input:  4 steps + audio file paths + durations
Prompt: "Write a Manim script that teaches these 4 steps visually,
         using self.add_sound() to sync each step's audio"
Output: Complete Python Manim scene (concept-specific diagrams)
Model:  Qwen2.5:14b
```

### Agent 3 — Voice
```
Input:  Step explanations text (one per step)
Output: 4 MP3 files via edge-tts
Tool:   ffprobe measures duration of each MP3
        → durations sent to Manim prompt for wait() timing
        → durations sent to frontend for step highlight sync
```

**Error recovery:** If Manim renders a broken script, the backend automatically sends the error back to Qwen to self-fix. If that also fails, a guaranteed fallback script renders cleanly.

---

## 💡 Example Questions

| Question | What you'll see |
|---|---|
| `How does TCP work?` | Client/server boxes, SYN→ACK→DATA arrows |
| `Explain DFS traversal` | Animated tree, traversal path highlighted |
| `What is binary search?` | Array cells, MID pointer moving |
| `Explain recursion` | Call stack frames building up |
| `How does a hash table work?` | Key → hash function → bucket diagram |
| `What is thrashing in OS?` | RAM bar filling up, page fault counter |
| `Explain bubble sort` | Array elements swapping step by step |

---

## ✅ Hackathon Checklist

**Track 1: AI Agents & Agentic Workflows**

- ✅ Multi-agent coordination (explainer → animator → voice → sync)
- ✅ Open-source model (Qwen2.5:14b via Ollama)
- ✅ AMD Developer Cloud compute (MI300X)
- ✅ Moves beyond simple RAG — full agentic pipeline with error recovery
- ✅ Real-world useful application (AI tutor)
- ✅ Impressive live demo — video + voice + UI all in sync

---

## 🔧 Troubleshooting

**Port already in use**
```bash
# Use a different port
uvicorn main:app --host 0.0.0.0 --port 8002
# Update GPU_NODE in App.js and SSH tunnel accordingly
```

**Manim render fails**
```bash
# Check the generated script
cat ~/sketchteach/animations/SketchScene_*.py
# Backend auto-retries with LLM fix, then fallback script
```

**SSH tunnel drops**
```bash
# Reconnect tunnel
ssh -L 3001:localhost:8001 root@YOUR_NODE_IP
```

**Model slow to respond**
```bash
# Check GPU utilization
rocm-smi
# Should show GPU% > 0 during inference
```

---

## 🤝 Contributing

Ideas for future improvements:
- LaTeX math equation rendering via Manim's `MathTex`
- Follow-up questions in the same session (conversation memory)
- Higher resolution output (`-qh` flag for 1080p)
- Export lesson as PDF with screenshots from each step
- Support for diagrams beyond CS — physics, chemistry, economics

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

**Built with ❤️ on AMD Instinct MI300X**

`Manim` • `Qwen2.5:14b` • `FastAPI` • `React` • `ROCm` • `edge-tts`

</div>