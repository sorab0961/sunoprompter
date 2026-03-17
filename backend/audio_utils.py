from __future__ import annotations

import shutil
import os
from pathlib import Path
from typing import Dict, List

import librosa
import numpy as np
from yt_dlp import YoutubeDL

# Pitch bounds for human voice detection
FMIN = librosa.note_to_hz("C2")  # ~65 Hz
FMAX = librosa.note_to_hz("C7")  # ~2093 Hz


# ---------------------------------------------------------------------------
# FFmpeg helpers
# ---------------------------------------------------------------------------

def _candidate_ffmpeg_paths() -> list[Path]:
    """Return likely ffmpeg.exe locations on Windows for WinGet/Gyan installs."""
    home = Path.home()
    candidates: list[Path] = []
    pkg_root = home / "AppData/Local/Microsoft/WinGet/Packages"
    if pkg_root.exists():
        for exe in pkg_root.glob("*ffmpeg*/**/bin/ffmpeg.exe"):
            candidates.append(exe)
    candidates.append(Path("C:/ffmpeg/bin/ffmpeg.exe"))
    return candidates


def ensure_ffmpeg() -> None:
    """Ensure ffmpeg is available, prepending known paths to PATH if needed."""
    # 1. Check custom location from Environment Variable
    env_path = os.environ.get("FFMPEG_PATH")
    if env_path:
        env_exe = Path(env_path)
        if env_exe.is_file():
            os.environ["PATH"] = str(env_exe.parent) + os.pathsep + os.environ.get("PATH", "")
            return
        elif env_exe.is_dir():
            os.environ["PATH"] = str(env_exe) + os.pathsep + os.environ.get("PATH", "")
            return

    # 2. Standard system lookups
    if shutil.which("ffmpeg") is not None:
        return

    # 3. Windows locale candidates (fallback for local dev)
    for exe in _candidate_ffmpeg_paths():
        if exe.exists():
            os.environ["PATH"] = str(exe.parent) + os.pathsep + os.environ.get("PATH", "")
            if shutil.which("ffmpeg") is not None:
                return

    raise RuntimeError(
        "ffmpeg is not installed or not on PATH. "
        "Set FFMPEG_PATH environment variable or install it (e.g., winget install Gyan.FFmpeg) and retry."
    )


# ---------------------------------------------------------------------------
# Audio I/O
# ---------------------------------------------------------------------------

def load_audio(path: str | Path) -> tuple[np.ndarray, int]:
    """Load audio as mono waveform and sample rate using librosa."""
    ensure_ffmpeg()
    y, sr = librosa.load(Path(path), sr=None, mono=True)
    return y, sr


def extract_features(y: np.ndarray | str | Path, sr: int | None = None) -> Dict[str, float]:
    """
    Compute core features: tempo, pitch, and average energy.

    Accepts either a waveform array with sample rate, or a file path
    (in which case the audio is loaded internally).
    """
    if sr is None and isinstance(y, (str, Path)):
        y, sr = load_audio(y)
    if not isinstance(y, np.ndarray) or sr is None:
        raise ValueError("extract_features expects a waveform plus sample rate, or an audio file path.")

    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    # librosa ≥0.10 may return tempo as a 1-d array shape (1,); squeeze to scalar first
    tempo_val = float(np.squeeze(tempo))
    pitch_track = librosa.yin(y, fmin=FMIN, fmax=FMAX)
    pitch_hz = float(np.nanmedian(pitch_track))
    energy = float(np.mean(np.abs(y)))
    return {"tempo": tempo_val, "pitch": pitch_hz, "energy": energy}


# ---------------------------------------------------------------------------
# YouTube download
# ---------------------------------------------------------------------------

