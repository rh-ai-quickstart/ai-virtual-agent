"""
Speech processing endpoints for voice-to-text functionality.
"""

import logging
import os
import tempfile
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from ...services.speech_service import SpeechService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/speech", tags=["speech"])

# Initialize speech service
speech_service = SpeechService()


@router.post("/transcribe")
async def transcribe_audio_file(
    session_id: str = Form(...),
    file: UploadFile = File(...),
    language: Optional[str] = Form(None),
):
    """
    Transcribe an uploaded audio file to text.

    Args:
        session_id: Chat session ID for tracking
        file: Audio file to transcribe (supported formats: mp3, wav, m4a, flac, ogg)
        language: Optional language code (e.g., 'en', 'es', 'fr') for better accuracy

    Returns:
        JSON response with transcription text and metadata
    """
    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=400, detail="File name is required")

    # Check file extension
    supported_extensions = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".webm"}
    file_ext = os.path.splitext(file.filename.lower())[1]

    if file_ext not in supported_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format. Supported formats: {', '.join(supported_extensions)}",
        )

    try:
        # Create temporary file to store uploaded audio
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            temp_file.write(await file.read())
            temp_file_path = temp_file.name

        # Transcribe audio
        result = await speech_service.transcribe_file(temp_file_path, language=language)

        # Clean up temporary file
        os.unlink(temp_file_path)

        # Log transcription for debugging (be careful with sensitive data in production)
        logger.info(
            f"Transcribed audio for session {session_id}: {len(result['text'])} characters"
        )

        return JSONResponse(
            content={
                "transcription": result["text"],
                "language": result.get("language"),
                "confidence": result.get("confidence"),
                "sentences": result.get("sentences", []),
                "session_id": session_id,
                "filename": file.filename,
            },
            status_code=200,
        )

    except Exception as e:
        logger.error(f"Transcription failed for session {session_id}: {str(e)}")
        # Clean up temporary file on error
        if "temp_file_path" in locals():
            try:
                os.unlink(temp_file_path)
            except OSError:
                pass

        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


@router.post("/transcribe-stream")
async def transcribe_audio_stream(
    session_id: str = Form(...),
    audio_data: bytes = File(...),
    language: Optional[str] = Form(None),
):
    """
    Transcribe audio data from a streaming source (e.g., microphone).

    Args:
        session_id: Chat session ID for tracking
        audio_data: Raw audio bytes (typically WebM format from browser)
        language: Optional language code for better accuracy

    Returns:
        JSON response with transcription text
    """
    try:
        # Use WebM extension since browsers typically send WebM format
        # This helps Whisper identify the format correctly
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_file:
            temp_file.write(audio_data)
            temp_file_path = temp_file.name

        # Transcribe audio
        result = await speech_service.transcribe_file(temp_file_path, language=language)

        # Clean up temporary file
        os.unlink(temp_file_path)

        return JSONResponse(
            content={
                "transcription": result["text"],
                "language": result.get("language"),
                "sentences": result.get("sentences", []),
                "session_id": session_id,
            },
            status_code=200,
        )

    except Exception as e:
        error_msg = str(e)
        logger.error(
            f"Stream transcription failed for session {session_id}: {error_msg}"
        )

        # Clean up temporary file on error
        if "temp_file_path" in locals():
            try:
                os.unlink(temp_file_path)
            except OSError:
                pass

        # Provide specific guidance for ffmpeg-related errors
        if "ffmpeg" in error_msg.lower():
            detail = (
                "Voice transcription requires additional audio processing tools. "
                "Try using the file upload feature with WAV format instead, "
                "or contact your administrator to enable full audio support."
            )
        else:
            detail = f"Stream transcription failed: {error_msg}"

        raise HTTPException(status_code=500, detail=detail)


@router.get("/models")
async def get_available_models():
    """
    Get information about available speech recognition models.

    Returns:
        JSON response with model information
    """
    try:
        models = speech_service.get_available_models()
        return JSONResponse(content={"models": models}, status_code=200)
    except Exception as e:
        logger.error(f"Failed to get model information: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get model information: {str(e)}"
        )


@router.get("/health")
async def speech_health_check():
    """
    Health check for speech processing service.

    Returns:
        JSON response with service status
    """
    try:
        is_healthy = await speech_service.health_check()
        return JSONResponse(
            content={
                "status": "healthy" if is_healthy else "unhealthy",
                "service": "speech_recognition",
            },
            status_code=200 if is_healthy else 503,
        )
    except Exception as e:
        logger.error(f"Speech service health check failed: {str(e)}")
        return JSONResponse(
            content={
                "status": "unhealthy",
                "service": "speech_recognition",
                "error": str(e),
            },
            status_code=503,
        )
