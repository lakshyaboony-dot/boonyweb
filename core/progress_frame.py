import os
import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
from core import theme
from core.resource_helper import resource_path


class ProgressFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=theme.CURRENT_THEME["PRIMARY_BG"])
        self.controller = controller
        self.user_id = self.controller.shared_data.get("user_info", {}).get("User ID")
        if not self.user_id:
            print("⚠️ No user logged in yet — ProgressFrame will not load data.")
            return
        self.day = controller.shared_data.get("current_day", "Day-1")

        # Activity columns (must match sheet)
        self.activities = ["Listen", "Speak", "Read", "Write", "Grammar", "Vocabulary", "Video", "Debate", "Bonus"]

        # Store bars and labels
        self.progress_bars = {}
        self.progress_labels = {}

        self.build_ui()
        self.load_user_progress()
        self.update_progress()

    def build_ui(self):
        T = theme.CURRENT_THEME

        title = tk.Label(self, text="📊 Your Progress", font=T["FONT_TITLE"], fg=T["PRIMARY_TEXT"], bg=T["PRIMARY_BG"])
        title.pack(pady=10)

        # Day Selector
        selector_frame = tk.Frame(self, bg=T["PRIMARY_BG"])
        selector_frame.pack(pady=10)

        tk.Label(selector_frame, text="Select Day:", font=T["FONT_SUBHEADING"], bg=T["PRIMARY_BG"], fg=T["PRIMARY_TEXT"]).pack(side="left", padx=5)
        self.day_var = tk.StringVar(value=self.day)
        self.day_dropdown = ttk.Combobox(selector_frame, textvariable=self.day_var, state="readonly", width=15)
        self.day_dropdown.pack(side="left", padx=5)
        self.day_dropdown.bind("<<ComboboxSelected>>", lambda e: self.update_progress())

        # Progress bars frame
        bars_frame = tk.Frame(self, bg=T["PRIMARY_BG"])
        bars_frame.pack(pady=10, fill="x", padx=20)

        for act in self.activities:
            row = tk.Frame(bars_frame, bg=T["PRIMARY_BG"])
            row.pack(fill="x", pady=5)

            lbl = tk.Label(row, text=act, font=T["FONT_TEXT"], bg=T["PRIMARY_BG"], fg=T["PRIMARY_TEXT"], width=15, anchor="w")
            lbl.pack(side="left")

            bar = ttk.Progressbar(row, length=300, maximum=100)
            bar.pack(side="left", padx=10)
            self.progress_bars[act] = bar

            perc_label = tk.Label(row, text="0% (0 cr)", font=T["FONT_TEXT"], bg=T["PRIMARY_BG"], fg=T["PRIMARY_TEXT"])
            perc_label.pack(side="left")
            self.progress_labels[act] = perc_label

        # Day completion bar
        tk.Label(self, text="Day Completion", font=T["FONT_SUBHEADING"], bg=T["PRIMARY_BG"], fg=T["PRIMARY_TEXT"]).pack(pady=(15, 0))
        self.day_bar = ttk.Progressbar(self, length=400, maximum=100)
        self.day_bar.pack()
        self.day_progress_label = tk.Label(self, text="0%", font=T["FONT_TEXT"], bg=T["PRIMARY_BG"], fg=T["PRIMARY_TEXT"])
        self.day_progress_label.pack()

        # Total credits
        self.total_label = tk.Label(self, text="🏆 Total Credits: 0", font=T["FONT_SUBHEADING"], bg=T["PRIMARY_BG"], fg=T["PRIMARY_TEXT"])
        self.total_label.pack(pady=10)

    def load_user_progress(self):
        """Load user progress from local or Google Sheet, auto-save if from Google."""
        self.df = None
        local_path = resource_path("data/syllabus/boony_user_progress.xlsx")

        # 1️⃣ Local check
        try:
            if os.path.exists(local_path):
                self.df = pd.read_excel(local_path, sheet_name=self.user_id)
        except Exception as e:
            print("⚠️ Local progress load failed:", e)

        # 2️⃣ Google Sheet fallback
        if self.df is None or self.df.empty:
            try:
                import gspread
                from oauth2client.service_account import ServiceAccountCredentials

                creds_path = resource_path("core/creds.json")
                scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
                creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
                client = gspread.authorize(creds)

                sheet = client.open("boony_user_progress").worksheet(self.user_id)
                records = sheet.get_all_records()
                if records:
                    self.df = pd.DataFrame(records)

                    # Auto-save locally
                    try:
                        mode = "a" if os.path.exists(local_path) else "w"
                        with pd.ExcelWriter(local_path, engine="openpyxl", mode=mode) as writer:
                            self.df.to_excel(writer, sheet_name=self.user_id, index=False)
                        print(f"💾 Saved {self.user_id} progress locally for offline use.")
                    except Exception as e:
                        print("⚠️ Auto-save to local failed:", e)
            except Exception as e:
                print("❌ Google Sheet load failed:", e)

        if self.df is None or self.df.empty:
            messagebox.showwarning("No Data", f"No progress data found for {self.user_id}.")
            self.df = pd.DataFrame(columns=["day"] + self.activities + ["Total Credits"])

        # Set days in dropdown
        days = self.df["day"].dropna().unique().tolist()
        self.day_dropdown["values"] = days
        if self.day not in days and days:
            self.day = days[0]
        self.day_var.set(self.day)

    def update_progress(self):
        """Update progress bars for the selected day."""
        if self.df is None or self.df.empty:
            return

        day_selected = self.day_var.get()
        row = self.df[self.df["day"] == day_selected]
        if row.empty:
            return

        row_data = row.iloc[0]
        total_credits = 0
        total_possible = 0

        for act in self.activities:
            credits = int(row_data.get(act, 0))
            max_cr = 20 if act.lower() == "speak" else 10
            percent = int((credits / max_cr) * 100) if max_cr > 0 else 0

            self.progress_bars[act]["value"] = percent
            self.progress_labels[act].config(text=f"{percent}% ({credits} cr)")

            total_credits += credits
            total_possible += max_cr

        day_percent = int((total_credits / total_possible) * 100) if total_possible > 0 else 0
        self.day_progress_label.config(text=f"Day Completion: {day_percent}%")
        self.day_bar["value"] = day_percent

        # Overall total
        self.total_label.config(text=f"🏆 Total Credits: {self.df[self.activities].sum().sum()}")
