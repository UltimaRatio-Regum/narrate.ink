"""
Audio Processor - Handles pitch shifting, speed changes, and audio manipulation
"""

import numpy as np
import soundfile as sf
from pathlib import Path
from typing import Optional

try:
    import pyrubberband as pyrb
    PYRUBBERBAND_AVAILABLE = True
except ImportError:
    PYRUBBERBAND_AVAILABLE = False


class AudioProcessor:
    """
    Processes audio files with pitch and speed adjustments
    based on sentiment analysis using pyrubberband.
    """
    
    SENTIMENT_PITCH_MAP = {
        "positive": 0.5,
        "negative": -0.5,
        "neutral": 0,
        "excited": 1.5,
        "sad": -1.0,
        "angry": 0.5,
        "fearful": 1.0,
    }
    
    SENTIMENT_SPEED_MAP = {
        "positive": 1.05,
        "negative": 0.95,
        "neutral": 1.0,
        "excited": 1.15,
        "sad": 0.85,
        "angry": 1.1,
        "fearful": 1.2,
    }
    
    def get_audio_duration(self, file_path: str) -> float:
        """Get the duration of an audio file in seconds."""
        try:
            info = sf.info(file_path)
            return info.duration
        except Exception:
            return 0.0
    
    def load_audio(self, file_path: str) -> tuple[np.ndarray, int]:
        """Load audio file and return (data, sample_rate)."""
        data, sr = sf.read(file_path)
        return data, sr
    
    def save_audio(self, file_path: str, data: np.ndarray, sample_rate: int):
        """Save audio data to file."""
        sf.write(file_path, data, sample_rate)
    
    def apply_sentiment_prosody(
        self,
        audio_data: np.ndarray,
        sample_rate: int,
        sentiment_label: str,
        sentiment_score: float = 0.5,
        base_pitch_offset: float = 0,
        base_speed_factor: float = 1.0,
    ) -> np.ndarray:
        """
        Apply pitch and speed changes based on sentiment.
        
        Args:
            audio_data: Audio samples as numpy array
            sample_rate: Sample rate in Hz
            sentiment_label: Detected sentiment (positive, negative, etc.)
            sentiment_score: Confidence of sentiment (0-1)
            base_pitch_offset: Additional pitch offset in semitones
            base_speed_factor: Additional speed multiplier
            
        Returns:
            Processed audio data
        """
        if not PYRUBBERBAND_AVAILABLE:
            return audio_data
        
        pitch_offset = self.SENTIMENT_PITCH_MAP.get(sentiment_label, 0) * sentiment_score
        pitch_offset += base_pitch_offset
        
        speed_factor = self.SENTIMENT_SPEED_MAP.get(sentiment_label, 1.0)
        speed_factor = 1.0 + (speed_factor - 1.0) * sentiment_score
        speed_factor *= base_speed_factor
        
        speed_factor = max(0.5, min(2.0, speed_factor))
        pitch_offset = max(-12, min(12, pitch_offset))
        
        processed = audio_data
        
        if abs(speed_factor - 1.0) > 0.01:
            processed = pyrb.time_stretch(processed, sample_rate, speed_factor)
        
        if abs(pitch_offset) > 0.1:
            processed = pyrb.pitch_shift(processed, sample_rate, pitch_offset)
        
        return processed
    
    def apply_pitch_shift(
        self,
        audio_data: np.ndarray,
        sample_rate: int,
        semitones: float,
    ) -> np.ndarray:
        """Apply pitch shift in semitones."""
        if not PYRUBBERBAND_AVAILABLE or abs(semitones) < 0.1:
            return audio_data
        return pyrb.pitch_shift(audio_data, sample_rate, semitones)
    
    def apply_time_stretch(
        self,
        audio_data: np.ndarray,
        sample_rate: int,
        factor: float,
    ) -> np.ndarray:
        """Apply time stretch (speed change without pitch change)."""
        if not PYRUBBERBAND_AVAILABLE or abs(factor - 1.0) < 0.01:
            return audio_data
        factor = max(0.5, min(2.0, factor))
        return pyrb.time_stretch(audio_data, sample_rate, factor)
    
    def concatenate_audio(
        self,
        audio_chunks: list[np.ndarray],
        sample_rate: int,
        pause_duration_ms: int = 500,
    ) -> np.ndarray:
        """
        Concatenate audio chunks with pauses between them.
        
        Args:
            audio_chunks: List of audio data arrays
            sample_rate: Sample rate in Hz
            pause_duration_ms: Pause between chunks in milliseconds
        """
        if not audio_chunks:
            return np.array([], dtype=np.float32)
        
        pause_samples = int(sample_rate * pause_duration_ms / 1000)
        pause = np.zeros(pause_samples, dtype=np.float32)
        
        result_parts = []
        for i, chunk in enumerate(audio_chunks):
            if len(chunk.shape) > 1:
                chunk = np.mean(chunk, axis=1)
            
            result_parts.append(chunk.astype(np.float32))
            
            if i < len(audio_chunks) - 1:
                result_parts.append(pause)
        
        return np.concatenate(result_parts)
    
    def normalize_audio(
        self,
        audio_data: np.ndarray,
        target_db: float = -3.0,
    ) -> np.ndarray:
        """Normalize audio to target dB level."""
        if len(audio_data) == 0:
            return audio_data
        
        peak = np.max(np.abs(audio_data))
        if peak < 1e-10:
            return audio_data
        
        target_amplitude = 10 ** (target_db / 20)
        normalized = audio_data * (target_amplitude / peak)
        
        return normalized
    
    def create_silence(self, sample_rate: int, duration_ms: int) -> np.ndarray:
        """Create silence of specified duration."""
        num_samples = int(sample_rate * duration_ms / 1000)
        return np.zeros(num_samples, dtype=np.float32)
