import { useState, useRef, useEffect } from "react";
import axios from "axios";

// const GPU_NODE = "http://134.199.197.193:8001"; // 👈 replace with your node IP
const GPU_NODE = "http://localhost:3001";

const COLORS = {
  bg: "#1a1a2e",
  panel: "#16213e",
  accent: "#e94560",
  white: "#eaeaea",
  gray: "#888",
  green: "#0f9b8e",
};

// function WhiteBoard({ sketchSteps, activeStep }) {
//   const canvasRef = useRef(null);
//   const animRef = useRef(null);

//   useEffect(() => {
//     if (!sketchSteps || sketchSteps.length === 0) return;
//     const canvas = canvasRef.current;
//     const ctx = canvas.getContext("2d");
//     ctx.clearRect(0, 0, canvas.width, canvas.height);

//     // Draw all steps up to activeStep
//     const stepsToDraw = sketchSteps.slice(0, activeStep + 1);

//     stepsToDraw.forEach((stepData, si) => {
//       const shapes = stepData.shapes || [];
//       const offsetY = si * 160;

//       shapes.forEach((shape) => {
//         ctx.save();
//         ctx.strokeStyle = "#2d2d2d";
//         ctx.fillStyle = "#2d2d2d";
//         ctx.lineWidth = 2;
//         ctx.font = "13px 'Segoe UI', sans-serif";

//         if (shape.type === "rect") {
//           // Whiteboard pencil style
//           ctx.strokeStyle = "#1a1a1a";
//           ctx.lineWidth = 2;
//           ctx.setLineDash([]);
//           ctx.beginPath();
//           ctx.roundRect(shape.x + 20, shape.y + offsetY, shape.w || 260, shape.h || 50, 6);
//           ctx.stroke();

//           if (shape.text) {
//             ctx.fillStyle = "#111";
//             ctx.font = "bold 12px 'Segoe UI'";
//             ctx.fillText(shape.text.slice(0, 38), shape.x + 28, shape.y + offsetY + 22);
//           }
//         }

//         if (shape.type === "circle") {
//           ctx.beginPath();
//           ctx.arc(shape.x + 20, shape.y + offsetY, shape.r || 25, 0, Math.PI * 2);
//           ctx.stroke();
//           if (shape.text) {
//             ctx.fillStyle = "#111";
//             ctx.fillText(shape.text.slice(0, 10), shape.x + 8, shape.y + offsetY + 5);
//           }
//         }

//         if (shape.type === "arrow") {
//           const from = shape.from || [shape.x, shape.y];
//           const to = shape.to || [shape.x + 80, shape.y];
//           ctx.beginPath();
//           ctx.moveTo(from[0] + 20, from[1] + offsetY);
//           ctx.lineTo(to[0] + 20, to[1] + offsetY);
//           ctx.stroke();
//           // arrowhead
//           ctx.beginPath();
//           ctx.moveTo(to[0] + 20, to[1] + offsetY);
//           ctx.lineTo(to[0] + 10, to[1] - 6 + offsetY);
//           ctx.lineTo(to[0] + 10, to[1] + 6 + offsetY);
//           ctx.fill();
//         }

//         if (shape.type === "text") {
//           ctx.fillStyle = "#222";
//           ctx.font = "12px 'Segoe UI'";
//           const words = (shape.text || "").split(" ");
//           let line = "", lineY = shape.y + offsetY;
//           words.forEach((word) => {
//             const test = line + word + " ";
//             if (ctx.measureText(test).width > 260 && line) {
//               ctx.fillText(line, shape.x + 20, lineY);
//               line = word + " ";
//               lineY += 16;
//             } else line = test;
//           });
//           ctx.fillText(line, shape.x + 20, lineY);
//         }

//         if (shape.type === "line") {
//           ctx.beginPath();
//           ctx.moveTo((shape.from?.[0] || shape.x) + 20, (shape.from?.[1] || shape.y) + offsetY);
//           ctx.lineTo((shape.to?.[0] || shape.x + 100) + 20, (shape.to?.[1] || shape.y) + offsetY);
//           ctx.stroke();
//         }

//         ctx.restore();
//       });

//       // Step label
//       ctx.save();
//       ctx.fillStyle = COLORS.accent;
//       ctx.font = "bold 13px 'Segoe UI'";
//       ctx.fillText(`Step ${si + 1}`, 20, offsetY + 18);
//       ctx.restore();
//     });
//   }, [sketchSteps, activeStep]);