def download_youtube_audio(url: str, output_dir: str | Path | None = None) -> Path:
    """Download audio from YouTube and return the file path."""
    ensure_ffmpeg()
    temp_dir = Path(output_dir) if output_dir is not None else Path("temp")
    temp_dir.mkdir(parents=True, exist_ok=True)
    clean_url = url.strip()
    outtmpl = (temp_dir / "audio.%(ext)s").resolve().as_posix()

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "quiet": True,
        "noplaylist": True,
        "windowsfilenames": True,
        "restrictfilenames": True,
        "paths": {"home": temp_dir.resolve().as_posix()},
        "ffmpeg_location": shutil.which("ffmpeg"),
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(clean_url, download=True)
        downloaded = Path(ydl.prepare_filename(info))
        if downloaded.exists():
            return downloaded
        ext = info.get("ext", "m4a")
        fallback = temp_dir / f"audio.{ext}"
        if fallback.exists():
            return fallback
        raise FileNotFoundError(f"Downloaded file not found at {downloaded} or {fallback}")


# ---------------------------------------------------------------------------
# Voice Analysis
# ---------------------------------------------------------------------------

def analyze_voice(features: Dict[str, float]) -> Dict[str, str | float]:
    """
    Classify voice type, texture, presence, style and emotion
    using both pitch and energy from the features dict.
    """
    pitch_hz = float(features["pitch"])
    energy = float(features["energy"])
    bpm = float(features["tempo"])

    # Voice type — pitch-driven
    if pitch_hz < 120:
        voice_type = "deep male vocal"
    elif pitch_hz <= 180:
        voice_type = "mid-range vocal"
    else:
        voice_type = "bright / airy vocal"

    # Texture — energy-driven
    if energy < 0.1:
        texture = "soft / breathy"
    elif energy < 0.3:
        texture = "clean / emotional"
    else:
        texture = "powerful / slightly raspy"

    # Presence — energy-driven
    presence = "intimate" if energy < 0.1 else "strong"

    # Emotion — tempo + energy
    emotion = _emotion_from_tempo_energy(bpm, energy)

    return {
        "pitch_hz": round(pitch_hz, 2),
        "type": voice_type,
        "texture": texture,
        "presence": presence,
        "style": "melodic, cinematic, emotional",
        "emotion": emotion,
    }


def _emotion_from_tempo_energy(bpm: float, energy: float) -> str:
    """Map tempo and energy to an emotional description."""
    if bpm < 90 and energy < 0.12:
        return "deeply melancholic and introspective"
    if bpm < 120:
        return "emotional and reflective"
    return "uplifting and energetic"


# ---------------------------------------------------------------------------
# Music Analysis
# ---------------------------------------------------------------------------

def analyze_music(features: Dict[str, float]) -> Dict[str, str | float | List[str]]:
    """Derive music attributes from tempo and energy."""
    bpm = float(features["tempo"])
    energy = float(features["energy"])

    # Mood — energy-primary
    if energy < 0.12:
        mood = "sad / melancholic"
        vibe_tags = ["lonely", "dark", "emotional"]
    elif energy < 0.25:
        mood = "emotional / reflective"
        vibe_tags = ["dreamy", "reflective", "cinematic"]
    else:
        mood = "energetic"
        vibe_tags = ["uplifting", "energetic", "vibrant"]

    # Tempo feel
    if bpm < 90:
        tempo_type = "slow"
    elif bpm <= 130:
        tempo_type = "mid-tempo"
    else:
        tempo_type = "fast"

    return {
        "bpm": round(bpm, 2),
        "energy": round(energy, 4),
        "mood": mood,
        "tempo_type": tempo_type,
        "genre": "cinematic pop",
        "instruments": ["piano", "strings", "ambient pads"],
        "vibe_tags": vibe_tags,
    }


# ---------------------------------------------------------------------------
# Vibe Engine
# ---------------------------------------------------------------------------

