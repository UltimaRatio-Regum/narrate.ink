# Narrator AI - Text to Audiobook Generator

## Overview

Narrator AI is a powerful web application that transforms plain text into expressive audiobooks using AI-powered text-to-speech technology. It combines multiple TTS engines, intelligent speaker detection, and emotion-based audio processing to create natural-sounding narration with distinct character voices.

## Key Features

### Two Workflow Modes

#### Beginner Mode (Recommended for New Users)
A streamlined wizard-style interface for quick audiobook generation:
1. **Upload** - Drag and drop a `.txt` or `.epub` file
2. **Analyze** - Automatic background analysis with progress tracking
3. **Assign Voices** - Choose single voice or per-character voice assignment
4. **Generate** - Create TTS jobs for each chapter automatically

**EPUB Support:**
- Automatic chapter extraction using ebooklib
- Each chapter becomes a separate TTS job
- Real-time progress for multi-chapter books
- Chapter-by-chapter voice assignment

#### Advanced Mode
Full control over text parsing and configuration:
- Manual text input with paste support
- LLM-powered speaker detection with streaming progress
- Per-segment voice and emotion configuration
- Fine-grained control over all TTS parameters

---

## TTS Engines: Comparison Guide

### Engine Comparison Table

| Engine | Voice Cloning | Emotion Control | Quality | Speed | Cost | Best For |
|--------|---------------|-----------------|---------|-------|------|----------|
| **Edge TTS** | ❌ No | ✅ Pitch/Speed | ⭐⭐⭐⭐⭐ | Fast | Free | General use, production |
| **OpenAI TTS** | ❌ No | ✅ Pitch/Speed | ⭐⭐⭐⭐⭐ | Fast | Paid API | Premium quality |
| **Chatterbox Free** | ✅ Yes | ✅ Exaggeration | ⭐⭐⭐⭐ | Slow | Free | Voice cloning (limited) |
| **Chatterbox Paid** | ✅ Yes | ✅ Exaggeration | ⭐⭐⭐⭐ | Medium | Self-hosted | Production voice cloning |
| **Piper TTS** | ❌ No | ✅ Pitch/Speed | ⭐⭐⭐ | Fast | Free/Local | Offline use |
| **Soprano TTS** | ❌ No | ✅ Pitch/Speed | ⭐⭐⭐ | Very Fast | Free/Local | Rapid prototyping |

### Engine Details

#### Edge TTS (Default - Recommended)
**Pros:**
- No API key required
- 300+ voices across 40+ languages
- High-quality Microsoft Azure Neural TTS
- Fast and reliable
- Free to use

**Cons:**
- No voice cloning capability
- Requires internet connection
- Limited emotional expressiveness compared to cloned voices

**Best For:** General audiobook production, quick results, no-cost usage

---

#### OpenAI TTS
**Pros:**
- Premium voice quality
- Six distinct, well-optimized voices
- Excellent for storytelling
- Consistent, professional output

**Cons:**
- Requires OpenAI API key (paid)
- No voice cloning
- Limited to 6 voice options

**Best For:** Professional-quality audiobooks, commercial projects

**Available Voices:**
- `alloy` - Neutral, versatile
- `echo` - Warm, conversational
- `fable` - Expressive, storytelling
- `onyx` - Deep, authoritative
- `nova` - Friendly, engaging
- `shimmer` - Clear, professional

---

#### Chatterbox Free (HuggingFace Spaces)
**Pros:**
- **Voice cloning supported** - Upload any voice sample
- **Dynamic emotion control** via exaggeration parameter
- Free to use
- Per-segment emotion adjustment

**Cons:**
- 300 character limit per generation
- Slower due to HuggingFace queue
- May have rate limits during peak usage
- Quality varies with voice sample quality

**Best For:** Experimenting with voice cloning, short passages, custom character voices

---

#### Chatterbox Paid (Self-hosted)
**Pros:**
- **Voice cloning supported** - Full voice cloning capability
- **Dynamic emotion control** via exaggeration parameter
- No character limits
- Faster than free tier
- Full control over API

**Cons:**
- Requires self-hosted HuggingFace Space
- Setup complexity
- Hosting costs

