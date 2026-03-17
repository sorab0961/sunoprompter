from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware

from audio_utils import (
    analyze_music,
    analyze_voice,
    detect_emotional_arc,
    download_youtube_audio,
    extract_features,
    generate_prompt,
    generate_recreate_prompt,
    generate_vibe_description,
    load_audio,
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/api/analyze")
async def analyze(
    file: UploadFile = File(None),
    youtube_url: str = Form(None)
) -> dict:
    print("Request received")

    if not file and not youtube_url:
        return {"error": "No input provided"}

    temp_dir = Path("temp")
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        if file:
            print("Processing file upload")
            safe_name = Path(file.filename).name or "audio_upload"
            audio_path = temp_dir / safe_name
            with audio_path.open("wb") as f:
                f.write(await file.read())
            print(f"Saved upload to: {audio_path}")

        elif youtube_url:
            print("Processing YouTube URL:", youtube_url)
            try:
                audio_path = download_youtube_audio(youtube_url, temp_dir)
                print(f"Downloaded YouTube audio to: {audio_path}")
            except Exception as exc:  # noqa: BLE001
                print(f"YouTube download failed: {exc}")
                return {"error": f"YouTube download failed: {exc}"}

        # Analysis pipeline
        waveform, sr = load_audio(audio_path)
        print(f"Audio loaded from: {audio_path}")

        features = extract_features(waveform, sr)
        print("Features extracted")

        voice = analyze_voice(features)
        music = analyze_music(features)
        print("Analysis completed")

        vibe = generate_vibe_description(features)
        emotional_arc = detect_emotional_arc(waveform)
        print(f"Emotional arc: {emotional_arc}")

        prompts = generate_prompt(voice, music)
        recreate = generate_recreate_prompt(voice, music, vibe)
        prompts["recreate"] = recreate
        print("Prompts generated")

        return {
            "voice": voice,
            "music": music,
            "vibe": vibe,
            "emotional_arc": emotional_arc,
            "prompts": prompts,
        }

    except Exception as exc:  # noqa: BLE001
        print(f"Analysis failed: {exc}")
        return {"error": f"Analysis failed: {exc}"}
