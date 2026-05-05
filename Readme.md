# 🎓 SketchNTeach — AI Whiteboard Tutor

> **Ask a question. Watch it get drawn. Hear it explained.**

SketchTeach is an AI-powered educational tool that takes any CS or math concept and explains it through synchronized **Manim whiteboard animations** + **voice narration** — like having a professor draw on a board just for you.

Built for the **AMD Hackathon — Track 1: AI Agents & Agentic Workflows**, running entirely on AMD Instinct MI300X GPUs via the AMD Developer Cloud.

---

![SketchNTeach Demo](docs/demo.gif)

---

## ✨ What It Does

You type: _"Explain how DFS traversal works"_

SketchNTeach:
1. 🧠 **Understands** your question using Qwen2.5:14b LLM
2. 📝 **Breaks it down** into 4 clear teaching steps
3. 🎬 **Generates a Manim animation script** tailored to the concept
4. 🖊️ **Renders a whiteboard-style video** — trees, arrays, flowcharts, client-server diagrams
5. 🎙️ **Speaks the explanation** in a natural teacher voice
6. 🖥️ **Plays everything in sync** in a clean React UI

---

## 🏗️ Architecture

```
User Question
      │
      ▼
┌─────────────────────────────────────────────────┐
│              FastAPI Backend (GPU Node)          │
│                                                 │
│  ┌─────────────┐      ┌──────────────────────┐  │
│  │ Explanation │      │   Manim Script Gen   │  │
│  │   Agent     │─────▶│       Agent          │  │
│  │ Qwen2.5:14b │      │   Qwen2.5:14b        │  │
│  └─────────────┘      └──────────┬───────────┘  │
│                                  │              │
│                    ┌─────────────▼────────────┐ │
│                    │   Manim Renderer         │ │
│                    │   (MP4 output)           │ │
│                    └─────────────┬────────────┘ │
│                                  │              │
│  ┌───────────────────────────────▼────────────┐ │
│  │         edge-tts Voice Generator           │ │
│  └────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
      │                    │
      ▼                    ▼
  Audio (MP3)          Animation (MP4)
      │                    │
      └────────┬───────────┘
               ▼
     React Frontend (Local)
     Steps + Video + Voice in sync
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **LLM** | Qwen2.5:14b via Ollama |
| **Animation** | Manim Community v0.20 |
| **Voice** | edge-tts (en-US-GuyNeural) |
| **Backend** | FastAPI + Python 3.12 |
| **Frontend** | React 18 |
| **GPU** | AMD Instinct MI300X (ROCm) |
| **Inference** | AMD Developer Cloud |

---

## 🚀 Getting Started

### Prerequisites

- AMD Developer Cloud GPU node (MI300X) with ROCm
- Python 3.11+
- Node.js 18+
- FFmpeg

### GPU Node Setup

```bash
# 1. Clone the repo
git clone https://github.com/Amantomar7/sketchNteach.git
cd sketchNteach

# 2. Install system dependencies
apt install -y python3.12-venv libcairo2-dev libpango1.0-dev ffmpeg

# 3. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 4. Install Python dependencies
pip install fastapi uvicorn requests edge-tts python-multipart manim

# 5. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 6. Pull the model
ollama pull qwen2.5:14b

# 7. Start the backend
cd backend
uvicorn main:app --host 0.0.0.0 --port 8001
```

### Frontend Setup (Local Machine)

```bash
# 1. Go to frontend folder
cd frontend/sketchteach-ui

# 2. Install dependencies
npm install

# 3. Set up SSH tunnel to GPU node
ssh -L 3001:localhost:8001 root@YOUR_NODE_IP

# 4. Start React app
npm start
```

Open [http://localhost:3000](http://localhost:3000) and start asking questions!

---

## 📁 Project Structure

```
sketchteach/
├── backend/
│   └── main.py              # FastAPI server — explanation, animation, TTS
├── frontend/
│   └── sketchteach-ui/
│       └── src/
│           └── App.js       # React UI — video player, step highlights
├── animations/
│   └── media/               # Manim renders output here
└── README.md
```

---

## 🎯 AMD GPU Advantage

SketchTeach leverages the **AMD Instinct MI300X** in two key ways:

- **Fast LLM inference** via Ollama + ROCm — Qwen2.5:14b generates explanation + full Manim Python scripts in seconds on the MI300X's massive 192GB HBM3 memory
- **Parallel rendering** — the backend runs Manim rendering and TTS generation concurrently using `asyncio`, fully utilizing the GPU node

Without GPU acceleration, generating + rendering a full animation would take minutes. On the MI300X it completes in **under 30 seconds**.

---

## 💡 Example Questions to Try

| Question | What you'll see |
|---|---|
| `How does TCP work?` | Client-server boxes, SYN/ACK packet arrows |
| `Explain DFS traversal` | Animated tree with traversal path highlighted |
| `What is binary search?` | Array cells with mid-pointer moving |
| `Explain recursion` | Call stack frames building up |
| `How does a hash table work?` | Key → hash function → bucket diagram |
| `What is bubble sort?` | Array elements swapping with comparison arrows |

---

## 🔮 How The Agentic Workflow Works

SketchNTeach uses a **3-agent pipeline**:

**Agent 1 — Explainer**
> Prompt: "Explain X in exactly 4 steps as structured JSON"
> Output: `[{step, title, explanation}, ...]`

**Agent 2 — Animator**
> Prompt: "Write a Manim script that visually teaches these 4 steps"
> Output: Full Python Manim scene with concept-specific diagrams

**Agent 3 — Voice**
> Input: Step explanations text
> Output: MP3 narration via edge-tts

All three run in a coordinated async pipeline — animation and voice generate in parallel after explanation is ready.

---

## 🏆 Hackathon Track

**Track 1: AI Agents & Agentic Workflows**

- ✅ Multi-agent coordination (explainer → animator → voice)
- ✅ Open-source model (Qwen2.5:14b via Ollama)
- ✅ AMD Developer Cloud compute
- ✅ Real-world useful application
- ✅ Impressive live demo

---

## 🤝 Contributing

Pull requests welcome! Ideas for improvement:

- Add more concept-specific Manim templates
- Support math equations via LaTeX rendering
- Add interactive quiz after each explanation
- Support follow-up questions in the same session

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">
  <strong>Built with ❤️ on AMD MI300X</strong><br/>
  <sub>Manim • Qwen2.5 • FastAPI • React • ROCm</sub>
</div>