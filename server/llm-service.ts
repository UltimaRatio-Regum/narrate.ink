import OpenAI from "openai";

export function isOpenRouterConfigured(): boolean {
  return !!(
    process.env.AI_INTEGRATIONS_OPENROUTER_BASE_URL &&
    process.env.AI_INTEGRATIONS_OPENROUTER_API_KEY
  );
}

const openrouter = new OpenAI({
  baseURL: process.env.AI_INTEGRATIONS_OPENROUTER_BASE_URL,
  apiKey: process.env.AI_INTEGRATIONS_OPENROUTER_API_KEY,
});

export const DEFAULT_MODEL = "openai/gpt-5.4";

export interface SpeakerCandidates {
  [speaker: string]: number;
}

export interface LLMSegment {
  type: "spoken" | "narration";
  text: string;
  speaker_candidates?: SpeakerCandidates;
  emotion?: {
    label: string;
    score: number;
  };
  sentiment?: {
    label: string;
    score: number;
  };
}

export interface LLMChunk {
  chunk_id: number;
  approx_duration_seconds: number;
  segments: LLMSegment[];
}

export interface LLMParseResult {
  characters: string[];
  chunks: LLMChunk[];
}

export interface SpeakerSegment {
  text: string;
  type: "dialogue" | "narration";
  speaker: string | null;
  speakerCandidates: SpeakerCandidates | null;
  needsReview: boolean;
  sentiment: { label: string; score: number } | null;
  chunkId: number;
  approxDurationSeconds: number;
}

export interface ParsedTextResult {
  segments: SpeakerSegment[];
  detectedSpeakers: string[];
}

function needsReview(candidates: SpeakerCandidates | undefined): boolean {
  if (!candidates) return false;
  const scores = Object.values(candidates);
  if (scores.length < 2) return false;
  
  scores.sort((a, b) => b - a);
  const topScore = scores[0];
  const secondScore = scores[1];
  
  return (topScore - secondScore) < 0.3;
}

function getMostLikelySpeaker(candidates: SpeakerCandidates | undefined): string | null {
  if (!candidates) return null;
  const entries = Object.entries(candidates);
  if (entries.length === 0) return null;
  
  entries.sort((a, b) => b[1] - a[1]);
  return entries[0][0];
}

const TARGET_CHUNK_WORDS = 30;
const MAX_CHUNK_WORDS = 40;

function rechunkSegmentText(text: string): string[] {
  const words = text.split(/\s+/).filter(w => w.length > 0);
  if (words.length <= MAX_CHUNK_WORDS) {
    return [text];
  }
  
  const chunks: string[] = [];
  let remaining = text.trim();
  
  while (remaining.trim()) {
    const wordCount = remaining.split(/\s+/).filter(w => w.length > 0).length;
    if (wordCount <= MAX_CHUNK_WORDS) {
      chunks.push(remaining.trim());
      break;
    }
    
    const targetCharPos = wordsToCharPos(remaining, TARGET_CHUNK_WORDS);
    let splitPos = findBestSplit(remaining, targetCharPos);
    
    if (splitPos <= 0 || splitPos >= remaining.length - 1) {
      splitPos = targetCharPos;
      const spacePos = remaining.lastIndexOf(' ', splitPos);
      if (spacePos > 0) {
        splitPos = spacePos;
      }
    }
    
    const chunk = remaining.substring(0, splitPos).trim();
    remaining = remaining.substring(splitPos).trim();
    
    if (chunk) {
      chunks.push(chunk);
    }
  }
  
  return chunks.length > 0 ? chunks : [text];
}

function wordsToCharPos(text: string, wordCount: number): number {
  const words = text.split(/\s+/).filter(w => w.length > 0);
  if (wordCount >= words.length) return text.length;
  
  let currentWord = 0;
  let inWord = false;
  for (let i = 0; i < text.length; i++) {
    const isSpace = /\s/.test(text[i]);
    if (isSpace && inWord) {
      currentWord++;
      inWord = false;
      if (currentWord >= wordCount) return i;
    } else if (!isSpace) {
      inWord = true;
    }
  }
  
  const avgChars = text.length / Math.max(1, words.length);
  return Math.floor(wordCount * avgChars);
}

