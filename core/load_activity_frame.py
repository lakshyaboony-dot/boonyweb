# core/load_activity_frame.py

from ui.speak_function import speak_text_wrapper
from ui.listen_chatbot_frame import ListenFrame
from ui.speak_activity_frame import SpeakActivityFrame
from ui.vocab_frame import VocabFrame  # Future

import tkinter as tk
from core import theme

def load_activity_frame(right_panel, controller, day, activity_type, resume_statement=0):
    """Loads the appropriate activity frame into right_panel."""
    controller.shared_data["current_day"] = day

    # Clear previous widgets
    for widget in right_panel.winfo_children():
        widget.destroy()

    # 🏷️ Add Day label on top
    day_label = tk.Label(
        right_panel,
        text=f"📅 You are working on {day}",
        font=("Segoe UI", 18, "bold"),
        fg="green",
        bg=theme.CURRENT_THEME["PRIMARY_BG"]
    )
    day_label.grid(row=0, column=0, pady=(10, 5), sticky="n")

    # 🧭 Load activity
    if activity_type == "listen":
        frame = ListenFrame(right_panel, controller)
        if hasattr(frame, "start_from_statement"):
            frame.start_from_statement(resume_statement)
        speak_text_wrapper(f"{day} listening activity is starting.", lang="hinglish")

    elif activity_type == "speak":
        frame = SpeakActivityFrame(right_panel, controller)
        if hasattr(frame, "start_from_statement"):
            frame.start_from_statement(resume_statement)
        speak_text_wrapper(f"{day} speaking activity is starting.", lang="hinglish")

    elif activity_type == "vocab":
        frame = VocabFrame(right_panel, controller)
        if hasattr(frame, "start_from_word"):
            frame.start_from_word(resume_statement)
        speak_text_wrapper(f"{day} vocabulary activity is starting.", lang="hinglish")

    else:
        speak_text_wrapper("Unknown activity type requested.", lang="english")
        return

    frame.grid(row=0, column=0, sticky="nsew")