//   return (
//     <canvas
//       ref={canvasRef}
//       width={680}
//       height={700}
//       style={{
//         background: "#f5f0e8",
//         borderRadius: 12,
//         boxShadow: "0 4px 24px #0004",
//         width: "100%",
//       }}
//     />
//   );
// }

function WhiteBoard({ sketchSteps, activeStep }) {
  const canvasRef = useRef(null);
  const animationsRef = useRef([]);

  const cancelAnimations = () => {
    animationsRef.current.forEach(id => cancelAnimationFrame(id));
    animationsRef.current = [];
  };

  const drawPencilLine = (ctx, x1, y1, x2, y2, duration, onDone) => {
    const start = performance.now();
    const animate = (now) => {
      const t = Math.min((now - start) / duration, 1);
      const cx = x1 + (x2 - x1) * t;
      const cy = y1 + (y2 - y1) * t;
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      // Slight wobble for pencil feel
      ctx.lineTo(
        cx + (Math.random() - 0.5) * 0.6,
        cy + (Math.random() - 0.5) * 0.6
      );
      ctx.stroke();
      if (t < 1) {
        const id = requestAnimationFrame(animate);
        animationsRef.current.push(id);
      } else {
        onDone && onDone();
      }
    };
    const id = requestAnimationFrame(animate);
    animationsRef.current.push(id);
  };

  const drawPencilRect = (ctx, x, y, w, h, onDone) => {
    // Draw 4 sides sequentially
    const sides = [
      [x, y, x + w, y],
      [x + w, y, x + w, y + h],
      [x + w, y + h, x, y + h],
      [x, y + h, x, y],
    ];
    let i = 0;
    const next = () => {
      if (i >= sides.length) { onDone && onDone(); return; }
      const [x1, y1, x2, y2] = sides[i++];
      drawPencilLine(ctx, x1, y1, x2, y2, 300, next);
    };
    next();
  };

  const drawPencilText = (ctx, text, x, y, onDone) => {
    const chars = text.slice(0, 40).split("");
    let i = 0;
    let currentX = x;
    const next = () => {
      if (i >= chars.length) { onDone && onDone(); return; }
      ctx.fillText(chars[i], currentX, y);
      currentX += ctx.measureText(chars[i]).width;
      i++;
      const id = setTimeout(next, 30);
      animationsRef.current.push(id);
    };
    next();
  };

  const drawPencilArrow = (ctx, x1, y1, x2, y2, onDone) => {
    drawPencilLine(ctx, x1, y1, x2, y2, 400, () => {
      // Arrowhead
      const angle = Math.atan2(y2 - y1, x2 - x1);
      ctx.beginPath();
      ctx.moveTo(x2, y2);
      ctx.lineTo(x2 - 12 * Math.cos(angle - 0.4), y2 - 12 * Math.sin(angle - 0.4));
      ctx.moveTo(x2, y2);
      ctx.lineTo(x2 - 12 * Math.cos(angle + 0.4), y2 - 12 * Math.sin(angle + 0.4));
      ctx.stroke();
      onDone && onDone();
    });
  };

  const drawStep = (ctx, stepData, offsetY, onDone) => {
    const shapes = stepData.shapes || [];
    let i = 0;

    // Draw step label first
    ctx.save();
    ctx.fillStyle = "#c0392b";
    ctx.font = "bold 13px 'Patrick Hand', cursive, sans-serif";
    ctx.fillText(`Step ${stepData.step}`, 22, offsetY + 16);
    ctx.restore();

    const nextShape = () => {
      if (i >= shapes.length) { onDone && onDone(); return; }
      const shape = shapes[i++];
      const sy = (shape.y || 0) + offsetY + 20;
      const sx = (shape.x || 0) + 20;

      ctx.save();
      ctx.strokeStyle = "#1a1a2e";
      ctx.fillStyle = "#1a1a2e";
      ctx.lineWidth = 1.8;
      ctx.lineCap = "round";
      ctx.lineJoin = "round";

      if (shape.type === "rect") {
        ctx.strokeStyle = "#2c3e50";
        drawPencilRect(ctx, sx, sy, shape.w || 240, shape.h || 44, () => {
          ctx.restore();
          // Write text inside after drawing box
          if (shape.text) {
            ctx.save();
            ctx.fillStyle = "#2c3e50";
            ctx.font = "bold 12px 'Patrick Hand', cursive, sans-serif";
            drawPencilText(ctx, shape.text, sx + 8, sy + 26, () => {
              ctx.restore();
              setTimeout(nextShape, 100);
            });
          } else {
            setTimeout(nextShape, 100);
          }
        });
      } else if (shape.type === "text") {
        ctx.fillStyle = "#34495e";
        ctx.font = "12px 'Patrick Hand', cursive, sans-serif";
        drawPencilText(ctx, shape.text || "", sx, sy + 10, () => {
          ctx.restore();
          setTimeout(nextShape, 100);
        });
      } else if (shape.type === "arrow") {
        const from = shape.from || [sx, sy];
        const to = shape.to || [sx + 80, sy];
        drawPencilArrow(ctx, from[0] + 20, from[1] + offsetY, to[0] + 20, to[1] + offsetY, () => {
          ctx.restore();
          setTimeout(nextShape, 100);
        });
      } else if (shape.type === "circle") {
        // Animate circle as arc
        const r = shape.r || 25;
        const start = performance.now();
        const animCircle = (now) => {
          const t = Math.min((now - start) / 600, 1);
          ctx.beginPath();
          ctx.arc(sx, sy, r, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * t);
          ctx.stroke();
          if (t < 1) {
            const id = requestAnimationFrame(animCircle);
            animationsRef.current.push(id);
          } else {
            if (shape.text) {
              ctx.fillStyle = "#2c3e50";
              ctx.font = "11px sans-serif";
              ctx.fillText(shape.text.slice(0, 8), sx - 16, sy + 4);
            }
            ctx.restore();
            setTimeout(nextShape, 100);
          }
        };
        const id = requestAnimationFrame(animCircle);
        animationsRef.current.push(id);
      } else {
        ctx.restore();
        nextShape();
      }
    };
    nextShape();
  };

  useEffect(() => {
    if (!sketchSteps || activeStep < 0) return;
    cancelAnimations();

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");

    // Only draw the new active step, don't redraw everything
    if (activeStep === 0) {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    }

    const stepData = sketchSteps[activeStep];
    if (!stepData) return;

    const offsetY = activeStep * 160;
    drawStep(ctx, stepData, offsetY, () => {
      // Draw separator line after step
      ctx.save();
      ctx.strokeStyle = "#ccc";
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(20, offsetY + 150);
      ctx.lineTo(640, offsetY + 150);
      ctx.stroke();
      ctx.restore();
    });
  }, [activeStep]);

  return (
    <div style={{ position: "relative" }}>
      {/* Pencil icon */}
      <div style={{
        position: "absolute", top: -32, right: 8,
        fontSize: 13, color: "#888", display: "flex", alignItems: "center", gap: 6
      }}>
        <span style={{ fontSize: 18 }}>✏️</span> Drawing...
      </div>
      <canvas
        ref={canvasRef}
        width={680}
        height={700}
        style={{
          background: "#fdf6e3",
          borderRadius: 12,
          boxShadow: "4px 4px 20px #0003, inset 0 0 60px #e8d9b520",
          width: "100%",
          // Lined paper effect via CSS
          backgroundImage: `repeating-linear-gradient(
            transparent,
            transparent 31px,
            #c5d0e020 31px,
            #c5d0e020 32px
          )`,
        }}
      />
    </div>
  );
}

