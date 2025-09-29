# core/theme.py

# === Unified Theme Definitions (Blue, Light, Golden) ===
THEMES = {
    "blue": {
        # Backgrounds
        "PRIMARY_BG": "#E6F2FA",
        "SECONDARY_BG": "#C8E1F5",
        "SIDEBAR_BG": "#90CAF9",
        "HIGHLIGHT": "#C8E1F5",
        "NOTICE_BG": "#DDEBFA",
        "STAR_BG": "#1E5AA8",
        "DARK_BG": "#0F0285",
        "INFO": "#007ACC",
        # Text Colors
        "PRIMARY_TEXT": "#1E40AF",
        "TEXT_COLOR": "#1E40AF",
        "NOTICE_TEXT": "#1E40AF",
        "NOTICE_HEADER": "#1D4ED8",
        "STAR_TEXT": "#FFFFFF",
        "BORDER": "#B0BEC5",
        # Entry Fields
        "ENTRY_BG": "#FFFFFF",
        "ENTRY_TEXT": "#000000",

        # Buttons
        "PRIMARY_BTN": "#AEDBFA",  # Light blue

        "SECONDARY_BTN": "#4D90FE",
        "DISABLED_BTN": "#AFCBE3",
        "DANGER_BTN": "#D32F2F",
        "WARNING_BTN": "#F4A300",
        "INFO_BTN": "#0288D1",
        "ACTIVE_BTN": "#103E8F",
        "HOVER_BTN": "#4D90FE",

        # Status Colors
        "SUCCESS": "#0D8B6C",
        "ERROR": "#B80028",
        "WARNING": "#F4A300",

        # Fonts
        "PRIMARY_FONT": ("Helvetica", 12),
        "FONT_TITLE": ("Helvetica", 18, "bold"),
        "FONT_HEADING": ("Helvetica", 16, "bold"),
        "FONT_SUBHEADING": ("Helvetica", 14, "bold"),
        "FONT_BODY": ("Helvetica", 12),
        "FONT_LABEL": ("Helvetica", 14),
        "FONT_TEXT": ("Helvetica", 12),
        "FONT_SMALL": ("Helvetica", 11),
        "FONT_BUTTON": ("Helvetica", 14, "bold"),
    },

    "light": {
        # Backgrounds
        "PRIMARY_BG": "#FAFAFA",
        "SECONDARY_BG": "#F0F0F0",
        "SIDEBAR_BG": "#E8E8E8",
        "HIGHLIGHT": "#F0F0F0",
        "NOTICE_BG": "#FFFFFF",
        "STAR_BG": "#5B8C5A",
        "DARK_BG": "#F7BF9E",
        "INFO": "#336699",
        # Text Colors
        "PRIMARY_TEXT": "#202020",
        "TEXT_COLOR": "#202020",
        "NOTICE_TEXT": "#333333",
        "NOTICE_HEADER": "#0A472E",
        "STAR_TEXT": "#FFFFFF",
        "BORDER": "#CCCCCC",
        # Entry Fields
        "ENTRY_BG": "#FAF9F2",
        "ENTRY_TEXT": "#000000",

        # Buttons
        "PRIMARY_BTN": "#FFCCCC",  # Very light red

        "SECONDARY_BTN": "#C2555B",
        "DISABLED_BTN": "#CCCCCC",
        "DANGER_BTN": "#FF4D4D",
        "WARNING_BTN": "#E67E22",
        "INFO_BTN": "#17A2B8",
        "ACTIVE_BTN": "#3D6F3C",
        "HOVER_BTN": "#6FC06E",

        # Status Colors
        "SUCCESS": "#007E5A",
        "ERROR": "#C62828",
        "WARNING": "#E67E22",

        # Fonts
        "PRIMARY_FONT": ("Helvetica", 12),
        
        "FONT_HEADING": ("Helvetica", 16, "bold"),
        
        "FONT_BODY": ("Helvetica", 12),
        "FONT_LABEL": ("Helvetica", 14),
        
        "FONT_SMALL": ("Helvetica", 11),
        "FONT_BUTTON": ("Helvetica", 14, "bold"),
        "FONT_TEXT" : ("Segoe UI", 13),
        "FONT_SUBHEADING" : ("Segoe UI", 15, "bold"),
        "FONT_TITLE" : ("Segoe UI", 18, "bold"),
    },

    "golden": {
        # Backgrounds
        "PRIMARY_BG": "#FFF8E1",
        "SECONDARY_BG": "#FFE082",
        "SIDEBAR_BG": "#FFD54F",
        "HIGHLIGHT": "#FFECB3",
        "NOTICE_BG": "#FFF3E0",
        "STAR_BG": "#B68D40",
        "DARK_BG": "#6D4C41",
        "BORDER": "#D7CCC8",
        # Text Colors
        "PRIMARY_TEXT": "#4E342E",
        "TEXT_COLOR": "#4E342E",
        "NOTICE_TEXT": "#6D4C41",
        "NOTICE_HEADER": "#5D4037",
        "STAR_TEXT": "#FFFFFF",
        "INFO": "#A67C00",
        # Entry Fields
        "ENTRY_BG": "#FFFFFF",
        "ENTRY_TEXT": "#000000",

        # Buttons
        "PRIMARY_BTN": "#B68D40",
        "SECONDARY_BTN": "#FFCA28",
        "DISABLED_BTN": "#D7CCC8",
        "DANGER_BTN": "#D84315",
        "WARNING_BTN": "#FFB300",
        "INFO_BTN": "#FF9800",
        "ACTIVE_BTN": "#A1887F",
        "HOVER_BTN": "#FBC02D",

        # Status Colors
        "SUCCESS": "#8BC34A",
        "ERROR": "#D84315",
        "WARNING": "#FFB300",

        # Fonts
        "PRIMARY_FONT": ("Helvetica", 12),
        "FONT_TITLE": ("Helvetica", 18, "bold"),
        "FONT_HEADING": ("Helvetica", 16, "bold"),
        "FONT_SUBHEADING": ("Helvetica", 14, "bold"),
        "FONT_BODY": ("Helvetica", 12),
        "FONT_LABEL": ("Helvetica", 14),
        "FONT_TEXT": ("Helvetica", 12),
        "FONT_SMALL": ("Helvetica", 11),
        "FONT_BUTTON": ("Helvetica", 14, "bold"),
    }
}

