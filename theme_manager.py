# theme_manager.py
import customtkinter as ctk
import os
import json


class ThemeManager:
    def __init__(self, default_theme="green"):
        self.themes_dir = "themes"
        self.default_theme = default_theme
        self.appearance = "dark"
        os.makedirs(self.themes_dir, exist_ok=True)
        self._load_theme_file()

    def _load_theme_file(self):
        theme_path = os.path.join(self.themes_dir, f"{self.default_theme}.json")
        if os.path.exists(theme_path):
            try:
                with open(theme_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    ctk.set_default_color_theme(data)
            except Exception:
                ctk.set_default_color_theme(self.default_theme)
        else:
            ctk.set_default_color_theme(self.default_theme)

        ctk.set_appearance_mode(self.appearance)

    def toggle_appearance(self):
        self.appearance = "light" if self.appearance == "dark" else "dark"
        ctk.set_appearance_mode(self.appearance)