export default function App() {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [steps, setSteps] = useState([]);
  const [sketch, setSketch] = useState([]);
  const [activeStep, setActiveStep] = useState(-1);
  const [audioUrl, setAudioUrl] = useState(null);
  const audioRef = useRef(null);

  const handleAsk = async () => {
    if (!question.trim()) return;
    setLoading(true);
    setSteps([]);
    setSketch([]);
    setActiveStep(-1);
    setAudioUrl(null);

    try {
      const res = await axios.post(`${GPU_NODE}/explain`, { question });
      const { steps, sketch, audio_url } = res.data;
      setSteps(steps);
      setSketch(sketch);
      setAudioUrl(`${GPU_NODE}${audio_url}`);

      // Animate steps one by one
      steps.forEach((_, i) => {
        setTimeout(() => setActiveStep(i), i * 3000);
      });
    } catch (e) {
      alert("Error connecting to backend. Is your GPU node running?");
    }
    setLoading(false);
  };

  useEffect(() => {
    if (audioUrl && audioRef.current) {
      audioRef.current.load();
      audioRef.current.play();
    }
  }, [audioUrl]);

  return (
    <div style={{ minHeight: "100vh", background: COLORS.bg, color: COLORS.white, fontFamily: "'Segoe UI', sans-serif" }}>
      {/* Header */}
      <div style={{ background: COLORS.panel, padding: "18px 40px", display: "flex", alignItems: "center", gap: 16, boxShadow: "0 2px 12px #0006" }}>
        <span style={{ fontSize: 28 }}>🎓</span>
        <span style={{ fontSize: 22, fontWeight: 700, color: COLORS.accent }}>SketchTeach</span>
        <span style={{ fontSize: 13, color: COLORS.gray, marginLeft: 8 }}>AI Whiteboard Tutor</span>
      </div>

      <div style={{ maxWidth: 1100, margin: "0 auto", padding: "32px 24px" }}>
        {/* Input */}
        <div style={{ display: "flex", gap: 12, marginBottom: 32 }}>
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleAsk()}
            placeholder="Ask anything... e.g. Explain recursion, How does TCP work?"
            style={{
              flex: 1, padding: "14px 20px", borderRadius: 10, border: "none",
              background: COLORS.panel, color: COLORS.white, fontSize: 15,
              outline: "2px solid transparent", transition: "outline 0.2s",
            }}
            onFocus={(e) => e.target.style.outline = `2px solid ${COLORS.accent}`}
            onBlur={(e) => e.target.style.outline = "2px solid transparent"}
          />
          <button
            onClick={handleAsk}
            disabled={loading}
            style={{
              padding: "14px 28px", borderRadius: 10, border: "none",
              background: loading ? COLORS.gray : COLORS.accent,
              color: "#fff", fontWeight: 700, fontSize: 15, cursor: loading ? "not-allowed" : "pointer",
              transition: "background 0.2s",
            }}
          >
            {loading ? "Thinking..." : "✦ Ask"}
          </button>
        </div>

        {/* Audio player (hidden, auto plays) */}
        {audioUrl && <audio ref={audioRef} src={audioUrl} style={{ display: "none" }} />}

        {/* Main content */}
        {steps.length > 0 && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
            {/* Left: Steps */}
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              {steps.map((s, i) => (
                <div
                  key={i}
                  style={{
                    background: i <= activeStep ? COLORS.panel : "#11112a",
                    border: `1.5px solid ${i === activeStep ? COLORS.accent : "#2a2a4a"}`,
                    borderRadius: 12, padding: "16px 20px",
                    transition: "all 0.4s ease",
                    opacity: i <= activeStep ? 1 : 0.4,
                    transform: i === activeStep ? "scale(1.02)" : "scale(1)",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
                    <span style={{
                      background: i <= activeStep ? COLORS.accent : COLORS.gray,
                      borderRadius: "50%", width: 24, height: 24,
                      display: "flex", alignItems: "center", justifyContent: "center",
                      fontSize: 12, fontWeight: 700, flexShrink: 0, transition: "background 0.4s"
                    }}>{s.step}</span>
                    <span style={{ fontWeight: 700, fontSize: 15 }}>{s.title}</span>
                  </div>
                  <p style={{ margin: 0, color: COLORS.gray, fontSize: 13, lineHeight: 1.6 }}>{s.explanation}</p>
                </div>
              ))}
            </div>

            {/* Right: Whiteboard */}
            <div>
              <div style={{ marginBottom: 10, fontSize: 13, color: COLORS.gray }}>
                🖊️ Drawing on whiteboard...
              </div>
              <WhiteBoard sketchSteps={sketch} activeStep={activeStep} />
            </div>
          </div>
        )}

        {/* Empty state */}
        {steps.length === 0 && !loading && (
          <div style={{ textAlign: "center", marginTop: 80, color: COLORS.gray }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>🖊️</div>
            <div style={{ fontSize: 18, marginBottom: 8 }}>Ask a question to start learning</div>
            <div style={{ fontSize: 13 }}>The AI will explain, draw, and speak the concept for you</div>
          </div>
        )}

        {loading && (
          <div style={{ textAlign: "center", marginTop: 80, color: COLORS.gray }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>⚙️</div>
            <div style={{ fontSize: 18 }}>AI is thinking and preparing your lesson...</div>
          </div>
        )}
      </div>
    </div>
  );
}