def generate_vibe_description(features: Dict[str, float]) -> str:
    """
    Generate a natural-language vibe sentence using energy + tempo + pitch together.

    Thresholds:
        energy  — low < 0.12, mid 0.12–0.25, high > 0.25
        tempo   — slow < 90 BPM, mid 90–130 BPM, fast > 130 BPM
        pitch   — low < 120 Hz, mid 120–180 Hz, high > 180 Hz
    """
    energy = float(features["energy"])
    bpm    = float(features["tempo"])
    pitch  = float(features["pitch"])

    # Classify each dimension
    e = "low" if energy < 0.12 else ("mid" if energy < 0.25 else "high")
    t = "slow" if bpm < 90 else ("mid" if bpm <= 130 else "fast")
    p = "low" if pitch < 120 else ("mid" if pitch <= 180 else "high")

    # Rule-based human sentences
    if e == "low" and t == "mid":
        return (
            "Melancholic, introspective and deeply emotional — "
            "the kind of sound that sits with you long after it ends."
        )
    if e == "low" and p == "high":
        return (
            "Fragile and airy, with an emotional vulnerability at its core — "
            "gossamer-thin vocals floating over hushed instrumentation."
        )
    if e == "low" and t == "slow":
        return (
            "Sparse and haunting — slow-burning sadness with cinematic weight, "
            "like a final farewell played at half tempo."
        )
    if e == "mid" and t == "mid":
        return (
            "Dreamy and reflective — a mid-tempo reverie that moves between "
            "nostalgia and quiet hope, warm but tinged with longing."
        )
    if e == "mid" and p == "high":
        return (
            "Emotionally luminous — a bright, soaring quality beneath a "
            "reflective surface, cinematic and quietly powerful."
        )
    if e == "high" and t == "fast":
        return (
            "Energetic and uplifting — a driving pulse that builds momentum "
            "and lifts the listener, euphoric and cinematic."
        )
    if e == "high":
        return (
            "Bold and immersive — strong presence and emotional intensity, "
            "cinematic in scale with a powerful forward motion."
        )

    # Soft fallback
    return (
        f"A cinematic, emotionally resonant soundscape — "
        f"{t} in pace, with a {'warm and intimate' if e == 'low' else 'expansive'} atmosphere."
    )


# ---------------------------------------------------------------------------
# Emotional Arc Detection
# ---------------------------------------------------------------------------

def detect_emotional_arc(y: np.ndarray, n_segments: int = 8) -> str:
    """
    Classify the emotional arc of a track by measuring how energy evolves
    across n_segments equal-length chunks of the waveform.

    Returns one of:
      - "slow emotional build"   — energy rises steadily toward the end
      - "steady melancholic tone" — energy stays flat with low variance
      - "dynamic rise and fall"   — energy peaks in the middle or has high variance
    """
    if len(y) < n_segments:
        return "steady melancholic tone"

    chunks = np.array_split(y, n_segments)
    # Root-mean-square energy per chunk
    energies = np.array([float(np.sqrt(np.mean(c ** 2))) for c in chunks])

    # Normalise so thresholds are scale-independent
    e_range = energies.max() - energies.min()
    if e_range < 1e-6:
        return "steady melancholic tone"

    e_norm = (energies - energies.min()) / e_range  # 0..1
    variance = float(np.var(e_norm))

    # Trend: linear regression slope over segment indices
    x = np.arange(n_segments, dtype=float)
    slope = float(np.polyfit(x, e_norm, 1)[0])

    # Peak position (0 = start, 1 = end)
    peak_pos = float(np.argmax(e_norm)) / (n_segments - 1)

    if slope > 0.04 and peak_pos > 0.55:
        # Energy climbs toward the end
        return "slow emotional build"
    if variance < 0.02:
        # Barely changes — sustained, steady feel
        return "steady melancholic tone"
    # Energy peaks mid-track or fluctuates a lot
    return "dynamic rise and fall"


# ---------------------------------------------------------------------------
# Prompt Generator
# ---------------------------------------------------------------------------

def _tempo_label(bpm: float) -> str:
    if bpm < 90:
        return "slow"
    if bpm <= 130:
        return "mid-tempo"
    return "fast"


