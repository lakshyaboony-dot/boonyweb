# services/tts.py

import os
import uuid
import shutil
from gtts import gTTS

EDGE_AVAILABLE = False
PYTTSX3_AVAILABLE = False
try:
    import edge_tts  # type: ignore
    EDGE_AVAILABLE = True
except Exception:
    EDGE_AVAILABLE = False
try:
    import pyttsx3  # type: ignore
    PYTTSX3_AVAILABLE = True
except Exception:
    PYTTSX3_AVAILABLE = False


# ----------------------------
# Helper: sanitize gender input
# ----------------------------
def get_gender(gender: str = "Male") -> str:
    gender = (gender or "Male").title()
    return "Male" if gender == "Male" else "Female"


# ----------------------------
# Generate TTS mp3 file
# ----------------------------
def _default_voice_name(gender: str = "Male", accent: str | None = None, voice_name: str | None = None) -> str:
    if voice_name:
        return voice_name
    g = (gender or "Male").lower()
    a = (accent or "indian")
    # Use reliable English voices instead of Hindi voices
    if a == "indian" or a == "hi-IN":
        return "en-IN-NeerjaNeural" if g == "female" else "en-IN-PrabhatNeural"
    return "en-US-JennyNeural" if g == "female" else "en-US-GuyNeural"


def _out_dir() -> str:
    out_dir = os.path.join("static", "tts")
    os.makedirs(out_dir, exist_ok=True)
    return out_dir


def _ffmpeg_path() -> str | None:
    # Try local ffmpeg in repo if present (Windows)
    win_path = os.path.join("ffmpeg-2025-08-20-git-4d7c609be3-full_build", "ffmpeg-2025-08-20-git-4d7c609be3-full_build", "bin", "ffmpeg.exe")
    return win_path if os.path.exists(win_path) else None


def _wav_to_mp3(wav_path: str, mp3_path: str) -> bool:
    exe = _ffmpeg_path()
    if not exe:
        return False
    try:
        os.system(f'"{exe}" -y -i "{wav_path}" -codec:a libmp3lame -qscale:a 4 "{mp3_path}"')
        return os.path.exists(mp3_path)
    except Exception:
        return False


