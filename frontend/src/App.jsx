import React, { useState } from "react";

/* ── Loading overlay ─────────────────────────────────────── */
function LoadingOverlay() {
  const steps = [
    "Loading audio waveform…",
    "Extracting BPM and pitch…",
    "Running vibe analysis…",
    "Generating Suno prompts…",
  ];
  const [step, setStep] = React.useState(0);

  React.useEffect(() => {
    const id = setInterval(() => setStep((s) => (s + 1) % steps.length), 1800);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="glass rounded-2xl p-10 flex flex-col items-center gap-6 border border-cyan-400/10">
      {/* Pulse dots */}
      <div className="flex gap-3">
        <span className="dot" />
        <span className="dot" />
        <span className="dot" />
      </div>
      {/* Cycling status line */}
      <div className="text-center space-y-1">
        <p className="text-white font-semibold text-lg">Analyzing your track</p>
        <p className="text-white/50 text-sm transition-all duration-500">{steps[step]}</p>
      </div>
      {/* Thin animated progress bar */}
      <div className="w-48 h-1 rounded-full bg-white/10 overflow-hidden">
        <div
          className="h-full rounded-full bg-gradient-to-r from-cyan-400 to-emerald-300"
          style={{ animation: "progressBar 1.8s ease-in-out infinite" }}
        />
      </div>
      <style>{`
        @keyframes progressBar {
          0%   { width: 0%;   margin-left: 0;    }
          50%  { width: 60%;  margin-left: 20%;  }
          100% { width: 0%;   margin-left: 100%; }
        }
      `}</style>
    </div>
  );
}

/* ── Stat tile ───────────────────────────────────────────── */
function Stat({ label, value }) {
  return (
    <div className="flex flex-col gap-1 bg-card/80 rounded-lg p-4 border border-white/5">
      <span className="text-xs uppercase tracking-wide text-white/60">{label}</span>
      <span className="text-lg font-semibold text-white">{value ?? "-"}</span>
    </div>
  );
}

/* ── Prompt card ─────────────────────────────────────────── */
function PromptCard({ label, text, badge, highlight, large, onCopy, copied, animDelay }) {
  return (
    <div
      className={`animate-card rounded-2xl border transition-all ${animDelay}
        ${highlight
          ? "border-cyan-400/60 bg-gradient-to-br from-cyan-950/60 to-emerald-950/50 shadow-xl shadow-cyan-500/10"
          : "border-white/5 bg-card/70"
        }
        ${large ? "p-7" : "p-5"}
      `}
    >
      {/* Header row */}
      <div className={`flex items-center justify-between gap-3 ${large ? "mb-4" : "mb-3"}`}>
        <div className="flex items-center gap-2 flex-wrap">
          <p className={`uppercase tracking-widest text-white/60 font-semibold ${large ? "text-sm" : "text-xs"}`}>
            {label}
          </p>
          {badge && (
            <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-gradient-to-r from-cyan-400 to-emerald-300 text-black">
              {badge}
            </span>
          )}
        </div>
        {/* Copy button with flash feedback */}
        <button
          onClick={onCopy}
          className={`shrink-0 text-xs px-3 py-1.5 rounded-lg font-bold transition-all
            ${copied
              ? "copied-pop bg-emerald-400 text-black scale-105"
              : "bg-white text-black hover:bg-white/90"
            }`}
        >
          {copied ? "✓ Copied!" : "Copy"}
        </button>
      </div>

      {/* Divider for highlight card */}
      {highlight && <div className="border-t border-cyan-400/10 mb-4" />}

      {/* Text */}
      <p className={`leading-relaxed text-white/85 whitespace-pre-line ${large ? "text-sm sm:text-base" : "text-sm"}`}>
        {text}
      </p>
    </div>
  );
}

/* ── App ─────────────────────────────────────────────────── */
export default function App() {
  const [file, setFile] = useState(null);
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [copiedKey, setCopiedKey] = useState("");

  const handleAnalyze = async () => {
    const API_URL = import.meta.env.VITE_API_URL || "";
    setError("");
    setData(null);
    const formData = new FormData();
    if (file) formData.append("file", file);
    if (youtubeUrl) formData.append("youtube_url", youtubeUrl);
    if (!file && !youtubeUrl) { alert("Please upload a file or enter a YouTube URL"); return; }

    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/analyze`, { method: "POST", body: formData });
      const text = await res.text();
      if (!res.ok) throw new Error(text || `Request failed with status ${res.status}`);
      const json = text ? JSON.parse(text) : {};
      if (json.error) throw new Error(json.error);
      setData(json);
    } catch (err) {
      console.error("Error:", err);
      setError(err.message || "Unexpected error");
    } finally {
      setLoading(false);
    }
  };

  const copyPrompt = async (key, text) => {
    if (!text) return;
    await navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(""), 2000);
  };

  const PROMPT_KEYS = [
    { key: "recreate",  label: "Recreate Style", badge: "✦ Best Result", highlight: true,  large: true,  animDelay: "delay-0"   },
    { key: "cinematic", label: "Cinematic",                                highlight: false, large: false, animDelay: "delay-75"  },
    { key: "minimal",   label: "Minimal",                                  highlight: false, large: false, animDelay: "delay-150" },
    { key: "creative",  label: "Creative",                                 highlight: false, large: false, animDelay: "delay-225" },
  ];

  return (
    <div className="min-h-screen px-4 py-10 sm:px-8 md:px-16">

      {/* Header */}
      <header className="max-w-5xl mx-auto text-center mb-10">
        <p className="text-sm text-white/50 mb-2 uppercase tracking-widest font-semibold">AI Song Analyzer</p>
        <h1 className="text-4xl sm:text-5xl font-bold text-white mb-3 leading-tight">
          Upload.&nbsp;Analyze.&nbsp;
          <span className="bg-gradient-to-r from-cyan-400 to-emerald-300 bg-clip-text text-transparent">
            Prompt.
          </span>
        </h1>
        <p className="text-white/60 max-w-xl mx-auto">
          Drop a song or paste a YouTube link. Extract BPM, vocal vibe, and get professional Suno-ready prompts.
        </p>
      </header>

      <main className="max-w-5xl mx-auto space-y-8">

        {/* Input card */}
        <section className="glass rounded-2xl p-6 sm:p-8">
          <form onSubmit={(e) => { e.preventDefault(); handleAnalyze(); }} className="space-y-6">
            <div className="grid md:grid-cols-2 gap-4">
              <label className="flex flex-col gap-2 bg-card/70 border border-white/5 rounded-xl p-4 cursor-pointer hover:border-white/10 transition">
                <span className="text-sm text-white/70 font-medium">Upload audio (mp3 or wav)</span>
                <input
                  type="file"
                  accept="audio/*"
                  className="text-white/70 text-sm"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                />
                {file && <span className="text-xs text-cyan-400">✓ {file.name}</span>}
              </label>

              <div className="flex flex-col gap-2">
                <span className="text-sm text-white/70 font-medium">YouTube link (optional)</span>
                <input
                  type="url"
                  placeholder="https://youtube.com/watch?v=..."
                  value={youtubeUrl}
                  onChange={(e) => setYoutubeUrl(e.target.value)}
                  className="flex-1 bg-card/70 border border-white/5 rounded-xl px-4 py-3 text-white placeholder:text-white/30 focus:outline-none focus:ring-2 focus:ring-cyan-400/60 transition"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full md:w-auto inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-cyan-400 to-emerald-300 text-black font-bold px-8 py-3 shadow-lg shadow-cyan-500/20 transition hover:brightness-110 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                  </svg>
                  Analyzing…
                </>
              ) : "Analyze"}
            </button>
          </form>
        </section>

        {/* Error */}
        {error && (
          <div className="text-sm text-red-400 bg-red-950/40 border border-red-500/20 rounded-xl px-5 py-4 animate-card delay-0">
            ⚠ {error}
          </div>
        )}

        {/* Loading animation */}
        {loading && <LoadingOverlay />}

        {/* Results */}
        {data && !loading && (
          <>
            {/* Vibe banner */}
            <section className="animate-card delay-0 glass rounded-2xl p-6 border border-cyan-400/20 bg-gradient-to-r from-cyan-950/40 to-emerald-950/30 space-y-3">
              <div>
                <p className="text-xs uppercase tracking-widest text-cyan-400/80 font-semibold mb-1">Vibe Detection</p>
                <p className="text-lg text-white font-medium leading-snug">{data.vibe}</p>
              </div>
              {data.emotional_arc && (
                <div className="flex items-center gap-3 pt-3 border-t border-white/5">
                  <span className="text-lg">〰</span>
                  <div>
                    <p className="text-xs uppercase tracking-widest text-emerald-400/70 font-semibold mb-0.5">Emotional Arc</p>
                    <p className="text-white/90 font-medium capitalize">{data.emotional_arc}</p>
                  </div>
                </div>
              )}
            </section>

            {/* Analysis stats */}
            <section className="grid md:grid-cols-2 gap-6">
              <div className="animate-card delay-75 glass rounded-2xl p-6 space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-xl font-semibold text-white">Voice Analysis</h2>
                  <span className="text-xs text-white/40">{data.voice?.pitch_hz ?? "-"} Hz</span>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <Stat label="Type"     value={data.voice?.type} />
                  <Stat label="Texture"  value={data.voice?.texture} />
                  <Stat label="Presence" value={data.voice?.presence} />
                  <Stat label="Emotion"  value={data.voice?.emotion} />
                  <div className="col-span-2"><Stat label="Style" value={data.voice?.style} /></div>
                </div>
              </div>

              <div className="animate-card delay-75 glass rounded-2xl p-6 space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-xl font-semibold text-white">Music Analysis</h2>
                  <span className="text-xs text-white/40">{data.music?.genre}</span>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <Stat label="BPM"    value={data.music?.bpm} />
                  <Stat label="Tempo"  value={data.music?.tempo_type} />
                  <Stat label="Mood"   value={data.music?.mood} />
                  <Stat label="Energy" value={data.music?.energy?.toFixed?.(4)} />
                  <div className="col-span-2">
                    <Stat label="Vibe Tags"   value={data.music?.vibe_tags?.join("  ·  ")} />
                  </div>
                  <div className="col-span-2">
                    <Stat label="Instruments" value={data.music?.instruments?.join(", ")} />
                  </div>
                </div>
              </div>
            </section>

            {/* Prompts */}
            <section className="glass rounded-2xl p-6 sm:p-8 space-y-5">
              <div>
                <h2 className="text-xl font-semibold text-white">Suno Prompts</h2>
                <p className="text-sm text-white/50 mt-1">Four styles generated from your audio's vibe</p>
              </div>
              <div className="space-y-4">
                {PROMPT_KEYS.map(({ key, label, badge, highlight, large, animDelay }) => (
                  <PromptCard
                    key={key}
                    label={label}
                    badge={badge}
                    highlight={highlight}
                    large={large}
                    animDelay={animDelay}
                    text={data.prompts?.[key]}
                    copied={copiedKey === key}
                    onCopy={() => copyPrompt(key, data.prompts?.[key])}
                  />
                ))}
              </div>
            </section>
          </>
        )}
      </main>
    </div>
  );
}