def _mood_emphasis(mood: str) -> Dict[str, str]:
    """
    Return mood-specific emphasis vocabulary and wording signals.

    Maps the mood string to one of three intensity tiers:
      melancholic | reflective | energetic
    Each tier provides words that get woven into every prompt variant.
    """
    m = mood.lower()

    if any(k in m for k in ("melancholic", "sad", "lonely", "dark")):
        return {
            "tier": "melancholic",
            "keywords": "haunting, lonely, introspective",
            "adj": "haunting",
            "feel": "lonely and introspective",
            "production": "sparse, reverb-heavy, fragile — every silence is intentional",
            "energy_word": "slow burn",
            "closer": "aching and deeply cinematic — built for quiet devastation.",
        }
    if any(k in m for k in ("energetic", "uplifting", "vibrant", "driving")):
        return {
            "tier": "energetic",
            "keywords": "punchy, driving, upbeat",
            "adj": "driving",
            "feel": "punchy and upbeat",
            "production": "tight, forward mix with punchy transients — no wasted space",
            "energy_word": "forward momentum",
            "closer": "vibrant and cinematic — built to move the listener.",
        }
    # Default: reflective / mid-tier
    return {
        "tier": "reflective",
        "keywords": "dreamy, reflective, cinematic",
        "adj": "dreamy",
        "feel": "reflective and cinematic",
        "production": "warm, mid-range focused, gentle reverb — melodic and immersive",
        "energy_word": "gentle pulse",
        "closer": "emotionally resonant and quietly powerful.",
    }


def _vocal_description(
    voice_analysis: Dict[str, str | float],
    tier: str,
    bpm: float,
) -> str:
    """
    Build a rich, natural storytelling vocal description:
      '<breath_control> in delivery, <phrasing> with the phrasing...'
    """
    texture  = str(voice_analysis.get("texture",  "clean"))
    presence = str(voice_analysis.get("presence", "strong"))
    energy   = float(voice_analysis.get("pitch_hz", 150))

    # ── Breath control — derived from texture ────────────────────────────────
    if "breathy" in texture or "soft" in texture:
        breath = "starts with soft, breathy tones"
    elif "airy" in texture:
        breath = "carries an airy, floating head-voice quality"
    else:
        breath = "maintains controlled, resonant support"

    # ── Phrasing — derived from tier + BPM ──────────────────────────────────
    if tier == "melancholic" or bpm < 90:
        phrasing = "lingering on each note with a stretched, unhurried pace"
    elif tier == "energetic" or bpm > 130:
        phrasing = "using broken, punchy delivery for rhythm"
    else:
        phrasing = "flowing continuously with a conversational ease"

    # ── Vocal Distance — NEW ────────────────────────────────────────────────
    if presence == "intimate":
        distance = "positioned intimate and close-mic'd, right in the center cage"
    elif tier == "melancholic":
        distance = "placed in a distant, echoic dark space, solitary"
    else:
        distance = "forward and centered, commanding direct attention"

    # ── Layering — derived from presence ────────────────────────────────────
    if presence == "intimate":
        layering = "supported by a fragile single-track arrangement"
    else:
        layering = "backed by layered harmonies and subtle doubling for depth"

    # ── Vocalise — always included for emotional tiers ──────────────────────
    vocalise = (
        "soft 'ahhh' textures that fill the atmospheric blanks" if tier in ("melancholic", "reflective")
        else "soaring 'ahhh' swells that open wide during the builds"
    )

    return (
        f"The delivery {breath}, {phrasing}. "
        f"The singer is {distance}, {layering} that expands into {vocalise}."
    )


