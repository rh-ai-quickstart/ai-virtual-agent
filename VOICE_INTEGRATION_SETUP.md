# Voice-to-Text Integration Setup Guide

This guide explains how to set up and test the newly integrated voice-to-text functionality in the AI Virtual Agent platform.

## Overview

The voice integration provides:
- **Real-time voice input**: Record audio directly in the chat interface
- **Whisper-powered transcription**: High-quality speech-to-text using OpenAI Whisper
- **Browser fallback**: Uses Web Speech API when available as fallback
- **Multi-language support**: Configurable language detection
- **File upload support**: Process audio files (MP3, WAV, M4A, etc.)

## Backend Setup

### 1. Install Dependencies

The required dependencies have been added to `backend/requirements.txt`:
```
openai-whisper
torch
torchaudio
```

Install them:
```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment (Optional)

Set the Whisper model size (default is 'base'):
```bash
export WHISPER_MODEL=base  # Options: tiny, base, small, medium, large, turbo
```

### 3. API Endpoints

The following endpoints are now available:

- `POST /api/v1/speech/transcribe` - Transcribe uploaded audio files
- `POST /api/v1/speech/transcribe-stream` - Transcribe streaming audio data
- `GET /api/v1/speech/models` - Get available Whisper models
- `GET /api/v1/speech/health` - Health check for speech service

## Frontend Features

### Voice Input Button
- Microphone icon next to the message input
- Click to start/stop recording
- Visual feedback for recording state
- Status indicators for processing

### Browser Support
- **Primary**: Chrome, Firefox, Safari (with MediaRecorder API)
- **Fallback**: Web Speech API for basic voice recognition
- **Requirements**: HTTPS (required for microphone access in production)

### Language Support
- Configurable language detection
- Default: English ('en')
- Supports all languages that Whisper supports

## Current Status

### ✅ What Works Now
- **Speech service health check**: All endpoints responsive
- **Whisper model loading**: Base model (74M) loaded and ready
- **File upload transcription**: Upload WAV, MP3, M4A files for transcription
- **API endpoints**: All speech processing endpoints functional
- **Web Speech API fallback**: Browser-based voice recognition in supported browsers

### ⚠️ Current Limitations
- **Live microphone recording**: Requires FFmpeg for WebM audio processing
- **Browser audio formats**: Chrome/Firefox record in WebM which needs FFmpeg
- **Container setup**: Current UBI9 container doesn't include FFmpeg

### 🔧 Available Workarounds
1. **Use file upload**: Record audio separately and upload WAV files
2. **Web Speech API**: Browser's built-in speech recognition (Chrome/Edge)
3. **Alternative audio apps**: Use external recording apps to create WAV files

## Testing the Integration

### 1. Start the Backend
```bash
cd backend
uvicorn app.main:app --reload
```

### 2. Start the Frontend
```bash
cd frontend
npm run dev
```

### 3. Test Voice Input (File Upload Method)

1. **Open the application** in a modern browser (Chrome recommended)
2. **Grant microphone permissions** when prompted
3. **Start a chat session** with an AI agent
4. **Click the microphone button** next to the message input
5. **Speak clearly** for 2-5 seconds
6. **Click the microphone again** to stop recording
7. **Wait for processing** - the transcribed text should appear in the input field
8. **Send the message** as normal

### 4. Test Audio File Upload

1. **Prepare an audio file** (MP3, WAV, M4A format)
2. **Use the attachment feature** to upload the audio file
3. **The system will automatically transcribe** audio files and include them in the conversation

## Troubleshooting

### Common Issues

1. **"Voice not supported" error**
   - Ensure you're using HTTPS (required for microphone access)
   - Try a different browser (Chrome/Firefox recommended)
   - Check microphone permissions

2. **"Session ID required" error**
   - Start a chat session before trying voice input
   - Select an agent from the dropdown

3. **"Voice transcription requires additional audio processing tools" error**
   - This occurs when FFmpeg is not available in the container
   - **Workaround**: Use file upload with WAV format audio files instead of live microphone
   - **Solution**: Enable FFmpeg in deployment (requires container rebuild)
   - The Web Speech API fallback may work in some browsers

4. **Whisper model loading fails**
   - Check that PyTorch is properly installed
   - Verify sufficient disk space for model download
   - Check logs for specific error messages

5. **Poor transcription quality**
   - Speak clearly and avoid background noise
   - Try a larger Whisper model (small, medium, large)
   - Ensure good microphone quality

### Browser Requirements

- **HTTPS**: Required for microphone access (except localhost)
- **Modern browser**: Chrome 47+, Firefox 29+, Safari 14+
- **Microphone access**: User must grant permissions

### Performance Notes

- **Model loading**: First transcription may take longer (model download/loading)
- **GPU acceleration**: Automatically used if available
- **Memory usage**: Varies by model size (1GB for base, 10GB for large)

## Model Options

| Model | Size | VRAM | Speed | Use Case |
|-------|------|------|--------|----------|
| tiny | 39M | ~1GB | Fastest | Quick testing |
| base | 74M | ~1GB | Fast | **Recommended default** |
| small | 244M | ~2GB | Good | Better accuracy |
| medium | 769M | ~5GB | Slower | High accuracy needed |
| large | 1550M | ~10GB | Slowest | Best quality |
| turbo | 809M | ~6GB | Fast | Optimized large model |

## Security Considerations

- Audio data is processed on your server (not sent to external services)
- Temporary files are automatically cleaned up
- Microphone access requires user permission
- All audio processing respects session boundaries

## Next Steps

- Configure language preferences per user
- Add voice activity detection for better UX
- Implement push-to-talk mode
- Add audio format conversion for broader file support
- Consider adding speaker identification for multi-user scenarios