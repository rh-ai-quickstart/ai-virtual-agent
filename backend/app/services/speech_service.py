"""
Speech recognition service using OpenAI Whisper.
"""

import asyncio
import logging
import os
import re
from typing import Dict, List, Optional, Any
import functools

logger = logging.getLogger(__name__)

# Lazy imports to avoid startup issues if dependencies aren't available
_whisper = None
_torch = None


def _get_whisper():
    """Lazily import whisper to avoid import-time dependencies."""
    global _whisper
    if _whisper is None:
        try:
            import whisper
            _whisper = whisper
        except ImportError as e:
            logger.error("OpenAI Whisper not available. Install with: pip install openai-whisper")
            raise ImportError("OpenAI Whisper is required for speech recognition") from e
    return _whisper


def _get_torch():
    """Lazily import torch to check for GPU availability."""
    global _torch
    if _torch is None:
        try:
            import torch
            _torch = torch
        except ImportError:
            logger.warning("PyTorch not available. Using CPU-only mode.")
            _torch = None
    return _torch


class SpeechService:
    """Service for handling speech-to-text operations using OpenAI Whisper."""

    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize the speech service.

        Args:
            model_name: Whisper model to use. Options: tiny, base, small, medium, large, turbo
                       Defaults to 'base' for good balance of speed and accuracy.
        """
        self.model_name = model_name or os.getenv("WHISPER_MODEL", "base")
        self.model = None
        self.device = "cpu"
        self._initialized = False

    def _segment_into_sentences(self, text: str, segments: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Segment transcribed text into individual sentences with timing information.

        Args:
            text: The full transcribed text
            segments: Optional Whisper segments with word-level timing

        Returns:
            List of sentence dictionaries with text, start_time, end_time, and confidence
        """
        # Simple sentence boundary detection using regex
        sentence_endings = re.compile(r'[.!?]+\s*')
        sentences = []

        if not text.strip():
            return sentences

        # Split text into sentences
        sentence_parts = sentence_endings.split(text.strip())
        sentence_parts = [s.strip() for s in sentence_parts if s.strip()]

        if not sentence_parts:
            # If no sentence boundaries found, treat the whole text as one sentence
            sentence_parts = [text.strip()]

        # If we have Whisper segments with timing information, try to map sentences to timing
        if segments:
            current_char_pos = 0
            segment_idx = 0

            for i, sentence_text in enumerate(sentence_parts):
                sentence_start_char = text.find(sentence_text, current_char_pos)
                sentence_end_char = sentence_start_char + len(sentence_text)

                # Find the segments that contain this sentence
                sentence_start_time = None
                sentence_end_time = None
                sentence_confidences = []

                for segment in segments:
                    segment_text = segment.get('text', '').strip()
                    segment_start = segment.get('start', 0)
                    segment_end = segment.get('end', 0)

                    # Check if this segment overlaps with our sentence
                    if segment_text and sentence_text.lower().find(segment_text.lower()) != -1:
                        if sentence_start_time is None:
                            sentence_start_time = segment_start
                        sentence_end_time = segment_end

                        # Collect confidence scores if available
                        if 'avg_logprob' in segment:
                            import math
                            confidence = math.exp(segment['avg_logprob'])
                            sentence_confidences.append(confidence)

                # Calculate average confidence for the sentence
                avg_confidence = None
                if sentence_confidences:
                    avg_confidence = sum(sentence_confidences) / len(sentence_confidences)

                sentences.append({
                    'text': sentence_text,
                    'start_time': sentence_start_time,
                    'end_time': sentence_end_time,
                    'confidence': avg_confidence,
                    'index': i
                })

                current_char_pos = sentence_end_char
        else:
            # No timing information available, just return sentences with text
            for i, sentence_text in enumerate(sentence_parts):
                sentences.append({
                    'text': sentence_text,
                    'start_time': None,
                    'end_time': None,
                    'confidence': None,
                    'index': i
                })

        return sentences

    async def _initialize(self):
        """Initialize the Whisper model if not already done."""
        if self._initialized:
            return

        try:
            whisper = _get_whisper()
            torch = _get_torch()

            # Determine device
            if torch and torch.cuda.is_available():
                self.device = "cuda"
                logger.info("Using GPU for speech recognition")
            else:
                self.device = "cpu"
                logger.info("Using CPU for speech recognition")

            # Load model in a thread to avoid blocking
            logger.info(f"Loading Whisper model '{self.model_name}' on {self.device}")
            loop = asyncio.get_event_loop()
            self.model = await loop.run_in_executor(
                None,
                functools.partial(whisper.load_model, self.model_name, device=self.device)
            )

            self._initialized = True
            logger.info(f"Whisper model '{self.model_name}' loaded successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Whisper model: {str(e)}")
            raise

    async def transcribe_file(self, file_path: str, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Transcribe audio file to text.

        Args:
            file_path: Path to audio file
            language: Optional language code (e.g., 'en', 'es', 'fr')

        Returns:
            Dictionary containing transcription results:
            - text: Transcribed text
            - language: Detected language
            - segments: List of segments with timestamps (if available)
        """
        await self._initialize()

        if not self.model:
            raise RuntimeError("Whisper model not initialized")

        try:
            # Run transcription in thread to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                functools.partial(
                    self.model.transcribe,
                    file_path,
                    language=language
                )
            )

            # Extract useful information
            transcription_result = {
                "text": result.get("text", "").strip(),
                "language": result.get("language"),
                "segments": result.get("segments", [])
            }

            # Calculate confidence if segments are available
            if transcription_result["segments"]:
                # Average the segment probabilities if available
                segment_probs = [
                    seg.get("avg_logprob", 0) for seg in transcription_result["segments"]
                    if "avg_logprob" in seg
                ]
                if segment_probs:
                    import math
                    # Convert log probabilities to confidence scores
                    confidences = [math.exp(prob) for prob in segment_probs]
                    transcription_result["confidence"] = sum(confidences) / len(confidences)

            # Add sentence-level segmentation
            sentences = self._segment_into_sentences(
                transcription_result["text"],
                transcription_result["segments"]
            )
            transcription_result["sentences"] = sentences

            logger.info(
                f"Transcribed {len(transcription_result['text'])} characters "
                f"in language '{transcription_result['language']}'"
            )

            return transcription_result

        except Exception as e:
            error_msg = str(e)

            # Check for common ffmpeg-related errors and provide helpful guidance
            if "ffmpeg" in error_msg.lower():
                logger.error("FFmpeg not available - audio processing limited")
                raise RuntimeError(
                    "Audio processing requires FFmpeg for this audio format. "
                    "Try using WAV format or ensure FFmpeg is installed in the container."
                )

            logger.error(f"Transcription failed: {error_msg}")
            raise

    async def health_check(self) -> bool:
        """
        Check if the speech service is healthy.

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            # Check if we can import whisper
            _get_whisper()

            # If model is initialized, it's definitely healthy
            if self._initialized and self.model:
                return True

            # Try to initialize if not done yet
            await self._initialize()
            return True

        except Exception as e:
            logger.error(f"Speech service health check failed: {str(e)}")
            return False

    def get_available_models(self) -> List[Dict[str, Any]]:
        """
        Get information about available Whisper models.

        Returns:
            List of model information dictionaries
        """
        models = [
            {
                "name": "tiny",
                "parameters": "39M",
                "vram": "~1GB",
                "relative_speed": "~10x",
                "description": "Fastest, least accurate"
            },
            {
                "name": "base",
                "parameters": "74M",
                "vram": "~1GB",
                "relative_speed": "~7x",
                "description": "Good balance of speed and accuracy"
            },
            {
                "name": "small",
                "parameters": "244M",
                "vram": "~2GB",
                "relative_speed": "~4x",
                "description": "Better accuracy, moderate speed"
            },
            {
                "name": "medium",
                "parameters": "769M",
                "vram": "~5GB",
                "relative_speed": "~2x",
                "description": "Good accuracy, slower"
            },
            {
                "name": "large",
                "parameters": "1550M",
                "vram": "~10GB",
                "relative_speed": "1x",
                "description": "Best accuracy, slowest"
            },
            {
                "name": "turbo",
                "parameters": "809M",
                "vram": "~6GB",
                "relative_speed": "~8x",
                "description": "Optimized large model, no translation"
            }
        ]

        # Mark current model
        for model in models:
            model["current"] = model["name"] == self.model_name

        return models

    async def change_model(self, model_name: str):
        """
        Change the Whisper model.

        Args:
            model_name: New model name to use
        """
        if model_name == self.model_name and self._initialized:
            return  # Already using this model

        logger.info(f"Changing Whisper model from '{self.model_name}' to '{model_name}'")

        # Reset state
        self.model_name = model_name
        self.model = None
        self._initialized = False

        # Re-initialize with new model
        await self._initialize()