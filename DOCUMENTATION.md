# Narrator AI - Text to Audiobook Generator

## Overview

Narrator AI is a powerful web application that transforms plain text into expressive audiobooks using AI-powered text-to-speech technology. It combines multiple TTS engines, intelligent speaker detection, and emotion-based audio processing to create natural-sounding narration with distinct character voices.

## Key Features

### Multi-Engine TTS Support
Choose from six different text-to-speech engines, each with unique strengths:

| Engine | Description | Voice Cloning | Requirements |
|--------|-------------|---------------|--------------|
| **Edge TTS** | Microsoft Azure Neural TTS with 300+ voices | No | None (default) |
| **OpenAI TTS** | Premium voices (alloy, echo, fable, onyx, nova, shimmer) | No | OpenAI API key |
| **Chatterbox Free** | ResembleAI via HuggingFace Space (300 char limit) | Yes | Voice sample |
| **Chatterbox Paid** | Custom HuggingFace Space (configurable) | Yes | CHATTERBOX_API_URL + voice sample |
| **Piper TTS** | Open-source local TTS | No | Piper CLI installed |
| **Soprano TTS** | Fast local TTS (80M model) | No | GPU recommended |

**Note:** Not all engines may be available depending on your system configuration. Edge TTS is the recommended default as it works without additional setup.

### Intelligent Speaker Detection

**AI-Powered Detection (LLM)**
- Uses OpenRouter API with GPT-4o-mini for accurate speaker identification
- Streaming progress updates during parsing
- Maintains context across paragraphs for consistent speaker assignment
- Detects sentiment for each segment

