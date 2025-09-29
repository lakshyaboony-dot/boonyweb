import os
import speech_recognition as sr

# Global whisper model variable
_whisper_model = None

def transcribe_audio(audio_path, model_size="base"):
    """
    Transcribe audio with Whisper (faster-whisper if available),
    fallback to Google SpeechRecognition if Whisper not available.
    """
    global _whisper_model
    if not audio_path or not os.path.exists(audio_path):
        return "[No audio to transcribe]"
    try:
        from faster_whisper import WhisperModel
        if _whisper_model is None:
            print(f"⏳ Loading Whisper model ({model_size}) ...")
            _whisper_model = WhisperModel(model_size, device="cpu", compute_type="int8")
            print("✅ Whisper model loaded")
        segments, _ = _whisper_model.transcribe(audio_path)
        text = " ".join(segment.text for segment in segments).strip()
        return text if text else "[No speech detected]"
    except ModuleNotFoundError:
        print("⚠️ faster-whisper not installed, falling back to Google STT")
    except Exception as e:
        print("❌ Whisper error:", e)

    # Google fallback
    try:
        r = sr.Recognizer()
        with sr.AudioFile(audio_path) as source:
            audio = r.record(source)
        text = r.recognize_google(audio, language="en-IN")
        return text
    except Exception as e:
        print("❌ Google transcription failed:", e)
        return "[Transcription failed]"
