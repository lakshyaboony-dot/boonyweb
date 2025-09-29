# ===========================================
# core/app_config.py
# Central config for speech/voice
# ===========================================

# ----------------------------
# Default settings
# ----------------------------
language = "hinglish"      # "english" / "hinglish"
gender = "Female"          # "Male" / "Female"
speech_mode = "Auto"       # "Online" / "Offline" / "Auto" / "Silent"
global_avatar_widget = None

# Global vars used by app
global_avatar_widget = None
speak_text_wrapper_fn = None   # linked later by speak_function
_tts_forced_offline = False


# ----------------------------
# Voice selector for Online TTS
# ----------------------------
def voice_name():
    import pyttsx3

    online_voices = {
        ("en", "Male"): "en-US-GuyNeural",
        ("en", "Female"): "en-IN-KavyaNeural",        # More energetic female voice
        ("hinglish", "Male"): "hi-IN-MadhurNeural",   # Hinglish → Hindi Male voice
        ("hinglish", "Female"): "en-IN-KavyaNeural",  # More energetic female voice for Hinglish
    }

    # normalize language
    lang_key = "en"
    if language.lower() in ["hinglish"]:
        lang_key = "hinglish"

    # 🎯 अगर mode online/auto है → neural voice लौटाओ
    if speech_mode.lower() in ["online", "auto"]:
        return online_voices.get((lang_key, gender), "en-IN-KavyaNeural")

    # 🎯 अगर mode offline है → pyttsx3 से voices ढूंढो
    try:
        engine = pyttsx3.init()
        voices = engine.getProperty("voices")
        target_gender = gender.lower()
        for v in voices:
            if target_gender in v.name.lower():
                return v.id
        return voices[0].id  # fallback
    except Exception as e:
        print("⚠️ pyttsx3 voice select error:", e)
        return None