def _build_blocks(
    voice_analysis: Dict[str, str | float],
    music_analysis: Dict[str, str | float | List[str]],
    em: Dict[str, str],
) -> Dict[str, str]:
    """
    Assemble the 7 semantic building blocks shared by all prompt variants.

    [1] EMOTIONAL CORE       — the mood + vibe keywords
    [2] VOCAL STYLE          — voice type, texture, technique
    [3] PACE + TEMPO FEEL    — BPM + tempo descriptor + energy word
    [4] INSTRUMENT LAYERS    — core instruments + layering description
    [5] SPATIAL ATMOSPHERE   — reverb, stereo field, production texture
    [6] SONG STRUCTURE       — intro → verse → chorus → outro arc
    [7] EMOTIONAL NARRATIVE  — the human story the music tells
    """
    instruments: List[str] = music_analysis["instruments"]  # type: ignore[assignment]
    bpm       = float(music_analysis["bpm"])  # type: ignore[arg-type]
    tempo_type = str(music_analysis.get("tempo_type", _tempo_label(bpm)))
    mood      = str(music_analysis["mood"])
    vibe_tags: List[str] = music_analysis.get("vibe_tags", [])  # type: ignore[assignment]

    voice_type = str(voice_analysis["type"])
    texture    = str(voice_analysis["texture"])
    presence   = str(voice_analysis["presence"])
    emotion    = str(voice_analysis.get("emotion", "emotional"))

    vibe_str = ", ".join(vibe_tags) if vibe_tags else em["keywords"]
    instr_lead = instruments[0] if instruments else "piano"
    instr_layer = (
        f"{', '.join(instruments[:-1])} and {instruments[-1]}"
        if len(instruments) > 1 else instr_lead
    )

    # Fixed three-section structure — always present regardless of tier
    chorus_by_tier = {
        "melancholic": "open and expanded layout — layered strings swell into raw vulnerability, with 'ahhh' vocalise rising to the emotional peak",
        "energetic":   "open and explosive layout — full arrangement peaks with high kinetic drive, vocals front and wide",
        "reflective":  "open and expanded layout — strings and layered vocalise build smoothly to a resonant, soaring peak",
    }
    song_structure = (
        f"[Intro] Minimal and atmospheric — slow build from near silence. "
        f"Piano or ambient pad sitting alone. Space precedes sound. "
        f"[Verse] Intimate and storytelling — gradual rise in presence. "
        f"Vocals close and direct, letting the narrative breathe without support. "
        f"[Chorus] {chorus_by_tier.get(em['tier'], chorus_by_tier['reflective'])}. "
        f"[Outro] Strip back to the absolute intro texture. Float into silence."
    )

    narrative_by_tier = {
        "melancholic": "themes of loneliness, reflection and inner struggle, giving a sense of quiet emotional tension",
        "energetic":   "confidence, movement and forward energy",
        "reflective":  "dreamlike drifting and soft introspection",
    }

    emotional_core_by_tier = {
        "melancholic": "deeply vulnerable, melancholic and introspective",
        "reflective":  "soft, reflective and intricately layered",
        "energetic":   "uplifting and high-energy with driving momentum",
    }
    energy = float(music_analysis.get("energy", 0))
    if energy < 0.1:
        intensity = "hauntingly, fragile"
    elif energy < 0.25:
        intensity = "warm, evocative"
    else:
        intensity = "powerful, driving"

    tier = em["tier"]
    return {
        "emotional_core":    f"{intensity} — {emotional_core_by_tier.get(tier, f'{mood.capitalize()} — {em['keywords']}')}",
        "vocal_style":       _vocal_description(voice_analysis, tier, bpm),
        "pace_tempo":        f"{tempo_type.capitalize()}, {int(bpm)} BPM. "
                             f"{em['energy_word'].capitalize()} — the arrangement serves the pacing, not the other way around.",
        "instrument_layers": f"Core: {instr_layer}. "
                             f"Strings carry the emotional midrange. "
                             f"Ambient pads sustain beneath everything, creating depth.",
        "spatial_atmosphere": (
            "wide, spacious, reverb-heavy and ambient"
            if float(music_analysis.get("energy", 0)) < 0.12
            else "balanced, warm and immersive"
            if float(music_analysis.get("energy", 0)) < 0.25
            else "tight, punchy and forward"
        ),
        "song_structure":    song_structure,
        "emotional_narrative": narrative_by_tier.get(tier, narrative_by_tier["reflective"]),
    }


