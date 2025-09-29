import pyttsx3
import threading
import queue
import time

# ------------------ GLOBAL OFFLINE ENGINE ------------------ #
_tts_engine = pyttsx3.init()
_tts_engine.setProperty('rate', 170)
_tts_engine.setProperty('volume', 1.0)

_tts_queue = queue.Queue()
_tts_lock = threading.Lock()

def _tts_worker():
    while True:
        item = _tts_queue.get()
        if item is None:  # exit signal
            break
        text, wait_flag = item
        with _tts_lock:
            try:
                _tts_engine.say(text)
                _tts_engine.runAndWait()
            except RuntimeError:
                # engine already running, skip safely
                pass
        _tts_queue.task_done()

# Start the worker thread once
_tts_thread = threading.Thread(target=_tts_worker, daemon=True)
_tts_thread.start()

# ------------------ PUBLIC FUNCTIONS ------------------ #
_offline_queue = queue.Queue()
_offline_thread_started = False
_offline_thread_lock = threading.Lock()

def _offline_worker():
    while True:
        item = _offline_queue.get()
        if item is None:  # exit signal
            break
        text, avatar_widget = item
        try:
            if avatar_widget: avatar_widget.start()
            _offline_engine.say(text)
            _offline_engine.runAndWait()
            if avatar_widget: avatar_widget.stop()
        except Exception as e:
            print("⚠️ Offline TTS error:", e)
        _offline_queue.task_done()
def offline_speak_and_wait(text):
    """Blocking speak, waits until done."""
    _tts_queue.put(text)
    _tts_queue.join()
def offline_speak(text, avatar_widget=None):
    global _offline_thread_started
    with _offline_thread_lock:
        if not _offline_thread_started:
            t = Thread(target=_offline_worker, daemon=True)
            t.start()
            _offline_thread_started = True
    _offline_queue.put((text, avatar_widget))

def stop_offline_audio():
    while not _offline_queue.empty():
        try:
            _offline_queue.get_nowait()
            _offline_queue.task_done()
        except queue.Empty:
            break
    _offline_engine.stop()

def shutdown_tts():
    """Call on app exit to safely stop the TTS thread."""
    _tts_queue.put(None)
    _tts_thread.join()
