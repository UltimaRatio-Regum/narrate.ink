export const LLM_MODELS = [
  { id: "openai/gpt-5.4", name: "ChatGPT 5.4" },
  { id: "openai/gpt-5.3", name: "ChatGPT 5.3" },
  { id: "openai/gpt-4.1", name: "GPT-4.1" },
  { id: "openai/gpt-4.1-mini", name: "GPT-4.1 Mini" },
  { id: "openai/gpt-4.1-nano", name: "GPT-4.1 Nano" },
  { id: "meta-llama/llama-3.3-70b-instruct", name: "Llama 3.3 70B" },
  { id: "meta-llama/llama-3.1-8b-instruct", name: "Llama 3.1 8B" },
  { id: "mistralai/mistral-7b-instruct", name: "Mistral 7B" },
  { id: "qwen/qwen-2.5-72b-instruct", name: "Qwen 2.5 72B" },
  { id: "deepseek/deepseek-chat", name: "DeepSeek Chat" },
];

export const DEFAULT_MODEL = LLM_MODELS.find(m => m.id === "openai/gpt-4.1-mini") || LLM_MODELS[0];
