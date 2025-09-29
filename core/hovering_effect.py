    # hovering_effects.py

from tkinter import font

normal_font = None
bold_font = None   # Call this from your main app with root passed to it
def setup_fonts(root):
    global normal_font, bold_font
    normal_font = font.Font(root, family="Arial", size=12)
    bold_font = font.Font(root, family="Arial", size=12, weight="bold")

def on_enter(e):
    e.widget['background'] = '#1E90FF'     # Hover background (Dodger Blue)
    e.widget['foreground'] = 'white'       # Hover text color
    e.widget['font'] = bold_font           # Bold text

def on_leave(e):
    e.widget['background'] = '#dceeff'     # Original background
    e.widget['foreground'] = 'black'       # Original text color
    e.widget['font'] = normal_font         # Normal font
 