function findBestSplit(text: string, targetPos: number): number {
  const searchStart = Math.max(0, targetPos - 100);
  const searchEnd = Math.min(text.length, targetPos + 50);
  const region = text.substring(searchStart, searchEnd);
  
  const patterns: [RegExp, 'last' | 'mid'][] = [
    [/[.!?]\s+/g, 'last'],
    [/[:;]\s+/g, 'mid'],
    [/,\s+/g, 'mid'],
  ];
  
  for (const [pattern, strategy] of patterns) {
    const matches: RegExpExecArray[] = [];
    let m;
    while ((m = pattern.exec(region)) !== null) {
      matches.push(m);
    }
    if (matches.length > 0) {
      const best = strategy === 'last'
        ? matches[matches.length - 1]
        : matches.reduce((a, b) => 
            Math.abs(a.index + a[0].length - region.length / 2) < Math.abs(b.index + b[0].length - region.length / 2) ? a : b
          );
      return searchStart + best.index + best[0].length;
    }
  }
  
  const conjPattern = /\s+(and|but|or|yet|so|for|nor|because|though|while)\s+/gi;
  const conjMatches: RegExpExecArray[] = [];
  let cm;
  while ((cm = conjPattern.exec(region)) !== null) {
    conjMatches.push(cm);
  }
  if (conjMatches.length > 0) {
    const best = conjMatches.reduce((a, b) =>
      Math.abs(a.index - region.length / 2) < Math.abs(b.index - region.length / 2) ? a : b
    );
    return searchStart + best.index;
  }
  
  const spacePattern = /\s+/g;
  const spaceMatches: RegExpExecArray[] = [];
  let sm;
  while ((sm = spacePattern.exec(region)) !== null) {
    spaceMatches.push(sm);
  }
  if (spaceMatches.length > 0) {
    const best = spaceMatches.reduce((a, b) =>
      Math.abs(a.index - region.length / 2) < Math.abs(b.index - region.length / 2) ? a : b
    );
    return searchStart + best.index;
  }
  
  return targetPos;
}

function normalizeEmotion(emotion: { label: string; score: number } | null | undefined): { label: string; score: number } | null {
  if (!emotion) return null;
  const validSet = new Set<string>(VALID_EMOTIONS);
  if (validSet.has(emotion.label)) return emotion;
  return { label: "neutral", score: emotion.score };
}

const PASS2_SPLIT_PROMPT = `You are splitting a single long sentence into 2-3 shorter segments for a text-to-speech engine.

Split this text at natural conjunction or preposition boundaries (and, but, or, so, yet, because, though, while, in, on, at, with, from, to, through, across, before, after, etc.). Each sub-segment should read naturally when spoken aloud.

RULES:
- Split into 2-3 segments only
- Split ONLY at conjunction or preposition boundaries
- Preserve the EXACT original text — do not paraphrase, summarize, or omit words
- Every word from the input must appear in exactly one output segment

Return JSON in this format:
{
  "segments": [
    {"text": "first part of the sentence"},
    {"text": "second part of the sentence"}
  ]
}`;

const PASS2_WORD_THRESHOLD = 40;

async function splitOverlengthSegments(chunks: LLMChunk[], model: string): Promise<LLMChunk[]> {
  const result: LLMChunk[] = [];
  
  for (const chunk of chunks) {
    const newSegments: LLMSegment[] = [];
    
    for (const seg of chunk.segments) {
      const wordCount = seg.text.split(/\s+/).filter(w => w.length > 0).length;
      
      if (wordCount <= PASS2_WORD_THRESHOLD) {
        newSegments.push(seg);
        continue;
      }
      
      try {
        const response = await openrouter.chat.completions.create({
          model,
          messages: [
            { role: "system", content: PASS2_SPLIT_PROMPT },
            { role: "user", content: `Split this text (${wordCount} words) into 2-3 segments:\n\n${seg.text}` }
          ],
          max_tokens: 2048,
          temperature: 0.1,
          response_format: { type: "json_object" },
        });
        
        const content = response.choices[0]?.message?.content;
        if (content) {
          const parsed = JSON.parse(content) as { segments: Array<{ text: string }> };
          if (parsed.segments && Array.isArray(parsed.segments) && parsed.segments.length > 1) {
            const originalWords = seg.text.split(/\s+/).filter(w => w.length > 0).join(' ').toLowerCase();
            const reconstructed = parsed.segments.map(s => s.text).join(' ').split(/\s+/).filter(w => w.length > 0).join(' ').toLowerCase();
            
            if (originalWords === reconstructed) {
              for (const subSeg of parsed.segments) {
                newSegments.push({
                  type: seg.type,
                  text: subSeg.text,
                  speaker_candidates: seg.speaker_candidates,
                  emotion: seg.emotion,
                  sentiment: seg.sentiment,
                });
              }
              continue;
            } else {
              console.warn('Pass 2 split failed integrity check — words were altered. Keeping original segment.');
            }
          }
        }
      } catch (err) {
        console.warn(`Pass 2 split failed for segment, keeping original: ${err}`);
      }
      
      newSegments.push(seg);
    }
    
    result.push({
      ...chunk,
      segments: newSegments,
    });
  }
  
  return result;
}

