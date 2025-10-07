import { useState, useCallback, useRef, useEffect } from 'react';

export interface Sentence {
  text: string;
  start_time?: number | null;
  end_time?: number | null;
  confidence?: number | null;
  index: number;
}

export interface VoiceInputState {
  isRecording: boolean;
  isProcessing: boolean;
  error: string | null;
  transcript: string | null;
  sentences: Sentence[];
  isSupported: boolean;
}

export interface VoiceInputOptions {
  onTranscript?: (text: string) => void;
  onSentences?: (sentences: Sentence[]) => void;
  onError?: (error: Error) => void;
  language?: string;
  apiEndpoint?: string;
  sessionId?: string | null;
}

/**
 * Custom hook for voice input functionality with Web Speech API fallback and Whisper backend support
 */
export function useVoiceInput({
  onTranscript,
  onSentences,
  onError,
  language = 'en',
  apiEndpoint = '/api/v1/speech',
  sessionId
}: VoiceInputOptions = {}) {
  const [state, setState] = useState<VoiceInputState>({
    isRecording: false,
    isProcessing: false,
    error: null,
    transcript: null,
    sentences: [],
    isSupported: false,
  });

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const [useWebSpeech, setUseWebSpeech] = useState(false);

  // Check for browser support
  useEffect(() => {
    const checkSupport = () => {
      const hasMediaRecorder = typeof MediaRecorder !== 'undefined';
      const hasWebSpeech = 'webkitSpeechRecognition' in window || 'SpeechRecognition' in window;
      const hasGetUserMedia = navigator.mediaDevices && navigator.mediaDevices.getUserMedia;

      setState(prev => ({
        ...prev,
        isSupported: hasMediaRecorder && hasGetUserMedia,
      }));

      // Use Web Speech API as fallback if available
      setUseWebSpeech(hasWebSpeech && (!hasMediaRecorder || !hasGetUserMedia));
    };

    checkSupport();
  }, []);

  const handleError = useCallback((error: Error) => {
    setState(prev => ({ ...prev, error: error.message, isRecording: false, isProcessing: false }));
    onError?.(error);
  }, [onError]);

  const clearError = useCallback(() => {
    setState(prev => ({ ...prev, error: null }));
  }, []);

  // Web Speech API implementation (fallback)
  const startWebSpeechRecognition = useCallback(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      handleError(new Error('Speech recognition not supported in this browser'));
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = language;

    recognition.onstart = () => {
      setState(prev => ({ ...prev, isRecording: true, error: null }));
    };

    recognition.onresult = (event) => {
      const transcript = event.results[0]?.[0]?.transcript;
      if (transcript) {
        // Generate simple sentences for Web Speech API (no timing info available)
        const sentences: Sentence[] = transcript
          .split(/[.!?]+/)
          .map((text, index) => text.trim())
          .filter(text => text.length > 0)
          .map((text, index) => ({
            text,
            start_time: null,
            end_time: null,
            confidence: event.results[0]?.[0]?.confidence || null,
            index
          }));

        setState(prev => ({ ...prev, transcript, sentences, isRecording: false }));
        onTranscript?.(transcript);
        onSentences?.(sentences);
      }
    };

    recognition.onerror = (event) => {
      handleError(new Error(`Speech recognition error: ${event.error}`));
    };

    recognition.onend = () => {
      setState(prev => ({ ...prev, isRecording: false }));
    };

    recognitionRef.current = recognition;
    recognition.start();
  }, [language, onTranscript, onSentences, handleError]);

  // MediaRecorder implementation (primary)
  const startMediaRecording = useCallback(async () => {
    try {
      clearError();

      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        }
      });

      streamRef.current = stream;
      audioChunksRef.current = [];

      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
          ? 'audio/webm;codecs=opus'
          : 'audio/webm'
      });

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        setState(prev => ({ ...prev, isRecording: false, isProcessing: true }));

        try {
          // Create audio blob
          const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });

          // Send to our speech API
          await transcribeAudio(audioBlob);
        } catch (error) {
          handleError(error as Error);
        }
      };

      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start();

      setState(prev => ({ ...prev, isRecording: true, error: null }));
    } catch (error) {
      handleError(error as Error);
    }
  }, [handleError, clearError]);

  const transcribeAudio = useCallback(async (audioBlob: Blob) => {
    if (!sessionId) {
      handleError(new Error('Session ID is required for transcription'));
      return;
    }

    try {
      const formData = new FormData();
      formData.append('audio_data', audioBlob);
      formData.append('session_id', sessionId);
      if (language) {
        formData.append('language', language);
      }

      const response = await fetch(`${apiEndpoint}/transcribe-stream`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      const transcript = result.transcription?.trim();
      const sentences: Sentence[] = result.sentences || [];

      if (transcript) {
        setState(prev => ({
          ...prev,
          transcript,
          sentences,
          isProcessing: false
        }));
        onTranscript?.(transcript);
        onSentences?.(sentences);
      } else {
        handleError(new Error('No speech detected in audio'));
      }
    } catch (error) {
      handleError(error as Error);
    } finally {
      setState(prev => ({ ...prev, isProcessing: false }));
    }
  }, [sessionId, language, apiEndpoint, onTranscript, onSentences, handleError]);

  const startRecording = useCallback(() => {
    if (!state.isSupported && !useWebSpeech) {
      handleError(new Error('Voice input is not supported in this browser'));
      return;
    }

    if (state.isRecording) {
      return; // Already recording
    }

    if (useWebSpeech) {
      startWebSpeechRecognition();
    } else {
      void startMediaRecording();
    }
  }, [state.isSupported, state.isRecording, useWebSpeech, startWebSpeechRecognition, startMediaRecording]);

  const stopRecording = useCallback(() => {
    if (!state.isRecording) return;

    if (useWebSpeech && recognitionRef.current) {
      recognitionRef.current.stop();
    } else if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
    }

    // Clean up media stream
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
  }, [state.isRecording, useWebSpeech]);

  const toggleRecording = useCallback(() => {
    if (state.isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  }, [state.isRecording, startRecording, stopRecording]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    };
  }, []);

  return {
    ...state,
    startRecording,
    stopRecording,
    toggleRecording,
    clearError,
    useWebSpeech,
  };
}

// Extend Window interface for TypeScript
declare global {
  interface Window {
    SpeechRecognition: typeof SpeechRecognition;
    webkitSpeechRecognition: typeof SpeechRecognition;
  }
}