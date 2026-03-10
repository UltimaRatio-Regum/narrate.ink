import os
os.environ.setdefault("OMP_NUM_THREADS", "4")

import io
import base64
import tempfile
import logging
import wave
import numpy as np
import torch
import pyrubberband as pyrb
import soundfile as sf
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import Response, JSONResponse, HTMLResponse
from pydantic import BaseModel, Field
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("styletts2-engine")

BEARER_TOKEN = os.environ.get("API_KEY", "")
SAMPLE_RATE = 24000
BIT_DEPTH = 16
CHANNELS = 1
MAX_SECONDS = 60

CANONICAL_EMOTIONS = [
    "neutral", "happy", "sad", "angry", "fear",
    "surprise", "disgust", "excited", "calm", "confused",
    "anxious", "hopeful", "melancholy", "fearful",
]

EMOTION_PRESETS = {
    "neutral":   {"alpha": 0.3,  "beta": 0.7,  "embedding_scale": 1,   "diffusion_steps": 5},
    "happy":     {"alpha": 0.1,  "beta": 0.9,  "embedding_scale": 2,   "diffusion_steps": 10},
    "sad":       {"alpha": 0.1,  "beta": 0.9,  "embedding_scale": 2,   "diffusion_steps": 10},
    "angry":     {"alpha": 0.1,  "beta": 0.9,  "embedding_scale": 2,   "diffusion_steps": 10},
    "fear":      {"alpha": 0.1,  "beta": 0.9,  "embedding_scale": 2,   "diffusion_steps": 10},
    "excited":   {"alpha": 0.05, "beta": 0.95, "embedding_scale": 2.5, "diffusion_steps": 10},
    "calm":      {"alpha": 0.5,  "beta": 0.5,  "embedding_scale": 1,   "diffusion_steps": 5},
    "surprise":  {"alpha": 0.1,  "beta": 0.9,  "embedding_scale": 2,   "diffusion_steps": 10},
    "surprised": {"alpha": 0.1,  "beta": 0.9,  "embedding_scale": 2,   "diffusion_steps": 10},
    "whisper":   {"alpha": 0.5,  "beta": 0.3,  "embedding_scale": 0.5, "diffusion_steps": 10},
    "confused":  {"alpha": 0.2,  "beta": 0.8,  "embedding_scale": 1.5, "diffusion_steps": 8},
    "anxious":   {"alpha": 0.15, "beta": 0.85, "embedding_scale": 1.8, "diffusion_steps": 10},
    "hopeful":   {"alpha": 0.2,  "beta": 0.8,  "embedding_scale": 1.8, "diffusion_steps": 8},
    "melancholy":{"alpha": 0.15, "beta": 0.85, "embedding_scale": 1.8, "diffusion_steps": 10},
    "fearful":   {"alpha": 0.1,  "beta": 0.9,  "embedding_scale": 2,   "diffusion_steps": 10},
    "disgust":   {"alpha": 0.1,  "beta": 0.9,  "embedding_scale": 2,   "diffusion_steps": 10},
}

EMOTION_SPEED_MAP = {
    "neutral":    1.0,
    "happy":      1.04,
    "sad":        0.94,
    "angry":      1.06,
    "fear":       1.05,
    "excited":    1.08,
    "calm":       0.94,
    "surprise":   1.05,
    "surprised":  1.05,
    "whisper":    0.92,
    "confused":   0.97,
    "anxious":    1.04,
    "hopeful":    1.02,
    "melancholy": 0.93,
    "fearful":    1.05,
    "disgust":    0.98,
}

EMOTION_PITCH_MAP = {
    "neutral":    0.0,
    "happy":      0.5,
    "sad":       -0.4,
    "angry":     -0.3,
    "fear":       0.3,
    "excited":    0.7,
    "calm":       0.0,
    "surprise":   0.6,
    "surprised":  0.6,
    "whisper":   -0.2,
    "confused":   0.2,
    "anxious":    0.3,
    "hopeful":    0.3,
    "melancholy":-0.3,
    "fearful":    0.3,
    "disgust":   -0.2,
}