function convertLLMResult(result: LLMParseResult): ParsedTextResult {
  const segments: SpeakerSegment[] = [];
  
  for (const chunk of result.chunks) {
    for (const seg of chunk.segments) {
      const isSpoken = seg.type === "spoken";
      const candidates = isSpoken ? seg.speaker_candidates : null;
      const emotion = normalizeEmotion(seg.emotion ?? seg.sentiment ?? null);
      
      const subTexts = rechunkSegmentText(seg.text);
      for (const st of subTexts) {
        segments.push({
          text: st,
          type: isSpoken ? "dialogue" : "narration",
          speaker: isSpoken ? getMostLikelySpeaker(candidates ?? undefined) : null,
          speakerCandidates: candidates ?? null,
          needsReview: needsReview(candidates ?? undefined),
          sentiment: emotion,
          chunkId: chunk.chunk_id,
          approxDurationSeconds: Math.round(st.split(/\s+/).filter(w => w.length > 0).length / 2.5 * 10) / 10,
        });
      }
    }
  }
  
  return {
    segments,
    detectedSpeakers: result.characters || [],
  };
}

function splitIntoParagraphBatches(text: string, paragraphsPerBatch: number = 3): string[] {
  const paragraphs = text.split(/\n\n+/).filter(p => p.trim().length > 0);
  
  if (paragraphs.length === 0) {
    return text.trim() ? [text] : [];
  }
  
  const batches: string[] = [];
  let currentBatch: string[] = [];
  let straightQuoteCount = 0;
  let curlyQuoteBalance = 0;
  
  for (let i = 0; i < paragraphs.length; i++) {
    const para = paragraphs[i];
    currentBatch.push(para);
    
    const straightQuotes = (para.match(/"/g) || []).length;
    straightQuoteCount += straightQuotes;
    
    const curlyOpen = (para.match(/[\u201c]/g) || []).length;
    const curlyClose = (para.match(/[\u201d]/g) || []).length;
    curlyQuoteBalance += curlyOpen - curlyClose;
    
    const atBatchLimit = currentBatch.length >= paragraphsPerBatch;
    const isLastParagraph = i === paragraphs.length - 1;
    
    const straightQuotesBalanced = (straightQuoteCount % 2) === 0;
    const curlyQuotesBalanced = curlyQuoteBalance <= 0;
    const quotesBalanced = straightQuotesBalanced && curlyQuotesBalanced;
    
    const batchTooLarge = currentBatch.length >= paragraphsPerBatch * 2;
    
    if ((atBatchLimit && quotesBalanced) || isLastParagraph || batchTooLarge) {
      batches.push(currentBatch.join("\n\n"));
      currentBatch = [];
      straightQuoteCount = 0;
      curlyQuoteBalance = 0;
    }
  }
  
  if (currentBatch.length > 0) {
    batches.push(currentBatch.join("\n\n"));
  }
  
  return batches.length > 0 ? batches : [text];
}

const VALID_EMOTIONS = [
  "neutral", "happy", "sad", "angry", "fear", "disgust", "surprise",
  "excited", "calm", "anxious", "hopeful", "melancholy", "tender", "proud",
] as const;

let cachedResolvedPrompt: string | null = null;
let cachedPromptTimestamp: number = 0;
const PROMPT_CACHE_TTL_MS = 5000;

export function invalidatePromptCache(): void {
  cachedResolvedPrompt = null;
  cachedPromptTimestamp = 0;
}

async function getSystemPrompt(): Promise<string> {
  const now = Date.now();
  if (cachedResolvedPrompt !== null && (now - cachedPromptTimestamp) < PROMPT_CACHE_TTL_MS) {
    return cachedResolvedPrompt;
  }

  try {
    const resp = await fetch(`http://localhost:${process.env.PYTHON_PORT || 8000}/parsing-prompt`);
    if (resp.ok) {
      const data = await resp.json() as { prompt: string };
      if (data.prompt) {
        const resolved = data.prompt.replace(/\$\{VALID_EMOTIONS\}/g, VALID_EMOTIONS.join(", "));
        cachedResolvedPrompt = resolved;
        cachedPromptTimestamp = now;
        return resolved;
      }
    }
  } catch {
  }

  throw new Error("No parsing prompt configured. Please set one in Settings.");
}

async function parseWithConversation(
  text: string,
  model: string,
  knownSpeakers: string[]
): Promise<LLMParseResult> {
  const batches = splitIntoParagraphBatches(text, 3);
  const systemPrompt = await getSystemPrompt();
  const messages: OpenAI.Chat.ChatCompletionMessageParam[] = [
    { role: "system", content: systemPrompt }
  ];
  
  if (knownSpeakers.length > 0) {
    messages.push({
      role: "user",
      content: `Known characters in this text: ${knownSpeakers.join(", ")}. Please use these names when identifying speakers.`
    });
    messages.push({
      role: "assistant",
      content: `Understood. I'll identify speakers using these character names: ${knownSpeakers.join(", ")}.`
    });
  }
  
  const allCharacters = new Set<string>(knownSpeakers);
  const allChunks: LLMChunk[] = [];
  let nextChunkId = 1;
  
  for (let i = 0; i < batches.length; i++) {
    const batch = batches[i];
    const isFirst = i === 0;
    
    const userPrompt = isFirst
      ? `Split the following text into individual sentences and quote boundaries. Each sentence should be its own segment. Do NOT split within sentences for any reason. Start chunk IDs at ${nextChunkId}.\n\nHere is the text:\n\n${batch}`
      : `Continue splitting the next section into individual sentences and quote boundaries. Each sentence should be its own segment. Do NOT split within sentences for any reason. Continue chunk IDs from ${nextChunkId}. Use the same characters identified so far.\n\nHere is the text:\n\n${batch}`;
    
    messages.push({ role: "user", content: userPrompt });
    
    const response = await openrouter.chat.completions.create({
      model,
      messages,
      max_tokens: 8192,
      temperature: 0.1,
      response_format: { type: "json_object" },
    });
    
    const content = response.choices[0]?.message?.content;
    if (!content) {
      throw new Error(`No response from LLM for batch ${i + 1}`);
    }
    
    messages.push({ role: "assistant", content });
    
    const parsed = JSON.parse(content) as LLMParseResult;
    
    if (parsed.characters) {
      parsed.characters.forEach(c => allCharacters.add(c));
    }
    
    if (parsed.chunks && Array.isArray(parsed.chunks)) {
      for (const chunk of parsed.chunks) {
        allChunks.push(chunk);
        if (chunk.chunk_id >= nextChunkId) {
          nextChunkId = chunk.chunk_id + 1;
        }
      }
    }
  }

  const pass2Chunks = await splitOverlengthSegments(allChunks, model);
  
  return {
    characters: Array.from(allCharacters),
    chunks: pass2Chunks,
  };
}

export async function parseTextWithLLM(
  text: string,
  model: string = DEFAULT_MODEL,
  knownSpeakers: string[] = []
): Promise<ParsedTextResult> {
  if (!isOpenRouterConfigured()) {
    throw new Error("OpenRouter is not configured");
  }
  
  const result = await parseWithConversation(text, model, knownSpeakers);
  return convertLLMResult(result);
}

export interface StreamingParseUpdate {
  type: 'progress' | 'chunk' | 'complete' | 'error';
  chunkIndex?: number;
  totalChunks?: number;
  segments?: SpeakerSegment[];
  detectedSpeakers?: string[];
  error?: string;
}

export async function* parseTextWithLLMStreaming(
  text: string,
  model: string = DEFAULT_MODEL,
  knownSpeakers: string[] = []
): AsyncGenerator<StreamingParseUpdate> {
  if (!isOpenRouterConfigured()) {
    yield { type: 'error', error: 'OpenRouter is not configured' };
    return;
  }

  const batches = splitIntoParagraphBatches(text, 3);
  const totalBatches = batches.length;
  
  yield { type: 'progress', chunkIndex: 0, totalChunks: totalBatches };
  
  const systemPrompt = await getSystemPrompt();
  const messages: OpenAI.Chat.ChatCompletionMessageParam[] = [
    { role: "system", content: systemPrompt }
  ];
  
  if (knownSpeakers.length > 0) {
    messages.push({
      role: "user",
      content: `Known characters in this text: ${knownSpeakers.join(", ")}. Please use these names when identifying speakers.`
    });
    messages.push({
      role: "assistant",
      content: `Understood. I'll identify speakers using these character names: ${knownSpeakers.join(", ")}.`
    });
  }
  
  const allCharacters = new Set<string>(knownSpeakers);
  let nextChunkId = 1;
  
  for (let i = 0; i < batches.length; i++) {
    const batch = batches[i];
    const isFirst = i === 0;
    
    const userPrompt = isFirst
      ? `Split the following text into individual sentences and quote boundaries. Each sentence should be its own segment. Do NOT split within sentences for any reason. Start chunk IDs at ${nextChunkId}.\n\nHere is the text:\n\n${batch}`
      : `Continue splitting the next section into individual sentences and quote boundaries. Each sentence should be its own segment. Do NOT split within sentences for any reason. Continue chunk IDs from ${nextChunkId}. Use the same characters identified so far.\n\nHere is the text:\n\n${batch}`;
    
    messages.push({ role: "user", content: userPrompt });
    
    try {
      const response = await openrouter.chat.completions.create({
        model,
        messages,
        max_tokens: 8192,
        temperature: 0.1,
        response_format: { type: "json_object" },
      });
      
      const content = response.choices[0]?.message?.content;
      if (!content) {
        throw new Error(`No response from LLM for batch ${i + 1}`);
      }
      
      messages.push({ role: "assistant", content });
      
      const parsed = JSON.parse(content) as LLMParseResult;
      
      if (parsed.characters) {
        parsed.characters.forEach(c => allCharacters.add(c));
      }
      
      const batchSegments: SpeakerSegment[] = [];
      if (parsed.chunks && Array.isArray(parsed.chunks)) {
        const pass2Chunks = await splitOverlengthSegments(parsed.chunks, model);
        for (const chunk of pass2Chunks) {
          if (chunk.chunk_id >= nextChunkId) {
            nextChunkId = chunk.chunk_id + 1;
          }
          
          for (const seg of chunk.segments) {
            const isSpoken = seg.type === "spoken";
            const candidates = isSpoken ? seg.speaker_candidates : null;
            const emotion = normalizeEmotion(seg.emotion ?? seg.sentiment ?? null);
            
            const subTexts = rechunkSegmentText(seg.text);
            for (const st of subTexts) {
              batchSegments.push({
                text: st,
                type: isSpoken ? "dialogue" : "narration",
                speaker: isSpoken ? getMostLikelySpeaker(candidates ?? undefined) : null,
                speakerCandidates: candidates ?? null,
                needsReview: needsReview(candidates ?? undefined),
                sentiment: emotion,
                chunkId: chunk.chunk_id,
                approxDurationSeconds: Math.round(st.split(/\s+/).filter(w => w.length > 0).length / 2.5 * 10) / 10,
              });
            }
          }
        }
      }
      
      yield {
        type: 'chunk',
        chunkIndex: i + 1,
        totalChunks: totalBatches,
        segments: batchSegments,
        detectedSpeakers: Array.from(allCharacters),
      };
      
    } catch (error) {
      yield { 
        type: 'error', 
        error: error instanceof Error ? error.message : 'Unknown error',
        chunkIndex: i + 1,
        totalChunks: totalBatches
      };
      return;
    }
  }
  
  yield { 
    type: 'complete',
    chunkIndex: totalBatches,
    totalChunks: totalBatches,
    detectedSpeakers: Array.from(allCharacters)
  };
}

export async function getAvailableModels(): Promise<string[]> {
  return [
    "openai/gpt-5.4",
    "openai/gpt-5.3",
    "openai/gpt-4.1",
    "openai/gpt-4.1-mini",
    "openai/gpt-4.1-nano",
    "meta-llama/llama-3.3-70b-instruct",
    "meta-llama/llama-3.1-8b-instruct",
    "mistralai/mistral-7b-instruct",
    "qwen/qwen-2.5-72b-instruct",
    "deepseek/deepseek-chat",
  ];
}

export { openrouter };
