import os
from faster_whisper import WhisperModel

_model = None

def transcribe_audio(path, size="base"):
    global _model
    if not os.path.exists(path):
        return "[No audio]"
    if _model is None:
        _model = WhisperModel(size, device="cpu", compute_type="int8")
    
    try:
        # Check audio file properties
        file_size = os.path.getsize(path)
        print(f"🎵 STT: Processing audio file: {path}")
        print(f"🎵 STT: File size: {file_size} bytes")
        print(f"🎵 STT: File extension: {os.path.splitext(path)[1]}")
        # Maximum sensitivity transcription with forced English
        segments, info = _model.transcribe(
            path,
            language="en",  # Force English language detection
            task="transcribe",  # Explicitly set transcription task
            vad_filter=True,  # Enable Voice Activity Detection
            beam_size=1,  # Faster processing with single beam
            best_of=1,    # Single candidate for speed
            temperature=0.0,  # Deterministic output
            no_speech_threshold=0.01,  # Extremely low threshold
            condition_on_previous_text=False,  # Independent processing
            initial_prompt="This is English speech.",  # Hint for English
            vad_parameters=dict(
                min_silence_duration_ms=100,  # Very short silence
                speech_pad_ms=400,  # Moderate padding
                threshold=0.1,  # Very sensitive VAD
            ),
            word_timestamps=True,  # Enable word timestamps
            prepend_punctuations="\"'([{-",
            append_punctuations="\"'.。,，!！?？:：)]}、"
        )
        
        result = " ".join([s.text for s in segments]).strip()
        
        # Enhanced debugging for transcription results
        print(f"🎵 STT: Segments found: {len(list(segments))}")
        print(f"🎵 STT: Detected language: {info.language if hasattr(info, 'language') else 'unknown'}")
        print(f"🎵 STT: Language probability: {info.language_probability if hasattr(info, 'language_probability') else 'unknown'}")
        print(f"🎵 STT: Transcription result: '{result}'")
        
        # Enhanced debugging for speech detection issues
        if not result and os.path.exists(path):
            file_size = os.path.getsize(path)
            if file_size > 1000:  # If file has reasonable size but no transcription
                print(f"⚠️ STT: Audio file size: {file_size} bytes, but no speech detected")
                return "[Low volume or unclear speech detected]"
        
        return result or "[No speech detected]"
        
    except Exception as e:
        print(f"❌ STT transcription error: {e}")
        return "[Transcription error]"

# Alias function for compatibility
def transcribe_audio_file(path, size="base"):
    """Alias for transcribe_audio function for compatibility"""
    return transcribe_audio(path, size)
