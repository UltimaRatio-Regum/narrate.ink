"""
Configuration for Chatterbox TTS paid API.
Update these settings when using a custom Chatterbox endpoint.
"""
import os

# Chatterbox Paid API Configuration (HuggingFace Space via Gradio)
CHATTERBOX_PAID_CONFIG = {
    # HuggingFace Space URL for the paid Chatterbox service
    # Default points to user's custom Docker-based Space (no GPU quota limits)
    "space_url": os.environ.get("CHATTERBOX_API_URL", "https://cherithcutestory-chatterbox-docker.hf.space"),
    
    # API key for authentication (optional, for private spaces)
    "api_key": os.environ.get("CHATTERBOX_API_KEY", ""),
    
    # Request timeout in seconds (300s = 5 min default for TTS generation)
    "timeout": int(os.environ.get("CHATTERBOX_TIMEOUT", "300")),
    
    # Maximum characters per request (0 = no limit)
    "max_chars": int(os.environ.get("CHATTERBOX_MAX_CHARS", "0")),
    
    # Default parameters
    "default_exaggeration": 0.5,
    "default_temperature": 0.8,
    "default_cfg_weight": 0.5,
    
    # Multi-model support (qwen3, chatterbox, etc.)
    "model": os.environ.get("CHATTERBOX_MODEL", "qwen3"),
    "language": os.environ.get("CHATTERBOX_LANGUAGE", "English"),
    
    # Qwen-specific parameters
    "qwen_model_id": os.environ.get("CHATTERBOX_QWEN_MODEL_ID", "Qwen/Qwen3-TTS-12Hz-0.6B-Base"),
    "qwen_x_vector_only_mode": os.environ.get("CHATTERBOX_QWEN_X_VECTOR_ONLY", "false").lower() == "true",
}

# Free HuggingFace Spaces configuration
CHATTERBOX_FREE_CONFIG = {
    # HuggingFace Spaces endpoint
    "space_id": "ResembleAI/Chatterbox",
    
    # Character limit for free tier
    "max_chars": 300,
    
    # Default parameters
    "default_exaggeration": 0.5,
    "default_temperature": 0.8,
    "default_cfg_weight": 0.5,
}


def is_paid_chatterbox_configured() -> bool:
    """Check if paid Chatterbox API is properly configured."""
    # Only requires space_url to be set (api_key is optional for public spaces)
    return bool(CHATTERBOX_PAID_CONFIG["space_url"])


def get_chatterbox_config(use_paid: bool = False) -> dict:
    """Get the appropriate Chatterbox configuration."""
    if use_paid:
        return CHATTERBOX_PAID_CONFIG
    return CHATTERBOX_FREE_CONFIG
