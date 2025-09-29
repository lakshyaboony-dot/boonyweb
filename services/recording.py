# services/recording.py
import sounddevice as sd
import wavio
import os
import uuid

def record_audio(duration=5, samplerate=44100, channels=1):
    """
    Record audio from microphone and save as WAV file.
    """
    filename = f"record_{uuid.uuid4().hex}.wav"
    filepath = os.path.join("static/recordings", filename)
    os.makedirs("static/recordings", exist_ok=True)

    print("🎤 Recording...")
    recording = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=channels, dtype="int16")
    sd.wait()  # wait until recording is finished
    print("✅ Recording finished")

    wavio.write(filepath, recording, samplerate, sampwidth=2)
    return filepath
