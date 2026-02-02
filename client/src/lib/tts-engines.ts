import type { TTSEngine } from "@shared/schema";

export interface TTSEngineConfig {
  id: TTSEngine;
  label: string;
  name: string;
  description: string;
  badge?: string;
  badgeVariant?: "default" | "secondary" | "destructive" | "outline";
  supportsVoiceCloning: boolean;
  requiresApiKey: boolean;
  isLocal: boolean;
}

export const TTS_ENGINES: TTSEngineConfig[] = [
  {
    id: "edge-tts",
    label: "Edge TTS (Recommended)",
    name: "Edge TTS (Azure Neural)",
    description: "47 English neural voices, free, high quality",
    badge: "Recommended",
    badgeVariant: "default",
    supportsVoiceCloning: false,
    requiresApiKey: false,
    isLocal: false,
  },
  {
    id: "openai",
    label: "OpenAI TTS",
    name: "OpenAI TTS",
    description: "6 premium voices, requires API key",
    badge: "API Key",
    badgeVariant: "secondary",
    supportsVoiceCloning: false,
    requiresApiKey: true,
    isLocal: false,
  },
  {
    id: "chatterbox-free",
    label: "Chatterbox Free",
    name: "Chatterbox Free (HuggingFace)",
    description: "Voice cloning via free HuggingFace Spaces, 300 char limit",
    badge: "Free",
    badgeVariant: "outline",
    supportsVoiceCloning: true,
    requiresApiKey: false,
    isLocal: false,
  },
  {
    id: "hf-tts-paid",
    label: "HuggingFace TTS Paid",
    name: "HuggingFace TTS Paid",
    description: "Multi-model voice cloning (Qwen3, Chatterbox, XTTS, StyleTTS2)",
    badge: "API Key",
    badgeVariant: "secondary",
    supportsVoiceCloning: true,
    requiresApiKey: true,
    isLocal: false,
  },
  {
    id: "styletts2",
    label: "StyleTTS2 (Expressive)",
    name: "StyleTTS2 (Expressive)",
    description: "Expressive TTS with emotion control via HuggingFace Space",
    badge: "Free",
    badgeVariant: "outline",
    supportsVoiceCloning: true,
    requiresApiKey: false,
    isLocal: false,
  },
  {
    id: "piper",
    label: "Piper TTS",
    name: "Piper TTS",
    description: "Fast open source TTS, many voices",
    badge: "Local",
    badgeVariant: "outline",
    supportsVoiceCloning: false,
    requiresApiKey: false,
    isLocal: true,
  },
  {
    id: "soprano",
    label: "Soprano TTS",
    name: "Soprano TTS (80M)",
    description: "Ultra-fast local TTS, 2000x real-time on GPU",
    badge: "Local",
    badgeVariant: "default",
    supportsVoiceCloning: false,
    requiresApiKey: false,
    isLocal: true,
  },
];

export function getTTSEngine(id: TTSEngine): TTSEngineConfig | undefined {
  return TTS_ENGINES.find(e => e.id === id);
}

export function isVoiceCloningEngine(id: TTSEngine): boolean {
  const engine = getTTSEngine(id);
  return engine?.supportsVoiceCloning ?? false;
}

export function getVoiceCloningEngines(): TTSEngineConfig[] {
  return TTS_ENGINES.filter(e => e.supportsVoiceCloning);
}

export function getLocalEngines(): TTSEngineConfig[] {
  return TTS_ENGINES.filter(e => e.isLocal);
}