**Basic Heuristic Detection**
- Fast, no-API-required fallback
- Uses dialogue verb patterns ("said John", "Mary replied")
- Works with both straight quotes (") and curly quotes (" ")

### Voice Library
- **103 Pre-loaded Voices**: High-quality samples from the VCTK corpus
- **Voice Metadata**: Gender, age, accent, and location information
- **Preview Playback**: Listen to voice samples before selection
- **Search & Filter**: Find voices by gender, accent, or other criteria
- **Custom Uploads**: Add your own voice samples for voice cloning

### Emotion-Based Prosody

The application analyzes text sentiment and automatically adjusts pitch and speed:

| Emotion | Pitch | Speed | Description |
|---------|-------|-------|-------------|
| neutral | 0% | 0% | No adjustment |
| happy | +1% | +1% | Joy, pleasure, positive |
| sad | -1% | -1% | Sorrow, disappointment |
| angry | +1% | +1% | Frustration, confrontation |
| fearful | +1% | +1% | Fear, worry, danger |
| excited | +1% | +1% | Enthusiasm, anticipation |
| calm | 0% | -1% | Peaceful, serene |
| surprised | +1% | +1% | Shock, astonishment |
| anxious | +0.5% | +1% | Nervousness, tension |
| hopeful | +0.5% | 0% | Optimism, looking forward |
| melancholy | -0.5% | -1% | Wistful sadness, nostalgia |

### Asynchronous Job Processing
- **Background Processing**: TTS generation runs in background threads
- **Database Persistence**: Jobs and segments survive page reloads and server restarts
- **Real-time Progress**: 2-second polling for live progress updates
- **Partial Playback**: Listen to completed segments while job is still processing
- **Combined Audio**: Download all segments as a single MP3 file
- **Job Management**: Create, view, cancel, and delete jobs

### Smart Text Chunking
Text is intelligently split into ~30 second audio segments:
1. Respects sentence boundaries (., !, ?)
2. Preserves quote integrity (won't split mid-dialogue)
3. Breaks at natural pause points (colons, semicolons, commas)
4. Handles conjunctions (and, but, or)
5. Graceful fallback for edge cases

## How It Works

### Workflow

1. **Input Text**: Paste or type your story, novel excerpt, or script
2. **Parse & Analyze**: The AI identifies dialogue vs narration, detects speakers, and analyzes sentiment
3. **Assign Voices**: Map each detected speaker to a voice from the library
4. **Generate Audio**: Choose your TTS engine and start generation
5. **Listen & Download**: Preview segments as they complete, then download the full audiobook

### Text Parsing Process

The LLM streaming parser:
1. Splits text into 2-3 paragraph chunks (respecting quote boundaries)
2. Sends each chunk to the LLM for analysis
3. Streams progress updates via Server-Sent Events (SSE)
4. Detects speakers, dialogue/narration types, and sentiment
5. Falls back to basic parsing if LLM fails

## Voice Options

### Edge TTS Voices (Default)
Over 300 voices across 40+ languages. Popular English voices include:
- **en-US-GuyNeural**: Natural American male voice
- **en-US-JennyNeural**: Warm American female voice
- **en-GB-RyanNeural**: British male voice
- **en-GB-SoniaNeural**: British female voice
- **en-AU-WilliamNeural**: Australian male voice

### OpenAI TTS Voices
Six premium voices optimized for different use cases:
- **alloy**: Neutral, versatile
- **echo**: Warm, conversational
- **fable**: Expressive, storytelling
- **onyx**: Deep, authoritative
- **nova**: Friendly, engaging
- **shimmer**: Clear, professional

### Voice Library (VCTK Corpus)
103 voice samples with metadata:
- Format: "Voice 226: M/22 Surrey, England"
- Gender: Male (M) or Female (F)
- Age: Range from young adults to seniors
- Accents: Various British regional accents

### Voice Cloning (Chatterbox)
Upload a 7-20 second audio sample to clone any voice:
- Supported formats: WAV, MP3, OGG
- Best results with clear speech, minimal background noise
- Requires Chatterbox engine (Free or Paid tier)

## API Reference

**API Access:**
- **Frontend proxy (port 5000)**: All endpoints are prefixed with `/api/` (e.g., `/api/parse-text`)
- **Direct backend (port 8000)**: Endpoints are at root path (e.g., `/parse-text`)

The examples below use the `/api/` prefix for frontend access.

### Text Parsing

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/parse-text | Basic text parsing without LLM |
| POST | /api/parse-text-llm-stream | LLM-powered parsing with SSE streaming |
| POST | /api/parse-text-llm | LLM-powered parsing (non-streaming) |

**POST /api/parse-text**
Basic text parsing using heuristic detection.

```json
{
  "text": "Your story text here..."
}
```

**POST /api/parse-text-llm-stream**
LLM-powered parsing with real-time progress updates via Server-Sent Events.

```json
{
  "text": "Your story text here...",
  "model": "openai/gpt-4o-mini",
  "knownSpeakers": ["John", "Mary"]
}
```

SSE Events:
- `progress`: Initial event with total chunks count
- `chunk`: Per-chunk results with segments and detected speakers
- `complete`: Final event with total segment count
- `error`: Error event if parsing fails

### Audio Generation

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/generate | Legacy SSE-based audio generation |
| POST | /api/generate-stream | Streaming audio generation |

### Job Management (Async Processing)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/jobs | Create a new TTS generation job |
| GET | /api/jobs | List all jobs |
| GET | /api/jobs/:id | Get job status and progress |
| GET | /api/jobs/:id/segments | List segments for a job |
| GET | /api/jobs/:id/segments/:segId/audio | Get audio for a specific segment |
| GET | /api/jobs/:id/audio | Get combined audio for completed segments |
| POST | /api/jobs/:id/cancel | Cancel a running job |
| DELETE | /api/jobs/:id | Delete a job and its segments |

### Voice Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/voices | List uploaded voice samples |
| POST | /api/voices/upload | Upload a new voice sample |
| DELETE | /api/voices/:id | Delete a voice sample |
| GET | /api/voice-library | List pre-recorded library voices (VCTK) |
| GET | /api/edge-voices | List available Edge TTS neural voices |
| GET | /api/openai-voices | List available OpenAI TTS voices |

### Health & Status

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/health | Health check endpoint |
| GET | /api/chatterbox-status | Check Chatterbox configuration status |

## Technical Architecture

### Frontend
- **React** with TypeScript
- **Tailwind CSS** for styling
- **TanStack Query** for server state
- **Wouter** for routing
- **Shadcn/ui** components

### Backend
- **FastAPI** (Python) for API server
- **edge-tts** for Microsoft Neural TTS
- **pyrubberband** for audio pitch/speed processing
- **TextBlob** for sentiment analysis
- **SQLAlchemy** for database ORM
- **PostgreSQL** for job persistence

### Audio Processing
- **pydub** for format conversion
- **soundfile** for audio I/O
- **numpy/scipy** for audio manipulation
- Trailing silence trimming via RMS analysis

## Running the Application

The application requires both the Python backend and Node.js frontend to run:

### Quick Start

```bash
npm run dev
```

This single command starts:
- **Node.js Frontend** on port 5000 (proxies API requests to backend)
- **Python Backend** on port 8000 (FastAPI with TTS processing)

### Manual Start (Development)

**Python Backend** (port 8000):
```bash
cd backend && python main.py
```

**Node.js Frontend** (port 5000):
```bash
npm run dev
```

### Database Setup

The application uses PostgreSQL for job persistence. Database tables are created automatically on startup via SQLAlchemy.

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | Frontend server port | 5000 |
| `PYTHON_BACKEND_URL` | Backend API URL | http://127.0.0.1:8000 |
| `AI_INTEGRATIONS_OPENROUTER_BASE_URL` | OpenRouter API base URL | (auto-configured) |
| `AI_INTEGRATIONS_OPENROUTER_API_KEY` | OpenRouter API key | (auto-configured) |
| `OPENAI_API_KEY` | OpenAI API key (required for OpenAI TTS engine) | - |
| `CHATTERBOX_API_URL` | Custom Chatterbox HuggingFace Space URL | - |
| `CHATTERBOX_API_KEY` | Optional Bearer token for Chatterbox | - |
| `DATABASE_URL` | PostgreSQL connection string | (auto-configured) |
| `SESSION_SECRET` | Session encryption key | (auto-configured) |

## Getting Started

1. Enter your text in the input area
2. Click "Analyze Text" to detect speakers and segments
3. Review the parsed segments and detected speakers
4. Assign voices to each speaker from the voice library
5. Select your preferred TTS engine
6. Click "Generate Audio" to start processing
7. Listen to segments as they complete
8. Download the full audiobook when finished

## Tips for Best Results

1. **Clean Text**: Remove excessive formatting, page numbers, or headers
2. **Clear Dialogue**: Use consistent quote marks for speech
3. **Speaker Tags**: Include "said X" patterns for better speaker detection
4. **Voice Matching**: Match voices to character demographics for immersion
5. **Preview First**: Test with a short excerpt before processing long texts
6. **Use Edge TTS**: For fastest results without API costs

## Limitations

- Chatterbox Free has a 300 character limit per generation
- Soprano TTS does not support voice cloning
- Voice cloning quality depends on reference audio quality
- Very long texts may take significant time to process
- Some TTS engines require GPU for optimal performance
