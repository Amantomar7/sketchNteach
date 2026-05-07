import { useState, useRef, useEffect } from "react";
import axios from "axios";

const GPU_NODE = "https://134.199.197.193";

const COLORS = {
  bg: "#1a1a2e", panel: "#16213e", accent: "#e94560",
  white: "#eaeaea", gray: "#666",
};

export default function App() {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingMsg, setLoadingMsg] = useState("");
  const [steps, setSteps] = useState([]);
  const [videoUrl, setVideoUrl] = useState(null);
  const [activeStep, setActiveStep] = useState(-1);
  const [durations, setDurations] = useState(null);
  const videoRef = useRef(null);
  const timersRef = useRef([]);

  const LOADING_MSGS = [
    "🧠 Thinking about your question...",
    "✏️  Writing Manim animation script...",
    "🎬 Rendering whiteboard animation...",
    "🎙️  Generating voice explanation...",
  ];

  const handleAsk = async () => {
    if (!question.trim()) return;
    setLoading(true);
    setSteps([]);
    setVideoUrl(null);
    setActiveStep(-1);
    setDurations(null);
    timersRef.current.forEach(clearTimeout);
    timersRef.current = [];

    let mi = 0;
    setLoadingMsg(LOADING_MSGS[0]);
    const msgInterval = setInterval(() => {
      mi = (mi + 1) % LOADING_MSGS.length;
      setLoadingMsg(LOADING_MSGS[mi]);
    }, 4000);

    try {
      const res = await axios.post(
        `${GPU_NODE}/explain`,
        { question },
        { timeout: 180000 }
      );
      const { steps, video_url, durations } = res.data;
      setSteps(steps);
      setVideoUrl(`${GPU_NODE}${video_url}`);
      setDurations(durations);

      // Sync step highlights using real audio durations + animation time
      let elapsed = 0;
      steps.forEach((_, i) => {
        const id = setTimeout(() => setActiveStep(i), elapsed * 1000);
        timersRef.current.push(id);
        // audio duration + ~3.5s for manim animations + fadeout
        const stepDuration = durations && durations[i] ? durations[i] + 3.5 : 10;
        elapsed += stepDuration;
      });

    } catch (e) {
      alert("Error: " + (e.message || "Could not reach backend"));
    }

    clearInterval(msgInterval);
    setLoading(false);
  };

  // Auto-play video when ready (audio baked in)
  useEffect(() => {
    if (videoUrl && videoRef.current) {
      videoRef.current.load();
      videoRef.current.play().catch(() => {});
    }
  }, [videoUrl]);

  // Recalculate active step when user scrubs video
  const handleSeeked = () => {
    if (!videoRef.current || !durations || !steps.length) return;
    const t = videoRef.current.currentTime;
    let elapsed = 0;
    let currentStep = 0;
    for (let i = 0; i < steps.length; i++) {
      if (t >= elapsed) currentStep = i;
      elapsed += (durations[i] || 7) + 3.5;
    }
    setActiveStep(currentStep);
  };

  return (
    <div style={{
      minHeight: "100vh",
      background: COLORS.bg,
      color: COLORS.white,
      fontFamily: "'Segoe UI', sans-serif"
    }}>

      {/* Header */}
      <div style={{
        background: COLORS.panel,
        padding: "16px 36px",
        display: "flex",
        alignItems: "center",
        gap: 14,
        boxShadow: "0 2px 16px #0008"
      }}>
        <span style={{ fontSize: 26 }}>🎓</span>
        <span style={{ fontSize: 20, fontWeight: 800, color: COLORS.accent, letterSpacing: 1 }}>
          SketchTeach
        </span>
        <span style={{ fontSize: 12, color: COLORS.gray, marginLeft: 6 }}>
          AI Whiteboard Tutor • Powered by Manim + Qwen
        </span>
      </div>

      <div style={{ maxWidth: 1200, margin: "0 auto", padding: "28px 24px" }}>

        {/* Input bar */}
        <div style={{ display: "flex", gap: 10, marginBottom: 28 }}>
          <input
            value={question}
            onChange={e => setQuestion(e.target.value)}
            onKeyDown={e => e.key === "Enter" && !loading && handleAsk()}
            placeholder="Ask anything... e.g. How does DFS work? Explain recursion. What is TCP?"
            style={{
              flex: 1, padding: "13px 18px", borderRadius: 10,
              border: "1.5px solid #2a2a4a",
              background: COLORS.panel, color: COLORS.white,
              fontSize: 15, outline: "none",
            }}
          />
          <button
            onClick={handleAsk}
            disabled={loading}
            style={{
              padding: "13px 26px", borderRadius: 10, border: "none",
              background: loading ? "#333" : COLORS.accent,
              color: "#fff", fontWeight: 700, fontSize: 15,
              cursor: loading ? "not-allowed" : "pointer",
              transition: "background 0.2s",
            }}
          >
            {loading ? "..." : "✦ Ask"}
          </button>
        </div>

        {/* Loading state */}
        {loading && (
          <div style={{ textAlign: "center", marginTop: 80 }}>
            <div style={{ fontSize: 52, marginBottom: 20 }}>⚙️</div>
            <div style={{ fontSize: 18, color: COLORS.white, marginBottom: 10 }}>
              {loadingMsg}
            </div>
            <div style={{ fontSize: 13, color: COLORS.gray }}>
              This takes ~30–60 seconds. Manim is rendering your animation...
            </div>
            <div style={{ marginTop: 24, display: "flex", justifyContent: "center", gap: 8 }}>
              {[0, 1, 2].map(i => (
                <div key={i} style={{
                  width: 10, height: 10, borderRadius: "50%",
                  background: COLORS.accent,
                  animation: `bounce 1.2s ${i * 0.2}s infinite`,
                }} />
              ))}
            </div>
          </div>
        )}

        {/* Result */}
        {!loading && steps.length > 0 && (
          <div style={{ display: "grid", gridTemplateColumns: "380px 1fr", gap: 24 }}>

            {/* Steps panel */}
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div style={{
                fontSize: 13, color: COLORS.gray,
                marginBottom: 4, fontWeight: 600, letterSpacing: 1
              }}>
                EXPLANATION
              </div>
              {steps.map((s, i) => (
                <div key={i} style={{
                  background: i <= activeStep ? COLORS.panel : "#0f0f20",
                  border: `1.5px solid ${i === activeStep ? COLORS.accent : "#1e1e3a"}`,
                  borderRadius: 12, padding: "14px 18px",
                  opacity: i <= activeStep ? 1 : 0.4,
                  transform: i === activeStep ? "translateX(4px)" : "none",
                  transition: "all 0.5s ease",
                }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
                    <div style={{
                      background: i <= activeStep ? COLORS.accent : "#333",
                      borderRadius: "50%", width: 26, height: 26, flexShrink: 0,
                      display: "flex", alignItems: "center", justifyContent: "center",
                      fontSize: 12, fontWeight: 800, transition: "background 0.4s"
                    }}>
                      {s.step}
                    </div>
                    <span style={{
                      fontWeight: 700, fontSize: 14,
                      color: i <= activeStep ? COLORS.white : COLORS.gray
                    }}>
                      {s.title}
                    </span>
                  </div>
                  <p style={{
                    margin: 0, fontSize: 13, color: COLORS.gray,
                    lineHeight: 1.65, paddingLeft: 36
                  }}>
                    {s.explanation}
                  </p>
                </div>
              ))}
            </div>

            {/* Video panel */}
            <div>
              <div style={{
                fontSize: 13, color: COLORS.gray,
                marginBottom: 8, fontWeight: 600, letterSpacing: 1
              }}>
                ANIMATION
              </div>
              <div style={{
                background: "#FEFCF3", borderRadius: 14,
                overflow: "hidden", boxShadow: "0 4px 30px #0006",
                aspectRatio: "16/9",
              }}>
                {videoUrl ? (
                  <video
                    ref={videoRef}
                    controls
                    onSeeked={handleSeeked}
                    style={{ width: "100%", height: "100%", display: "block" }}
                  >
                    <source src={videoUrl} type="video/mp4" />
                  </video>
                ) : (
                  <div style={{
                    display: "flex", alignItems: "center",
                    justifyContent: "center", height: "100%", color: "#aaa"
                  }}>
                    Loading animation...
                  </div>
                )}
              </div>

              {/* Step progress indicators */}
              {steps.length > 0 && (
                <div style={{
                  display: "flex", gap: 8, marginTop: 12,
                  justifyContent: "center", flexWrap: "wrap"
                }}>
                  {steps.map((s, i) => (
                    <div key={i} style={{
                      display: "flex", alignItems: "center", gap: 6,
                      padding: "5px 14px", borderRadius: 20,
                      background: i === activeStep ? COLORS.accent : "#1e1e3a",
                      fontSize: 12,
                      color: i === activeStep ? "#fff" : COLORS.gray,
                      transition: "all 0.4s ease",
                      boxShadow: i === activeStep ? `0 0 12px ${COLORS.accent}66` : "none",
                    }}>
                      <span style={{ fontWeight: 800 }}>{i + 1}</span>
                      <span>{s.title}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

          </div>
        )}

        {/* Empty state */}
        {!loading && steps.length === 0 && (
          <div style={{ textAlign: "center", marginTop: 100, color: COLORS.gray }}>
            <div style={{ fontSize: 56, marginBottom: 18 }}>🖊️</div>
            <div style={{ fontSize: 20, marginBottom: 10, color: COLORS.white }}>
              Ask a question to start learning
            </div>
            <div style={{ fontSize: 14 }}>
              Manim will draw it. AI will explain it. Voice will speak it.
            </div>
          </div>
        )}

      </div>

      <style>{`
        @keyframes bounce {
          0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
          40% { transform: scale(1); opacity: 1; }
        }
        input::placeholder { color: #444; }
      `}</style>
    </div>
  );
}
