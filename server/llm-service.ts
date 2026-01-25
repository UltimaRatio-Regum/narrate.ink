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

export interface SpeakerSegment {
  text: string;
  type: "dialogue" | "narration";
  speaker: string | null;
}

export interface ParsedTextResult {
  segments: SpeakerSegment[];
  detectedSpeakers: string[];
}

export async function parseTextWithLLM(
  text: string,
  model: string = "meta-llama/llama-3.3-70b-instruct"
): Promise<ParsedTextResult> {
  if (!isOpenRouterConfigured()) {
    throw new Error("OpenRouter is not configured");
  }

  const systemPrompt = `You are an expert text analyzer for audiobook production. Your task is to parse narrative text and identify:
1. Dialogue sections (text within quotes that is spoken by a character)
2. Narration sections (descriptive text not spoken by characters)
3. The speaker of each dialogue section

Rules:
- Dialogue is ONLY text within quotation marks (straight " or curly "")
- The speaker is typically mentioned before or after the dialogue (e.g., "Hello," said John)
- If no speaker is clearly identified, use null
- Preserve the exact text content including quotes
- Include ALL text - both dialogue and narration

Return a JSON object with this structure:
{
  "segments": [
    {"text": "exact text content", "type": "dialogue" or "narration", "speaker": "Name" or null}
  ],
  "detectedSpeakers": ["list of all unique speaker names found"]
}

Important: The segments should cover the ENTIRE input text in order, with no gaps or overlaps.`;

  const userPrompt = `Parse the following text into dialogue and narration segments, identifying speakers:

${text}`;

  const response = await openrouter.chat.completions.create({
    model,
    messages: [
      { role: "system", content: systemPrompt },
      { role: "user", content: userPrompt },
    ],
    max_tokens: 8192,
    temperature: 0.1,
    response_format: { type: "json_object" },
  });

  const content = response.choices[0]?.message?.content;
  if (!content) {
    throw new Error("No response from LLM");
  }

  const parsed = JSON.parse(content) as ParsedTextResult;
  
  if (!Array.isArray(parsed.segments)) {
    throw new Error("Invalid response format: segments not an array");
  }
  
  if (!Array.isArray(parsed.detectedSpeakers)) {
    parsed.detectedSpeakers = [];
  }

  return parsed;
}

export async function getAvailableModels(): Promise<string[]> {
  return [
    "meta-llama/llama-3.3-70b-instruct",
    "meta-llama/llama-3.1-8b-instruct",
    "mistralai/mistral-7b-instruct",
    "qwen/qwen-2.5-72b-instruct",
    "deepseek/deepseek-chat",
  ];
}

export { openrouter };