# Default theme
CURRENT_THEME = THEMES["blue"]

# === Helper functions ===
def apply_button(button):
    T = CURRENT_THEME

    try:
        button.configure(
            bg=T["PRIMARY_BTN"],
            fg=T.get("ENTRY_TEXT", "#001f3f"),
            activebackground=T["ACTIVE_BTN"],
            font=T["FONT_BUTTON"],
            relief="raised",
            bd=2,
            padx=str(8),   # convert int -> str
            pady=str(4),   # convert int -> str
            cursor="hand2"
        )

        def on_hover(event):
            button["background"] = T.get("HOVER_BTN", "#66BB6A")

        def on_leave(event):
            button["background"] = T.get("PRIMARY_BTN", "#4CAF50")

        button.bind("<Enter>", on_hover)
        button.bind("<Leave>", on_leave)

    except Exception as e:
        print("apply_button safe error:", e)



def apply_label(label, kind="normal"):
    T = CURRENT_THEME
    if kind == "heading":
        label.configure(
            bg=T["PRIMARY_BG"], fg=T["PRIMARY_TEXT"],
            font=T["FONT_HEADING"]
        )
    elif kind == "subheading":
        label.configure(
            bg=T["PRIMARY_BG"], fg=T["PRIMARY_TEXT"],
            font=T["FONT_SUBHEADING"]
        )
    else:
        label.configure(
            bg=T["PRIMARY_BG"], fg=T["TEXT_COLOR"],
            font=T["PRIMARY_FONT"]
        )