**Best For:** Production voice cloning, long audiobooks with custom voices

---

#### Piper TTS
**Pros:**
- Completely offline
- Fast local generation
- No API costs
- Privacy-friendly

**Cons:**
- Requires Piper CLI installation
- Limited voice options
- Lower quality than neural TTS

**Best For:** Offline usage, privacy-sensitive content, rapid iteration

---

#### Soprano TTS
**Pros:**
- Extremely fast (2000x real-time on GPU)
- Small model size (80M parameters)
- Local generation
- Good for prototyping

**Cons:**
- Requires GPU for optimal performance
- Lower quality than Edge/OpenAI
- No voice cloning

**Best For:** Rapid prototyping, testing, GPU-accelerated workflows

---

## Emotion-Based Prosody System

The application analyzes text sentiment and automatically adjusts audio properties to create more expressive narration.

### How Emotion Affects Audio

Two systems work together:
1. **Pitch/Speed Adjustments** - Applied to all TTS engines via pyrubberband
2. **Exaggeration Parameter** - Applied only to Chatterbox engines

### Pitch and Speed Modifiers (All Engines)

These adjustments are applied via audio post-processing using pyrubberband:

| Emotion | Pitch (semitones) | Speed Factor | Description |
|---------|-------------------|--------------|-------------|
| `neutral` | 0.00 | 1.00 | No adjustment - baseline |
| `happy` | +0.12 | 1.01 | Slightly higher and faster |
| `sad` | -0.12 | 0.99 | Slightly lower and slower |
| `angry` | +0.12 | 1.01 | Higher pitch, faster pace |
| `fearful` | +0.12 | 1.01 | Higher pitch, faster pace |
| `surprised` | +0.12 | 1.01 | Higher pitch, faster pace |
| `disgusted` | -0.12 | 0.99 | Lower pitch, slower pace |
| `excited` | +0.12 | 1.01 | Higher pitch, faster pace |
| `calm` | 0.00 | 0.99 | Normal pitch, slower pace |
| `anxious` | +0.06 | 1.01 | Slightly higher, faster |
| `hopeful` | +0.06 | 1.00 | Slightly higher, normal speed |
| `melancholy` | -0.06 | 0.99 | Slightly lower, slower |

**Note:** +0.12 semitones ≈ 1% pitch increase; 1.01 speed factor = 1% faster

### Exaggeration Parameter (Chatterbox Only)

For Chatterbox engines, an additional "exaggeration" parameter controls how expressively the voice is synthesized. This is dynamically adjusted per segment based on detected emotion:

| Emotion | Exaggeration | Effect |
|---------|--------------|--------|
| `neutral` | 0.50 | Baseline expressiveness |
| `happy` | 0.70 | More expressive, upbeat |
| `sad` | 0.60 | Slightly subdued |
| `angry` | 0.85 | Very expressive, intense |
| `fearful` | 0.75 | Heightened expressiveness |
| `surprised` | 0.80 | Strong expressiveness |
| `disgusted` | 0.70 | More expressive |
| `excited` | 0.90 | Maximum expressiveness |
| `calm` | 0.40 | Subdued, relaxed |
| `anxious` | 0.75 | Heightened tension |
| `hopeful` | 0.60 | Gentle expressiveness |
| `melancholy` | 0.55 | Subtle, wistful |

**How It Works:**
The final exaggeration is calculated as:
```
adjusted = base_exaggeration + (target_exaggeration - base_exaggeration) × sentiment_score
```
Where `sentiment_score` (0-1) indicates confidence in the detected emotion.

---

## Voice Library

### VCTK Corpus Samples

The application includes **103 pre-recorded voice samples** from the **VCTK (Voice Cloning Toolkit) Corpus**, a widely-used dataset for speech synthesis research.

**About VCTK:**
- Created by the Centre for Speech Technology Research, University of Edinburgh
- Contains recordings from 110 English speakers with various accents
- High-quality studio recordings optimized for TTS training
- Includes metadata: gender, age, accent, and regional origin

**Voice Metadata Format:**
```
"Voice 226: M/22 Surrey, England"
        │    │ │   │
        │    │ │   └── Location/Region
        │    │ └────── Age
        │    └──────── Gender (M/F)
        └────────────── Voice ID
```

