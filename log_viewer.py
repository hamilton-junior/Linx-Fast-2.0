"""CustomTkinter-based log viewer window with auto refresh support."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import customtkinter as ctk

from logger_config import auto_log_functions, get_log_file_path, tail_log_file

logger = logging.getLogger("log_viewer")


@auto_log_functions
class LogViewer(ctk.CTkToplevel):
    """Displays the application log with optional auto-refresh."""

    _DEFAULT_LINES = ("50", "100", "200", "500", "1000")

    def __init__(self, parent: Optional[ctk.CTk] = None) -> None:
        super().__init__(parent)
        self.master = parent

        self.title("Log Viewer")
        self.geometry("900x600")
        self.minsize(500, 360)

        self._auto_refresh_job: Optional[str] = None
        self._refresh_interval_ms = 2000

        self.lines_var = ctk.StringVar(value="200")
        self.auto_refresh_var = ctk.BooleanVar(value=True)

        self._build_ui()
        self.refresh_logs()
        if self.auto_refresh_var.get():
            self._start_auto_refresh()

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # ------------------------------------------------------------------ UI ---
    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        main_frame = ctk.CTkFrame(self, corner_radius=0)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)

        controls = ctk.CTkFrame(main_frame)
        controls.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        controls.grid_columnconfigure(3, weight=1)

        ctk.CTkButton(controls, text="Atualizar", command=self.refresh_logs).grid(
            row=0, column=0, padx=(6, 10), pady=6
        )

        self.auto_refresh_switch = ctk.CTkSwitch(
            controls,
            text="Auto refresh",
            variable=self.auto_refresh_var,
            command=self.toggle_auto_refresh,
        )
        self.auto_refresh_switch.grid(row=0, column=1, padx=6, pady=6)

        ctk.CTkLabel(controls, text="Qtde. linhas:").grid(
            row=0, column=2, padx=(20, 6), pady=6
        )
        self.lines_combo = ctk.CTkComboBox(
            controls,
            values=list(self._DEFAULT_LINES),
            variable=self.lines_var,
            width=110,
            command=lambda _: self.refresh_logs(),
        )
        self.lines_combo.grid(row=0, column=3, padx=(0, 6), pady=6, sticky="w")

        self.status_var = ctk.StringVar(value="")
        ctk.CTkLabel(
            controls, textvariable=self.status_var, anchor="e"
        ).grid(row=0, column=4, padx=(12, 6), pady=6, sticky="e")

        text_frame = ctk.CTkFrame(main_frame, corner_radius=0)
        text_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=(4, 8))
        text_frame.grid_columnconfigure(0, weight=1)
        text_frame.grid_rowconfigure(0, weight=1)

        self.log_text = ctk.CTkTextbox(
            text_frame,
            wrap="none",
            font=("Consolas", 11),
        )
        self.log_text.grid(row=0, column=0, sticky="nsew")

        self.v_scroll = ctk.CTkScrollbar(
            text_frame, orientation="vertical", command=self.log_text.yview
        )
        self.v_scroll.grid(row=0, column=1, sticky="ns")
        self.h_scroll = ctk.CTkScrollbar(
            text_frame, orientation="horizontal", command=self.log_text.xview
        )
        self.h_scroll.grid(row=1, column=0, sticky="ew")

        self.log_text.configure(
            state="disabled",
            yscrollcommand=self.v_scroll.set,
            xscrollcommand=self.h_scroll.set,
        )

    # -------------------------------------------------------------- Behaviour ---
    def refresh_logs(self) -> None:
        """Reload log content into the textbox."""
        try:
            num_lines = self._get_line_count()
        except ValueError:
            num_lines = 200
            self.lines_var.set(str(num_lines))

        log_path = Path(get_log_file_path())
        self.status_var.set(str(log_path))

        if not log_path.exists():
            logger.warning("Log file not found at %s", log_path)
            self._show_text("Log file not found.")
            return

        try:
            lines = tail_log_file(num_lines)
        except Exception as exc:
            logger.exception("Failed to read log file: %s", exc)
            self._show_text(f"Erro ao ler o log: {exc}")
            return

        display_text = "\n".join(lines).strip()
        if not display_text:
            display_text = "Nenhuma entrada de log encontrada."
        self._show_text(display_text, scroll_to_end=True)

    def toggle_auto_refresh(self) -> None:
        if self.auto_refresh_var.get():
            self._start_auto_refresh()
        else:
            self._cancel_auto_refresh()

    def _start_auto_refresh(self) -> None:
        self._cancel_auto_refresh()
        self._auto_refresh_job = self.after(
            self._refresh_interval_ms, self._auto_refresh_tick
        )

    def _auto_refresh_tick(self) -> None:
        self._auto_refresh_job = None
        if not self.auto_refresh_var.get():
            return
        self.refresh_logs()
        self._start_auto_refresh()

    def _cancel_auto_refresh(self) -> None:
        if self._auto_refresh_job is not None:
            try:
                self.after_cancel(self._auto_refresh_job)
            except Exception:
                pass
            finally:
                self._auto_refresh_job = None

    def _get_line_count(self) -> int:
        value = int(self.lines_var.get())
        return max(10, min(value, 5000))

    def _show_text(self, text: str, *, scroll_to_end: bool = False) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.insert("1.0", text)
        if scroll_to_end:
            self.log_text.see("end")
        self.log_text.configure(state="disabled")

    # --------------------------------------------------------------- Lifecycle ---
    def on_theme_changed(self) -> None:
        """Optional hook invoked by ThemeManager when theme changes."""
        self.update_idletasks()

    def on_close(self) -> None:
        """Gracefully close the viewer."""
        logger.info("Closing LogViewer window")
        self._cancel_auto_refresh()
        if getattr(self.master, "theme_manager", None):
            try:
                self.master.theme_manager.unregister_window(self)
            except Exception:
                pass
        if hasattr(self.master, "_log_viewer") and self.master._log_viewer is self:
            self.master._log_viewer = None
        self.destroy()

    def destroy(self) -> None:
        self._cancel_auto_refresh()
        super().destroy()