def generate_tts(text: str, gender: str = "Male", lang: str | None = None, accent: str | None = None, voice_name: str | None = None, mode: str | None = None) -> str | None:
    """
    Generate a temporary TTS file for given text.
    Returns the relative file path (e.g., 'static/tts/xyz.mp3')
    """
    print(f"🎵 TTS Generation started for: '{text[:30]}{'...' if len(text) > 30 else ''}'")
    print(f"🎵 TTS Parameters: gender={gender}, lang={lang}, accent={accent}, voice_name={voice_name}, mode={mode}")
    print(f"🎵 TTS Dependencies: EDGE_AVAILABLE={EDGE_AVAILABLE}, PYTTSX3_AVAILABLE={PYTTSX3_AVAILABLE}")
    
    if not text or not text.strip():
        print("❌ TTS Error: Empty text provided")
        raise ValueError("Text cannot be empty for TTS generation.")

    out_dir = _out_dir()
    print(f"🎵 TTS Output directory: {out_dir}")

    # Unique filename
    uid = uuid.uuid4().hex
    mp3_filename = f"tts_{uid}.mp3"
    wav_filename = f"tts_{uid}.wav"
    mp3_path = os.path.join(out_dir, mp3_filename)
    wav_path = os.path.join(out_dir, wav_filename)
    print(f"🎵 TTS Target files: MP3={mp3_path}, WAV={wav_path}")

    # language selection: 'english' => en, 'hinglish' => hi (closest)
    lang_code = "en"
    if isinstance(lang, str):
        l = lang.lower()
        if l.startswith("en"):
            lang_code = "en"
        elif "hinglish" in l or l.startswith("hi"):
            lang_code = "hi"
    print(f"🎵 TTS Language code: {lang_code}")
    
    # Prefer Edge online if available and not forced offline
    want_online = (mode or "auto").lower() != "offline"
    want_offline = (mode or "auto").lower() != "online"
    print(f"🎵 TTS Mode preferences: want_online={want_online}, want_offline={want_offline}")
    
    # Track attempted methods for error reporting
    attempted_methods = []

    if want_online and EDGE_AVAILABLE:
        print("🎵 Trying Edge TTS (online)...")
        attempted_methods.append("Edge TTS (online)")
        try:
            vn = _default_voice_name(gender, accent, voice_name)
            print(f"🎵 Edge TTS voice: {vn}")
            # Save via edge_tts directly to mp3
            import asyncio
            async def _save():
                comm = edge_tts.Communicate(text, voice=vn)
                await comm.save(mp3_path)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_save())
            loop.close()
            if os.path.exists(mp3_path):
                print(f"✅ Edge TTS Success: {mp3_path}")
                return mp3_path
            else:
                print("❌ Edge TTS failed: File not created")
        except Exception as e:
            print(f"❌ Edge TTS Exception: {str(e)}")
            pass

    if want_offline and PYTTSX3_AVAILABLE:
        print("🎵 Trying pyttsx3 TTS (offline)...")
        attempted_methods.append("pyttsx3 TTS (offline)")
        try:
            engine = pyttsx3.init()
            print("🎵 pyttsx3 engine initialized")
            # Try mapping for SAPI voices by name fragment
            target_name = _default_voice_name(gender, accent, voice_name)
            print(f"🎵 pyttsx3 target voice: {target_name}")
            print(f"🎵 pyttsx3 processing text: '{text[:50]}{'...' if len(text) > 50 else ''}'")
            try:
                # Some engines allow selecting by name; otherwise keep default
                voices = engine.getProperty('voices')
                print(f"🎵 pyttsx3 available voices: {len(voices) if voices else 0}")
                for v in voices or []:
                    if isinstance(target_name, str) and v.name and target_name.split('-')[-1].lower() in v.name.lower():
                        engine.setProperty('voice', v.id)
                        print(f"🎵 pyttsx3 voice set to: {v.name}")
                        break
            except Exception as ve:
                print(f"⚠️ pyttsx3 voice selection error: {ve}")
                pass
            engine.setProperty('rate', 170)
            print(f"🎵 pyttsx3 saving to: {wav_path}")
            # Ensure text is properly encoded for pyttsx3
            clean_text = text.encode('ascii', 'ignore').decode('ascii') if any(ord(c) > 127 for c in text) else text
            if clean_text != text:
                print(f"🎵 pyttsx3 text cleaned for ASCII compatibility")
            engine.save_to_file(clean_text, wav_path)
            engine.runAndWait()
            engine.stop()
            if os.path.exists(wav_path):
                print(f"✅ pyttsx3 WAV created: {wav_path}")
                # Try to convert to mp3 if ffmpeg available
                if _wav_to_mp3(wav_path, mp3_path):
                    print(f"✅ pyttsx3 converted to MP3: {mp3_path}")
                    try: os.remove(wav_path)
                    except Exception: pass
                    return mp3_path
                print(f"✅ pyttsx3 returning WAV: {wav_path}")
                return wav_path
            else:
                print("❌ pyttsx3 failed: WAV file not created")
        except Exception as e:
            print(f"❌ pyttsx3 Exception: {str(e)}")
            pass

    # Fallback: gTTS (online google) - with error handling
    print("🎵 Trying Google TTS (online fallback)...")
    attempted_methods.append("Google TTS (online fallback)")
    try:
        tts = gTTS(text=text, lang=lang_code)
        print(f"🎵 Google TTS object created with lang: {lang_code}")
        tts.save(mp3_path)
        print(f"🎵 Google TTS saved to: {mp3_path}")
        if os.path.exists(mp3_path):
            print(f"✅ Google TTS Success: {mp3_path}")
            return mp3_path
        else:
            print("❌ Google TTS failed: File not created")
    except Exception as e:
        print(f"❌ Google TTS Exception: {e}")
        pass

    # Enhanced error reporting
    error_msg = f"TTS generation failed. Attempted methods: {', '.join(attempted_methods)}"
    if not attempted_methods:
        error_msg = "No TTS methods available. Please check your internet connection or install offline TTS."
    elif mode == "online" and not any("online" in method for method in attempted_methods):
        error_msg = "Online TTS requested but not available. Please check your internet connection."
    elif mode == "offline" and not any("offline" in method for method in attempted_methods):
        error_msg = "Offline TTS requested but not available. Please install pyttsx3 for offline support."
    
    print(f"❌ All TTS methods failed: {error_msg}")
    raise RuntimeError(error_msg)


# ----------------------------
# Cleanup old TTS files
# ----------------------------
def cleanup_tts(older_than_seconds: int = 3600):
    """
    Delete temporary TTS files older than X seconds.
    By default, deletes files older than 1 hour.
    """
    out_dir = os.path.join("static", "tts")
    if not os.path.exists(out_dir):
        return

    import time
    now = time.time()

    for f in os.listdir(out_dir):
        fpath = os.path.join(out_dir, f)
        if os.path.isfile(fpath) and f.startswith("tts_") and f.endswith(".mp3"):
            if now - os.path.getmtime(fpath) > older_than_seconds:
                try:
                    os.remove(fpath)
                except Exception:
                    pass
