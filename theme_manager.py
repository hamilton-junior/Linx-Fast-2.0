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
        # Re-entrancy guards to avoid recursive theme/appearance changes
        self._in_set_theme = False
        self._in_set_appearance = False
        self.windows: List[ctk.CTkBaseClass] = []  # type: ignore[type-arg]
        # debounce flags to avoid scheduling many refreshes in a short time
        self._refresh_pending = False
        self._verify_pending = False

        self.base_dir = Path(__file__).resolve().parent
        self.themes_dir = self.base_dir / "themes"
        self.themes_dir.mkdir(parents=True, exist_ok=True)

        self.set_theme(self.theme_name)
        self.set_appearance_mode(self.mode)

    # ----------------------------------------------------------------- setters
    def set_theme(self, theme_name: str) -> None:
        """Set theme and update all managed windows. Does NOT change appearance mode."""
        if theme_name == self.theme_name:
            logger.debug("set_theme called with same theme '%s' - skipping", theme_name)
            return

        if self._in_set_theme:
            logger.debug(
                "Already setting theme, skipping nested call for '%s'", theme_name
            )
            return

        self._in_set_theme = True
        try:
            theme_path = self.themes_dir / f"{theme_name}.json"
            if theme_path.exists():
                ctk.set_default_color_theme(str(theme_path))
            else:
                ctk.set_default_color_theme(theme_name)
            self.theme_name = theme_name
            # Do NOT change appearance mode here!
            try:
                if not self._refresh_pending:
                    self._refresh_pending = True
                    self.refresh_all_windows_async()
            finally:
                self._refresh_pending = False
        finally:
            self._in_set_theme = False

    def set_appearance_mode(self, mode: str) -> None:
        """Set appearance mode and refresh open windows. Does NOT change theme."""
        if mode == self.mode:
            logger.debug(
                "set_appearance_mode called with same mode '%s' - skipping", mode
            )
            return

        if self._in_set_appearance:
            logger.debug(
                "Already setting appearance mode, skipping nested call for '%s'", mode
            )
            return

        self._in_set_appearance = True
        try:
            ctk.set_appearance_mode(mode)
            self.mode = mode
            # Do NOT change theme here!
            try:
                if not self._refresh_pending:
                    self._refresh_pending = True
                    self.refresh_all_windows_async()
            finally:
                self._refresh_pending = False
        finally:
            self._in_set_appearance = False

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
    def _refresh_all_windows_safe(self) -> None:
        """Refresh all managed windows to apply new theme, safely and responsively."""
        # Use after_idle to avoid blocking the mainloop and prevent freezes
        for window in list(self.windows):
            try:
                if not getattr(window, "winfo_exists", lambda: False)():
                    continue
                # Força update imediato para todas as janelas, inclusive main_window
                self._refresh_single_window_safe(window)
            except Exception as exc:
                logger.error("Error scheduling refresh for window %s: %s", window, exc)

    def _refresh_single_window_safe(self, window):
        """Refresh a single window and all its widgets, avoiding redundant traversals."""
        try:
            if not getattr(window, "winfo_exists", lambda: False)():
                return
            
            # 1. Apply theme colors to all widgets in the tree (iterative, safe)
            self._apply_theme_to_all_widgets(window)
            
            # 2. Call specific update methods if they exist
            # We call these AFTER the general styling so windows can do custom adjustments
            if hasattr(window, "on_theme_changed"):
                try:
                    # Note: windows should avoid calling theme_manager.apply_theme_to(self) 
                    # inside on_theme_changed to avoid redundant work.
                    window.on_theme_changed()
                except Exception:
                    pass
            elif hasattr(window, "reload_theme_and_interface"):
                try:
                    window.reload_theme_and_interface()
                except Exception:
                    pass
            
            # 3. Force redraw
            try:
                window.update_idletasks()
            except Exception:
                pass
        except Exception as exc:
            logger.error("Error refreshing window %s: %s", window, exc)

    def _apply_theme_to_all_widgets(self, root_widget):
        """Iteratively update all CTk widgets' colors to match the current theme, safely."""
        try:
            theme = ctk.ThemeManager.theme
            current_mode = self.get_current_appearance()
            visited = set()
            stack = [root_widget]

            while stack:
                widget = stack.pop()
                widget_id = id(widget)
                if widget_id in visited:
                    continue
                visited.add(widget_id)

                try:
                    widget_class = widget.__class__.__name__
                    # Actual configuration
                    if widget_class in theme:
                        for prop in ("fg_color", "bg_color", "text_color", "border_color", "hover_color"):
                            try:
                                if prop in theme[widget_class]:
                                    color = theme[widget_class][prop]
                                    if isinstance(color, (list, tuple)):
                                        color = color[1] if current_mode.lower() == "dark" else color[0]
                                    widget.configure(**{prop: color})
                            except Exception:
                                pass
                except Exception:
                    pass

                # Add special components (dropdowns, etc)
                for attr in ("dropdown_menu", "listbox"):
                    component = getattr(widget, attr, None)
                    if component and id(component) not in visited:
                        stack.append(component)

                # Add standard children
                try:
                    for child in widget.winfo_children():
                        if id(child) not in visited:
                            stack.append(child)
                except Exception:
                    pass
        except Exception:
            pass

    def _refresh_single_window(self, window: ctk.CTkBaseClass) -> None:
        """Refresh a single window safely. Intended to be called from the mainloop via .after."""
        try:
            if not getattr(window, "winfo_exists", lambda: False)():
                return
            # Use the robust safe refresh logic by default
            self._refresh_single_window_safe(window)

            try:
                window.update_idletasks()
            except Exception:
                pass
        except Exception as exc:
            logger.debug("_refresh_single_window failed for %s: %s", window, exc)

    def refresh_all_windows_async(self) -> None:
        """Schedule a non-blocking refresh for all registered windows.

        This schedules per-window refresh using each window's .after(1, ...), which
        keeps the mainloop responsive and avoids synchronous work that can freeze
        the UI when many windows are open.
        """
        alive = []
        for window in list(self.windows):
            try:
                if not getattr(window, "winfo_exists", lambda: False)():
                    continue
                alive.append(window)
                try:
                    # Prefer scheduling via the window itself so the callback runs
                    # in the right context and doesn't block the main thread.
                    window.after(1, lambda w=window: self._refresh_single_window(w))
                except Exception:
                    # If scheduling fails (rare), do a best-effort synchronous call
                    self._refresh_single_window(window)
            except Exception as exc:
                logger.debug("Error scheduling refresh for window %s: %s", window, exc)
        # Prune dead windows
        self.windows = alive

    def verify_and_fix_all_windows(self) -> None:
        """Verify widget colours on all registered windows and fix mismatches.

        This will schedule a per-window non-blocking verification that checks
        each widget's relevant colour properties against the active theme and
        updates widgets that do not declare _custom_theme_overrides = True.
        """
        alive = []
        for window in list(self.windows):
            try:
                if not getattr(window, "winfo_exists", lambda: False)():
                    continue
                alive.append(window)
                try:
                    window.after(1, lambda w=window: self._verify_and_fix_window(w))
                except Exception:
                    # best-effort synchronous fallback
                    self._verify_and_fix_window(window)
            except Exception as exc:
                logger.debug("Error scheduling verify for window %s: %s", window, exc)
        self.windows = alive

    def _verify_and_fix_window(self, window: ctk.CTkBaseClass) -> None:
        """Walk a window's widget tree and ensure colours match theme defaults.

        This is conservative: widgets that expose attribute
        `_custom_theme_overrides = True` are left untouched.
        """
        try:
            if not getattr(window, "winfo_exists", lambda: False)():
                return

            theme = getattr(ctk.ThemeManager, "theme", {}) or {}
            current_mode = self.get_current_appearance()

            def _normalize(col):
                if isinstance(col, (list, tuple)):
                    return col[1] if current_mode.lower() == "dark" else col[0]
                return col

            def _check_widget(widget):
                try:
                    if getattr(widget, "_custom_theme_overrides", False):
                        return
                    cls_name = widget.__class__.__name__
                    if cls_name not in theme:
                        return
                    props = (
                        "fg_color",
                        "bg_color",
                        "text_color",
                        "border_color",
                        "hover_color",
                    )
                    for prop in props:
                        try:
                            if prop not in theme[cls_name]:
                                continue
                            desired = _normalize(theme[cls_name][prop])
                            # Attempt to read current value
                            current = None
                            try:
                                if hasattr(widget, "cget"):
                                    current = widget.cget(prop)
                            except Exception:
                                current = None
                            if current is None:
                                try:
                                    current = getattr(widget, prop, None)
                                except Exception:
                                    current = None
                            # If mismatch, try to configure
                            if current is not None and str(current) != str(desired):
                                try:
                                    widget.configure(**{prop: desired})
                                except Exception:
                                    pass
                        except Exception:
                            pass
                except Exception:
                    pass

            # Traverse
            stack = [window]
            while stack:
                w = stack.pop()
                _check_widget(w)
                try:
                    for c in w.winfo_children():
                        stack.append(c)
                except Exception:
                    pass
            try:
                window.update_idletasks()
            except Exception:
                pass
        except Exception as exc:
            logger.debug("_verify_and_fix_window failed for %s: %s", window, exc)


    def apply_theme_to(self, widget: ctk.CTkBaseClass) -> None:
        """Public helper to apply current theme/appearance recursively to a widget.

        This is useful for windows or complex widgets that want to refresh their
        internal state when the global theme changes.
        """
        try:
            if not widget or not getattr(widget, "winfo_exists", lambda: False)():
                return
            self._apply_theme_to_all_widgets(widget)
            try:
                widget.update_idletasks()
            except Exception:
                pass
        except Exception:
            logger.exception("Failed to apply theme to widget %s", widget)

    # ----------------------------------------------------------- helper methods
    def get_theme_default_color(self, widget_class, property_name: str) -> str:
        """Return theme default colour for a given widget property."""
        try:
            widget_name = widget_class.__name__
            color = ctk.ThemeManager.theme[widget_name][property_name]

            current_mode = self.get_current_appearance()
            if isinstance(color, (list, tuple)):
                return color[1] if current_mode.lower() == "dark" else color[0]
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