tts_engine = None


def ensure_nltk_data():
    import nltk
    for pkg in ['punkt', 'punkt_tab', 'averaged_perceptron_tagger_eng']:
        try:
            nltk.data.find(f'tokenizers/{pkg}' if 'punkt' in pkg else f'taggers/{pkg}')
        except LookupError:
            nltk.download(pkg)


def load_model():
    global tts_engine
    ensure_nltk_data()

    _original_load = torch.load
    def _patched_load(*args, **kwargs):
        kwargs.setdefault("weights_only", False)
        return _original_load(*args, **kwargs)
    torch.load = _patched_load

    from styletts2 import tts as styletts2_tts

    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"Loading StyleTTS2 model on {device}...")

    tts_engine = styletts2_tts.StyleTTS2()
    logger.info("StyleTTS2 model loaded successfully.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_model()
    yield


app = FastAPI(title="StyleTTS2 TTS Engine", lifespan=lifespan)


def verify_auth(request: Request):
    if not BEARER_TOKEN:
        return None
    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {BEARER_TOKEN}":
        return JSONResponse(
            status_code=401,
            content={"error": "Unauthorized", "error_code": "UNAUTHORIZED"}
        )
    return None


def numpy_to_wav_bytes(audio_np: np.ndarray, sample_rate: int) -> bytes:
    audio_np = np.clip(audio_np, -1.0, 1.0)
    audio_int16 = (audio_np * 32767).astype(np.int16)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_int16.tobytes())
    return buf.getvalue()


class ConvertRequest(BaseModel):
    input_text: str
    builtin_voice_id: Optional[str] = None
    voice_to_clone_sample: Optional[str] = None
    random_seed: Optional[int] = None
    emotion_set: list[str] = Field(default_factory=lambda: ["neutral"])
    intensity: int = Field(default=50, ge=1, le=100)
    volume: int = Field(default=75, ge=1, le=100)
    speed_adjust: float = Field(default=0.0, ge=-5.0, le=5.0)
    pitch_adjust: float = Field(default=0.0, ge=-5.0, le=5.0)


@app.post("/GetEngineDetails")
async def get_engine_details(request: Request):
    auth_err = verify_auth(request)
    if auth_err:
        return auth_err

    return {
        "engine_id": "styletts2",
        "engine_name": "StyleTTS2",
        "sample_rate": SAMPLE_RATE,
        "bit_depth": BIT_DEPTH,
        "channels": CHANNELS,
        "max_seconds_per_conversion": MAX_SECONDS,
        "supports_voice_cloning": True,
        "builtin_voices": [],
        "supported_emotions": CANONICAL_EMOTIONS,
        "extra_properties": {
            "architecture": "Style diffusion + adversarial training with large SLMs",
            "model": "LibriTTS multi-speaker",
            "parameters": {
                "alpha": "Timbre control (0=reference voice, 1=text-predicted style)",
                "beta": "Prosody control (0=reference voice, 1=text-predicted style)",
                "embedding_scale": "Expressiveness (higher=more emotional)",
                "diffusion_steps": "Style diversity (more steps=more varied)",
            }
        }
    }