def generate_prompt(
    voice_analysis: Dict[str, str | float],
    music_analysis: Dict[str, str | float | List[str]],
) -> Dict[str, str]:
    """
    Create Suno-ready prompts in three voicings.

    All three share the same 7 semantic blocks:
      [EMOTIONAL CORE] + [VOCAL STYLE + TECHNIQUE] + [PACE + TEMPO FEEL] +
      [INSTRUMENT LAYERS] + [SPATIAL ATMOSPHERE] + [SONG STRUCTURE] + [EMOTIONAL NARRATIVE]

    Cinematic  — labelled sections, detailed, producer-brief style
    Minimal    — all 7 collapsed into one flowing sentence
    Creative   — poetic prose, literary voice
    """
    mood = str(music_analysis["mood"])
    em   = _mood_emphasis(mood)
    b    = _build_blocks(voice_analysis, music_analysis, em)

    # ── CINEMATIC: labelled 7-block prompt ──────────────────────────────────
    cinematic = (
        f"[EMOTIONAL CORE] {b['emotional_core']}\n"
        f"[VOCAL STYLE + TECHNIQUE] {b['vocal_style']}\n"
        f"[PACE + TEMPO FEEL] {b['pace_tempo']}\n"
        f"[INSTRUMENT LAYERS] {b['instrument_layers']}\n"
        f"[SPATIAL ATMOSPHERE] {b['spatial_atmosphere']}\n"
        f"[SONG STRUCTURE] {b['song_structure']}\n"
        f"[EMOTIONAL NARRATIVE] {b['emotional_narrative']}"
    )

    # ── MINIMAL: one producer sentence, all 7 implied ───────────────────────
    minimal = (
        f"{b['emotional_core']} — {b['vocal_style'].split('.')[0].lower()}, "
        f"{b['pace_tempo'].split('.')[0].lower()}, "
        f"{b['instrument_layers'].split('.')[0].lower()}. "
        f"{b['spatial_atmosphere'].split('—')[0].strip().capitalize()}. "
        f"{em['closer']}"
    )

    # ── CREATIVE: poetic prose, literary voice ───────────────────────────────
    creative = (
        f"Feel: {b['emotional_core'].lower()}.\n"
        f"Voice: {b['vocal_style']}\n"
        f"Motion: {b['pace_tempo']}\n"
        f"Sound: {b['instrument_layers']}\n"
        f"Space: {b['spatial_atmosphere']}.\n"
        f"Shape: {b['song_structure']}\n"
        f"Story: {b['emotional_narrative']} "
        f"Like {_creative_simile(em['tier'])}."
    )

    return {
        "cinematic": cinematic,
        "minimal":   minimal,
        "creative":  creative,
    }


def _creative_simile(tier: str) -> str:
    """Return a poetic simile matched to the mood tier."""
    return {
        "melancholic": "a memory you can't shake, playing on repeat at 3 AM",
        "energetic":   "the first light breaking over a city that never stopped moving",
        "reflective":  "a late afternoon that stretches longer than it should",
    }.get(tier, "a feeling that arrives before words do")






def generate_recreate_prompt(
    voice: Dict[str, str | float],
    music: Dict[str, str | float | List[str]],
    vibe: str,
) -> str:
    """Suno recreate prompt using the user-defined template."""
    return (
        f"{music['mood']} cinematic pop track with {voice['texture']} {voice['type']} vocals,\n"
        f"featuring stretched phrasing and subtle \"ahhh\" vocalise textures.\n\n"
        f"The track follows a slow emotional build, starting with a minimal atmospheric intro,\n"
        f"moving into intimate storytelling verses, and expanding into a wide, emotionally rich chorus.\n\n"
        f"Layered piano, soft strings, and ambient pads create a spacious, reverb-heavy soundscape,\n"
        f"giving the track a {vibe} feel.\n\n"
        f"The pacing is {music['tempo_type']} with a gradual rise in intensity,\n"
        f"leading to an emotional peak in the chorus.\n\n"
        f"Themes revolve around loneliness, reflection, and internal emotional depth,\n"
        f"creating a haunting and immersive listening experience."
    )

