"""
TTS Service - Text-to-Speech generation using Chatterbox or synthesized fallback
"""

import os
import numpy as np
import logging
from pathlib import Path
from typing import Optional

from models import TextSegment, ProjectConfig, Sentiment
from audio_processor import AudioProcessor

logger = logging.getLogger(__name__)

CHATTERBOX_AVAILABLE = False
try:
    from chatterbox.tts import ChatterboxTTS
    import torch
    if torch.cuda.is_available():
        CHATTERBOX_AVAILABLE = True
        logger.info("Chatterbox TTS with CUDA is available")
    else:
        logger.warning("Chatterbox requires CUDA, using synthesized audio fallback")
except ImportError:
    logger.warning("Chatterbox TTS not installed, using synthesized audio fallback")


class TTSService:
    """
    Text-to-Speech service that uses Chatterbox when GPU available,
    or uses synthesized placeholder audio for demonstration.
    The synthesized audio applies sentiment-based prosody adjustments.
    """
    
    def __init__(self):
        self.model = None
        self.sample_rate = 24000
        
        if CHATTERBOX_AVAILABLE:
            try:
                self.model = ChatterboxTTS.from_pretrained(device="cuda")
                logger.info("Loaded Chatterbox TTS on CUDA")
            except Exception as e:
                logger.warning(f"Failed to load Chatterbox: {e}")
    
    def generate_audiobook(
        self,
        segments: list[TextSegment],
        config: ProjectConfig,
        voice_files: dict[str, str],
        output_path: str,
        audio_processor: AudioProcessor,
    ):
        """
        Generate complete audiobook from text segments.
        Applies sentiment-based prosody adjustments (pitch, speed) to each segment.
        
        Args:
            segments: Parsed text segments with sentiment
            config: Project configuration (voices, exaggeration, etc.)
            voice_files: Mapping of voice_id to file path
            output_path: Path to save the final audio
            audio_processor: Audio processor for effects
        """
        audio_chunks = []
        
        for i, segment in enumerate(segments):
            logger.info(f"Processing segment {i+1}/{len(segments)}: {segment.type} - '{segment.text[:50]}...'")
            
            voice_id = None
            pitch_offset = 0.0
            speed_factor = 1.0
            
            if segment.type == "dialogue" and segment.speaker:
                speaker_config = config.speakers.get(segment.speaker)
                if speaker_config:
                    voice_id = speaker_config.voiceSampleId
                    pitch_offset = speaker_config.pitchOffset
                    speed_factor = speaker_config.speedFactor
            else:
                voice_id = config.narratorVoiceId
            
            voice_path = voice_files.get(voice_id) if voice_id else None
            
            audio = self._generate_segment_audio(
                text=segment.text,
                voice_path=voice_path,
                exaggeration=config.defaultExaggeration,
            )
            
            if segment.sentiment:
                logger.info(f"  Applying prosody for sentiment: {segment.sentiment.label} (score: {segment.sentiment.score:.2f})")
                audio = audio_processor.apply_sentiment_prosody(
                    audio_data=audio,
                    sample_rate=self.sample_rate,
                    sentiment_label=segment.sentiment.label,
                    sentiment_score=segment.sentiment.score,
                    base_pitch_offset=pitch_offset,
                    base_speed_factor=speed_factor,
                )
            elif pitch_offset != 0 or speed_factor != 1.0:
                if pitch_offset != 0:
                    audio = audio_processor.apply_pitch_shift(audio, self.sample_rate, pitch_offset)
                if speed_factor != 1.0:
                    audio = audio_processor.apply_time_stretch(audio, self.sample_rate, speed_factor)
            
            audio_chunks.append(audio)
        
        logger.info(f"Concatenating {len(audio_chunks)} audio chunks with {config.pauseBetweenSegments}ms pauses")
        final_audio = audio_processor.concatenate_audio(
            audio_chunks,
            self.sample_rate,
            config.pauseBetweenSegments,
        )
        
        final_audio = audio_processor.normalize_audio(final_audio)
        
        audio_processor.save_audio(output_path, final_audio, self.sample_rate)
        logger.info(f"Saved audiobook to {output_path} ({len(final_audio) / self.sample_rate:.1f} seconds)")
    
    def _generate_segment_audio(
        self,
        text: str,
        voice_path: Optional[str] = None,
        exaggeration: float = 0.5,
    ) -> np.ndarray:
        """
        Generate audio for a single text segment.
        Uses Chatterbox if available with GPU, otherwise synthesized fallback.
        """
        if self.model is not None and voice_path:
            try:
                import torchaudio as ta
                wav = self.model.generate(
                    text,
                    audio_prompt_path=voice_path,
                    exaggeration=exaggeration,
                )
                return wav.numpy().flatten()
            except Exception as e:
                logger.warning(f"Chatterbox generation failed: {e}, using synthesized fallback")
        
        return self._synthesize_audio_from_text(text, exaggeration)
    
    def _synthesize_audio_from_text(self, text: str, exaggeration: float = 0.5) -> np.ndarray:
        """
        Generate synthesized audio that represents speech.
        Creates a more speech-like waveform with:
        - Formant-like frequencies based on text
        - Natural envelope for syllables
        - Slight randomness for organic feel
        """
        words = text.split()
        if not words:
            return np.zeros(int(self.sample_rate * 0.5), dtype=np.float32)
        
        syllables_per_word = 1.5
        duration_per_syllable = 0.15
        total_syllables = len(words) * syllables_per_word
        total_duration = total_syllables * duration_per_syllable
        total_duration = max(0.5, min(45.0, total_duration))
        
        num_samples = int(self.sample_rate * total_duration)
        audio = np.zeros(num_samples, dtype=np.float32)
        
        base_f0 = 120 + exaggeration * 40
        
        samples_per_word = num_samples // max(1, len(words))
        word_gap_samples = int(self.sample_rate * 0.05)
        
        for i, word in enumerate(words[:200]):
            start_idx = i * samples_per_word
            end_idx = min(start_idx + samples_per_word - word_gap_samples, num_samples)
            
            if start_idx >= num_samples:
                break
            
            word_samples = end_idx - start_idx
            if word_samples <= 0:
                continue
            
            t = np.linspace(0, word_samples / self.sample_rate, word_samples)
            
            f0_variation = 0.9 + 0.2 * np.random.random()
            f0 = base_f0 * f0_variation
            
            if word.endswith('?'):
                f0 *= 1.15
            elif word.endswith('!'):
                f0 *= 1.1
            
            formant1 = f0
            formant2 = f0 * 2.5 + np.random.random() * 100
            formant3 = f0 * 4 + np.random.random() * 200
            
            wave = 0.4 * np.sin(2 * np.pi * formant1 * t)
            wave += 0.25 * np.sin(2 * np.pi * formant2 * t)
            wave += 0.1 * np.sin(2 * np.pi * formant3 * t)
            
            envelope = np.ones(word_samples)
            attack = int(word_samples * 0.1)
            release = int(word_samples * 0.2)
            envelope[:attack] = np.linspace(0, 1, attack)
            envelope[-release:] = np.linspace(1, 0, release)
            
            wave *= envelope
            
            noise = np.random.randn(word_samples) * 0.02
            wave += noise
            
            audio[start_idx:end_idx] += wave.astype(np.float32)
        
        max_val = np.max(np.abs(audio))
        if max_val > 0:
            audio = audio / max_val * 0.7
        
        return audio
