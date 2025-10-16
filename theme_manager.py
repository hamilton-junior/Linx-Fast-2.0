"""Theme management utilities for Linx Fast."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List

import customtkinter as ctk

from logger_config import auto_log_functions

logger = logging.getLogger(__name__)


@auto_log_functions
class ThemeManager:
    """Keeps track of CustomTkinter windows and propagates theme updates."""

    def __init__(self, theme_name: str = "green", mode: str = "dark") -> None:
        self.theme_name = theme_name
        self.mode = mode
        self.windows: List[ctk.CTkBaseClass] = []  # type: ignore[type-arg]

        self.base_dir = Path(__file__).resolve().parent
        self.themes_dir = self.base_dir / "themes"
        self.themes_dir.mkdir(parents=True, exist_ok=True)

        self.set_theme(self.theme_name)
        self.set_appearance_mode(self.mode)

    # ----------------------------------------------------------------- setters
    def set_theme(self, theme_name: str) -> None:
        """Set theme and update all managed windows."""
        theme_path = self.themes_dir / f"{theme_name}.json"
        if theme_path.exists():
            ctk.set_default_color_theme(str(theme_path))
        else:
            ctk.set_default_color_theme(theme_name)
        self.theme_name = theme_name
        self._refresh_all_windows()

    def set_appearance_mode(self, mode: str) -> None:
        """Set appearance mode and refresh open windows."""
        ctk.set_appearance_mode(mode)
        self.mode = mode
        self._refresh_all_windows()

    def toggle_appearance(self) -> None:
        self.mode = "dark" if self.mode == "light" else "light"
        self.set_appearance_mode(self.mode)

    def get_current_appearance(self) -> str:
        return self.mode

    # ----------------------------------------------------------- window registry
    def register_window(self, window: ctk.CTkBaseClass) -> None:
        """Register a window to be managed by the theme manager."""
        if window in self.windows:
            return
        self.windows.append(window)
        try:
            bind_id = window.bind(
                "<Destroy>", lambda _event, w=window: self.unregister_window(w)
            )
            setattr(window, "_theme_manager_destroy_bind", bind_id)
        except Exception:
            pass

    def unregister_window(self, window: ctk.CTkBaseClass) -> None:
        """Unregister a window from theme management."""
        if window in self.windows:
            self.windows.remove(window)
        bind_id = getattr(window, "_theme_manager_destroy_bind", None)
        if bind_id:
            try:
                window.unbind("<Destroy>", bind_id)
            except Exception:
                pass
            finally:
                try:
                    delattr(window, "_theme_manager_destroy_bind")
                except Exception:
                    pass

    # --------------------------------------------------------- theme propagation
    def _refresh_all_windows(self) -> None:
        """Refresh all managed windows to apply new theme."""
        alive = []
        for window in list(self.windows):
            if not isinstance(window, (ctk.CTk, ctk.CTkToplevel)) or not window.winfo_exists():
                continue
            alive.append(window)
            try:
                if hasattr(window, "on_theme_changed"):
                    window.on_theme_changed()
                elif hasattr(window, "reload_theme_and_interface"):
                    window.reload_theme_and_interface()
                else:
                    self._apply_appearance_recursive(window)
                    window.update_idletasks()
            except Exception as exc:
                logger.error("Error refreshing window %s: %s", window, exc)
        self.windows = alive

    def _apply_appearance_recursive(self, widget: ctk.CTkBaseClass) -> None:  # type: ignore[type-arg]
        if hasattr(widget, "_apply_appearance_mode"):
            try:
                widget._apply_appearance_mode(self.mode)
            except Exception:
                pass
        for child in widget.winfo_children():
            self._apply_appearance_recursive(child)

    # ----------------------------------------------------------- helper methods
    def get_theme_default_color(self, widget_class, property_name: str) -> str:
        """Return theme default colour for a given widget property."""
        try:
            widget_name = widget_class.__name__
            color = ctk.ThemeManager.theme[widget_name][property_name]

            current_mode = self.get_current_appearance()
            if isinstance(color, (list, tuple)):
                return color[0] if current_mode.lower() == "dark" else color[1]
            return color
        except (KeyError, IndexError):
            return "#FF0000"  # fallback colour

    def get_lighter_color(self, color_hex: str, factor: float = 0.2) -> str:
        """Return a lighter variant of the hexadecimal colour."""
        color_hex = color_hex.lstrip("#")
        r = int(color_hex[:2], 16)
        g = int(color_hex[2:4], 16)
        b = int(color_hex[4:], 16)
        r = min(255, int(r + (255 - r) * factor))
        g = min(255, int(g + (255 - g) * factor))
        b = min(255, int(b + (255 - b) * factor))
        return f"#{r:02x}{g:02x}{b:02x}"

    def get_darker_color(self, color_hex: str, factor: float = 0.2) -> str:
        """Return a darker variant of the hexadecimal colour."""
        color_hex = color_hex.lstrip("#")
        r = int(color_hex[:2], 16)
        g = int(color_hex[2:4], 16)
        b = int(color_hex[4:], 16)
        r = int(r * (1 - factor))
        g = int(g * (1 - factor))
        b = int(b * (1 - factor))
        return f"#{r:02x}{g:02x}{b:02x}"