**Accent Variety:**
- Various British regional accents (Scottish, Irish, Welsh, English regions)
- American accents
- International English speakers

### Using Voice Samples

**For Chatterbox (Voice Cloning):**
- Select a VCTK sample as the voice reference
- The TTS engine will clone the voice characteristics
- Best results with 7-20 second clear audio samples

**For Edge TTS/OpenAI:**
- VCTK samples are for preview only
- Select the corresponding neural voice from the engine's voice list

---

## Text Analysis Process

The text analysis system transforms raw text into structured segments ready for TTS generation.

### Step 1: Dialogue/Narration Separation

The parser identifies:
- **Dialogue**: Text within quotation marks (", ", ", «, »)
- **Narration**: Text outside quotation marks

**Quote Detection Patterns:**
- Straight quotes: `"Hello"`
- Curly quotes: `"Hello"`
- Unicode variants: `«Hello»`, `„Hello"`

### Step 2: Speaker Identification

**Heuristic Detection (Fast, No API):**
Uses dialogue verb patterns to identify speakers:
```
"Hello," said John  →  Speaker: John
Mary replied, "Hi"  →  Speaker: Mary
```

**Supported Dialogue Verbs:**
`said`, `says`, `asked`, `replied`, `answered`, `exclaimed`, `whispered`, `shouted`, `yelled`, `muttered`, `murmured`, `called`, `cried`, `screamed`, `sighed`, `laughed`, `growled`, `snapped`, `hissed`, `roared`, `declared`, `announced`, `inquired`, `responded`, `stated`, `added`, `continued`, `began`, `finished`, `interrupted`, `demanded`, `pleaded`, `begged`, `insisted`, `suggested`, `warned`, `threatened`, `promised`, `admitted`, `confessed`, `explained`, `wondered`

**Speaker Context Tracking:**
- Checks 150 characters before and after each quote
- Maintains speaker history for consecutive dialogue
- Prioritizes post-quote attribution ("Hello," said John)

**LLM-Powered Detection (Advanced Mode):**
- Uses OpenRouter API with GPT-4o-mini
- More accurate for complex dialogue patterns
- Streaming progress updates via Server-Sent Events
- Maintains context across paragraphs

### Step 3: Sentiment/Emotion Analysis

Each segment is analyzed for emotional content using TextBlob and keyword detection:

**Keyword-Based Detection:**
| Category | Trigger Words | Resulting Emotion |
|----------|---------------|-------------------|
| Fear | afraid, scared, terrified, fear, horror, dread, nervous, anxious | `fearful` |
| Anger | angry, furious, rage, hate, damn, hell | `angry` |
| Sadness | sad, cry, tears, grief, mourn, sorrow, depressed | `sad` |
| Excitement | excited, amazing, wonderful, fantastic, incredible, brilliant | `excited` |

**Polarity-Based Detection:**
If no keywords match, TextBlob polarity determines emotion:
- Polarity > 0.5 with high subjectivity → `excited`
- Polarity > 0.3 → `positive`/`happy`
- Polarity < -0.3 → `negative`/`sad`
- Otherwise → `neutral`

**Sentiment Score:**
Each emotion has an associated confidence score (0.0 - 1.0):
- Base score: 0.7 for keyword matches
- Adjusted by polarity/subjectivity for nuance
- Used to scale pitch/speed/exaggeration adjustments

### Step 4: Smart Text Chunking

Text is split into ~30 second audio segments (approximately 75 words at 2.5 words/second):

**Chunking Priority:**
1. **Sentence endings** (. ! ?) - Strongest break point
2. **Quote boundaries** - Never split mid-dialogue
3. **Colons/semicolons** (: ;) - Natural pause points
4. **Commas** - Moderate break points
5. **Conjunctions** (and, but, or, yet, so, for, nor) - Weak break points
6. **Word boundaries** - Last resort fallback

**Quote Integrity:**
The chunker never splits in the middle of quoted dialogue to preserve speaker attribution and context.

---

## Beginner Workflow (Detailed)

### Step 1: Upload Your File

**Supported Formats:**
- `.txt` - Plain text files
- `.epub` - Electronic publication (ebook) format

**EPUB Processing:**
- Extracts all chapters automatically
- Preserves chapter titles and order
- Creates separate analysis for each chapter
- Generates one TTS job per chapter

### Step 2: Choose TTS Engine

Select your preferred engine before uploading:
- **Edge TTS** (Recommended) - Best balance of quality and speed
- **OpenAI** - Premium quality (requires API key)
- **Chatterbox Free/Paid** - For voice cloning
- **Piper** - Offline usage
- **Soprano** - Fast local generation

### Step 3: Automatic Analysis

After upload, the system automatically:
1. Parses text into segments
2. Identifies dialogue vs narration
3. Detects speakers using heuristic patterns
4. Analyzes sentiment for each segment
5. Prepares segments for TTS generation

**Progress Tracking:**
- Real-time progress bar
- Per-chapter status indicators
- Chapter-by-chapter completion tracking

### Step 4: Voice Assignment

**Single Voice Mode:**
- One voice for the entire audiobook
- Simplest option for narration-heavy content
- Narrator voice used for all segments

**Character Voices Mode:**
- Separate voice for each detected speaker
- Narrator voice for non-dialogue segments
- Full control over character sound

**Available Voice Sources:**
- Edge TTS neural voices (300+)
- OpenAI premium voices (6)
- VCTK library samples (103) - for Chatterbox voice cloning

### Step 5: Generate Audiobook

Click "Generate Audiobook" to:
1. Create TTS jobs for each chapter
2. Process segments with assigned voices
3. Apply emotion-based prosody adjustments
4. Combine segments into chapter audio files

**Monitor Progress:**
Switch to the Job Monitor tab to:
- Track generation progress
- Preview completed segments
- Download finished chapters
- Cancel or delete jobs

---

## API Reference

**API Access:**
- **Frontend proxy (port 5000)**: All endpoints are prefixed with `/api/` (e.g., `/api/parse-text`)
- **Direct backend (port 8000)**: Endpoints are at root path (e.g., `/parse-text`)

### File Upload & Analysis

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/uploads | Upload a .txt or .epub file |
| GET | /api/uploads | List all uploads |
| GET | /api/uploads/:id | Get upload status and chapters |
| POST | /api/uploads/:id/analyze | Start background text analysis |
| POST | /api/uploads/:id/generate | Generate TTS jobs from analyzed upload |
| GET | /api/uploads/:id/chapters/:chapterId/analysis | Get analysis for a specific chapter |
| DELETE | /api/uploads/:id | Delete an upload |

### Text Parsing

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/parse-text | Basic text parsing without LLM |
| POST | /api/parse-text-llm-stream | LLM-powered parsing with SSE streaming |
| POST | /api/parse-text-llm | LLM-powered parsing (non-streaming) |

### Job Management

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

---

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
- **ebooklib** for EPUB parsing
- **SQLAlchemy** for database ORM
- **PostgreSQL** for job persistence

### Audio Processing
- **pydub** for format conversion
- **soundfile** for audio I/O
- **numpy/scipy** for audio manipulation
- **Aggressive silence trimming** via RMS analysis (two-pass: truncate at 2+ seconds, then trim edges)

---

## Running the Application

```bash
npm run dev
```

This single command starts:
- **Node.js Frontend** on port 5000 (proxies API requests to backend)
- **Python Backend** on port 8000 (FastAPI with TTS processing)

---

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

---

## Tips for Best Results

1. **Clean Text**: Remove excessive formatting, page numbers, or headers
2. **Clear Dialogue**: Use consistent quote marks for speech
3. **Speaker Tags**: Include "said X" patterns for better speaker detection
4. **Voice Matching**: Match voices to character demographics for immersion
5. **Preview First**: Test with a short excerpt before processing long texts
6. **Use Edge TTS**: For fastest results without API costs
7. **EPUB Structure**: Well-structured EPUBs with chapter divisions work best

---

## Limitations

- Chatterbox Free has a 300 character limit per generation
- Soprano TTS does not support voice cloning
- Voice cloning quality depends on reference audio quality
- Very long texts may take significant time to process
- Some TTS engines require GPU for optimal performance
- VCTK voice samples are English-only