@app.post("/ConvertTextToSpeech")
async def convert_text_to_speech(request: Request):
    auth_err = verify_auth(request)
    if auth_err:
        return auth_err

    try:
        body = await request.json()
        req = ConvertRequest(**body)
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e), "error_code": "INVALID_REQUEST"}
        )

    if not req.input_text.strip():
        return JSONResponse(
            status_code=400,
            content={"error": "Input text is empty", "error_code": "INVALID_REQUEST"}
        )

    if req.random_seed is not None:
        torch.manual_seed(req.random_seed)
        np.random.seed(req.random_seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed(req.random_seed)

    temp_files = []

    try:
        emotion = "neutral"
        if req.emotion_set and req.emotion_set[0] in EMOTION_PRESETS:
            emotion = req.emotion_set[0]

        preset = EMOTION_PRESETS[emotion].copy()

        intensity_scale = req.intensity / 50.0

        if req.intensity != 50:
            preset["embedding_scale"] = preset["embedding_scale"] * intensity_scale
            preset["embedding_scale"] = max(0.1, min(5.0, preset["embedding_scale"]))

        base_emotion_speed = EMOTION_SPEED_MAP.get(emotion, 1.0)
        emotion_speed = 1.0 + (base_emotion_speed - 1.0) * intensity_scale
        base_emotion_pitch = EMOTION_PITCH_MAP.get(emotion, 0.0)
        emotion_pitch = base_emotion_pitch * intensity_scale

        logger.info(
            f"StyleTTS2 emotion={emotion}, intensity={req.intensity}, "
            f"preset={preset}, emotion_speed={emotion_speed:.3f}, emotion_pitch={emotion_pitch:.2f}"
        )

        ref_wav_path = None
        if req.voice_to_clone_sample:
            try:
                wav_bytes = base64.b64decode(req.voice_to_clone_sample)
            except Exception:
                return JSONResponse(
                    status_code=400,
                    content={"error": "Invalid base64 in voice_to_clone_sample", "error_code": "INVALID_REQUEST"}
                )

            if len(wav_bytes) < 100:
                return JSONResponse(
                    status_code=400,
                    content={"error": "Voice clone sample is too small", "error_code": "INVALID_REQUEST"}
                )

            tmp_ref = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            tmp_ref.write(wav_bytes)
            tmp_ref.close()
            temp_files.append(tmp_ref.name)

            try:
                sf.read(tmp_ref.name)
            except Exception:
                return JSONResponse(
                    status_code=400,
                    content={"error": "Voice clone sample is not valid audio", "error_code": "INVALID_REQUEST"}
                )

            ref_wav_path = tmp_ref.name

        text = req.input_text.strip()
        is_long = len(text) > 200 or text.count('.') > 2

        if is_long:
            wav = tts_engine.long_inference(
                text,
                target_voice_path=ref_wav_path,
                output_sample_rate=SAMPLE_RATE,
                alpha=preset["alpha"],
                beta=preset["beta"],
                t=0.7,
                diffusion_steps=preset["diffusion_steps"],
                embedding_scale=preset["embedding_scale"],
            )
        else:
            wav = tts_engine.inference(
                text,
                target_voice_path=ref_wav_path,
                output_sample_rate=SAMPLE_RATE,
                alpha=preset["alpha"],
                beta=preset["beta"],
                diffusion_steps=preset["diffusion_steps"],
                embedding_scale=preset["embedding_scale"],
            )

        audio_np = np.array(wav, dtype=np.float32)

        max_val = np.max(np.abs(audio_np))
        if max_val > 0:
            audio_np = audio_np / max_val

        combined_speed = emotion_speed * (1.0 + (req.speed_adjust / 100.0))
        combined_speed = max(0.5, min(2.0, combined_speed))
        if abs(combined_speed - 1.0) > 0.01:
            audio_np = pyrb.time_stretch(audio_np, SAMPLE_RATE, combined_speed)

        combined_pitch = emotion_pitch + (req.pitch_adjust * 0.24)
        if abs(combined_pitch) > 0.01:
            audio_np = pyrb.pitch_shift(audio_np, SAMPLE_RATE, combined_pitch)

        vol_factor = req.volume / 75.0
        audio_np = audio_np * vol_factor

        wav_bytes = numpy_to_wav_bytes(audio_np, SAMPLE_RATE)

        return Response(content=wav_bytes, media_type="audio/wav")

    except Exception as e:
        logger.exception("TTS generation failed")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Audio generation failed",
                "error_code": "GENERATION_FAILED",
            }
        )
    finally:
        for f in temp_files:
            try:
                os.unlink(f)
            except OSError:
                pass


@app.get("/", response_class=HTMLResponse)
async def root():
    html_path = Path(__file__).parent / "index.html"
    return HTMLResponse(content=html_path.read_text())


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "model_loaded": tts_engine is not None,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
