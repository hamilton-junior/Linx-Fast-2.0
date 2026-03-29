"""Settings window for Linx Fast built entirely with CustomTkinter widgets.

Provides tabbed configuration sections with automatic size adjustments and
log preview helpers that stay responsive to the current application state.
"""

import os
import copy
import logging
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from logger_config import set_log_level
from settings_manager import DEFAULT_CONFIG, load_config, save_config

logger = logging.getLogger(__name__)


class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        logger.debug("SettingsWindow.__init__: Starting initialization")
        self.master = master
        self.title("Configurações - Linx Fast")
        try:
            self.transient(master)
        except Exception:
            pass
        try:
            self.grab_set()
        except Exception:
            pass
        try:
            self.protocol("WM_DELETE_WINDOW", self._close)
        except Exception:
            pass

        # config path and loading
        self.config_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "config.json")
        )
        self.config = load_config(self.config_path)
        logger.debug(
            f"SettingsWindow.__init__: Loaded config - theme_name='{self.config.get('theme_name')}', appearance_mode='{self.config.get('appearance_mode')}'"
        )

        # Snapshot initial config so we can detect changes on close
        try:
            self._initial_config = copy.deepcopy(self.config)
            logger.debug(
                f"SettingsWindow.__init__: Snapshot initial config - theme_name='{self._initial_config.get('theme_name')}'"
            )
        except Exception:
            self._initial_config = dict(self.config)
            logger.debug(
                f"SettingsWindow.__init__: Created initial config snapshot (shallow copy) - theme_name='{self._initial_config.get('theme_name')}'"
            )

        # Get theme manager from master window
        self.theme_manager = self.master.theme_manager
        self.theme_manager.register_window(self)
        logger.debug("SettingsWindow.__init__: Registered with theme_manager")

        self._resize_job = None
        self._pending_geometry_capture = True
        self._geometry_padding = (0, 0)
        self._min_geometry = (400, 320)
        self._in_theme_change = False  # Re-entrancy guard for theme updates
        self._in_theme_update = False  # Prevent closing during theme updates

        # UI: tabs
        self.tabs = ctk.CTkTabview(self, command=self._on_tab_changed)
        self.tabs.pack(fill="both", expand=True, padx=12, pady=6)
        self._tab_order = ("Geral", "Aparência", "Avançado")
        for name in self._tab_order:
            self.tabs.add(name)
        self._build_general_tab()
        self._build_appearance_tab()
        self._build_advanced_tab()

        self.after(0, self._initialize_geometry)

    def _initialize_geometry(self):
        if self._pending_geometry_capture is False:
            return
        self.update_idletasks()
        current_tab = self.tabs.get()
        if not current_tab:
            return
        tab_frame = self.tabs.tab(current_tab)
        if tab_frame is None:
            return
        tab_frame.update_idletasks()
        tab_req_width = tab_frame.winfo_reqwidth()
        tab_req_height = tab_frame.winfo_reqheight()
        outer_width = max(self.winfo_width(), tab_req_width)
        outer_height = max(self.winfo_height(), tab_req_height)
        padding_w = max(40, outer_width - tab_req_width)
        padding_h = max(80, outer_height - tab_req_height)
        self._geometry_padding = (padding_w, padding_h)
        self._min_geometry = (
            max(self._min_geometry[0], outer_width),
            max(self._min_geometry[1], outer_height),
        )
        self.minsize(*self._min_geometry)
        self._pending_geometry_capture = False
        self._resize_to_tab(current_tab, animate=False)

    def _on_tab_changed(self, tab_name):
        if not tab_name:
            tab_name = self.tabs.get()
        self._resize_to_tab(tab_name)
        # Logs tab removed; nothing special to do on tab change.

    def _resize_to_tab(self, tab_name=None, animate=True):
        if self._pending_geometry_capture:
            self._initialize_geometry()
            return
        if tab_name is None:
            tab_name = self.tabs.get()
        tab_frame = self.tabs.tab(tab_name)
        if tab_frame is None:
            return
        tab_frame.update_idletasks()
        self.update_idletasks()
        req_width = max(tab_frame.winfo_reqwidth(), self.tabs.winfo_reqwidth())
        req_height = max(tab_frame.winfo_reqheight(), self.tabs.winfo_reqheight())
        pad_w, pad_h = self._geometry_padding
        if pad_w == 0 and pad_h == 0:
            pad_w, pad_h = 60, 80
        target_width = max(req_width + pad_w, self._min_geometry[0])
        target_height = max(req_height + pad_h, self._min_geometry[1])
        self._min_geometry = (
            max(self._min_geometry[0], target_width),
            max(self._min_geometry[1], target_height),
        )
        self.minsize(*self._min_geometry)
        if animate:
            self._animate_resize(target_width, target_height)
        else:
            self.geometry(f"{target_width}x{target_height}")

    def _animate_resize(self, target_width, target_height):
        self._cancel_job("_resize_job")
        current_width = self.winfo_width()
        current_height = self.winfo_height()
        if (
            abs(target_width - current_width) <= 2
            and abs(target_height - current_height) <= 2
        ):
            self.geometry(f"{target_width}x{target_height}")
            return
        steps = 10
        duration = 15

        def step(index=1):
            if index >= steps:
                self.geometry(f"{target_width}x{target_height}")
                self._resize_job = None
                return
            new_w = round(
                current_width + (target_width - current_width) * index / steps
            )
            new_h = round(
                current_height + (target_height - current_height) * index / steps
            )
            self.geometry(f"{new_w}x{new_h}")
            self._resize_job = self.after(duration, lambda: step(index + 1))

        step()

    def _start_log_preview_updates(self):
        # Log preview functionality removed; keep method for compatibility.
        return

    def _refresh_log_preview(self, force=False):
        # Removed: live log preview has been removed from settings.
        return

    def _cancel_job(self, attr_name):
        job_id = getattr(self, attr_name, None)
        if job_id is not None:
            try:
                self.after_cancel(job_id)
            except Exception:
                pass
            setattr(self, attr_name, None)

    def _build_appearance_tab(self):
        logger.debug("_build_appearance_tab: Building appearance tab")
        f = ctk.CTkFrame(self.tabs.tab("Aparência"))
        f.pack(fill="both", expand=True, padx=10, pady=10)

        # Theme selection
        theme_frame = ctk.CTkFrame(f)
        theme_frame.pack(fill="x", padx=10, pady=(5, 10))

        ctk.CTkLabel(theme_frame, text="Tema", font=("", 12, "bold")).pack(
            anchor="w", padx=6, pady=(5, 10)
        )

        # Theme selection
        theme_select_frame = ctk.CTkFrame(theme_frame)
        theme_select_frame.pack(fill="x", padx=6, pady=2)
        ctk.CTkLabel(theme_select_frame, text="Tema atual:").pack(
            side="left", padx=(0, 10)
        )

        # Get available themes (custom + CTkinter defaults)
        theme_dir_path = getattr(self.theme_manager, "themes_dir", None)
        if theme_dir_path is None:
            theme_dir_path = Path("themes")
        else:
            theme_dir_path = Path(theme_dir_path)
        custom_themes = (
            [p.stem for p in theme_dir_path.glob("*.json")] if theme_dir_path.exists() else []
        )
        ctk_themes = ["green", "blue", "dark-blue"]
        theme_files = ctk_themes + custom_themes
        # Use the canonical 'theme_name' key from settings_manager.DEFAULT_CONFIG
        current_theme = self.config.get("theme_name", "green")
        logger.debug(
            f"_build_appearance_tab: Creating theme StringVar with value='{current_theme}'"
        )

        # Create StringVar without triggering callbacks yet
        self.theme_var = ctk.StringVar(value=current_theme)

        logger.debug(f"_build_appearance_tab: Creating theme combobox")
        theme_combo = ctk.CTkComboBox(
            theme_select_frame,
            values=theme_files,
            variable=self.theme_var,
            command=self._on_theme_change,
        )
        theme_combo.pack(side="left", fill="x", expand=True)
        logger.debug(
            f"_build_appearance_tab: Theme combobox created, current value='{self.theme_var.get()}'"
        )

        # Appearance mode selection
        appearance_frame = ctk.CTkFrame(f)
        appearance_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            appearance_frame, text="Modo de Aparência", font=("", 12, "bold")
        ).pack(anchor="w", padx=6, pady=(5, 10))

        mode_select_frame = ctk.CTkFrame(appearance_frame)
        mode_select_frame.pack(fill="x", padx=6, pady=2)
        ctk.CTkLabel(mode_select_frame, text="Modo:").pack(side="left", padx=(0, 10))

        current_mode = self.config.get("appearance_mode", "dark")
        logger.debug(
            f"_build_appearance_tab: Creating appearance StringVar with value='{current_mode}'"
        )

        # Create StringVar without triggering callbacks yet
        self.appearance_var = ctk.StringVar(value=current_mode)

        logger.debug(f"_build_appearance_tab: Creating appearance combobox")
        mode_combo = ctk.CTkComboBox(
            mode_select_frame,
            values=["light", "dark"],
            variable=self.appearance_var,
            command=self._on_appearance_change,
        )
        mode_combo.pack(side="left", fill="x", expand=True)
        logger.debug(
            f"_build_appearance_tab: Appearance combobox created, current value='{self.appearance_var.get()}'"
        )

    def _build_general_tab(self):
        f = ctk.CTkFrame(self.tabs.tab("Geral"))
        f.pack(fill="both", expand=True, padx=10, pady=10)

        # Folders
        folder_frame = ctk.CTkFrame(f)
        folder_frame.pack(fill="x", padx=6, pady=(5, 8))
        ctk.CTkLabel(folder_frame, text="Pastas", font=("", 12, "bold")).pack(
            anchor="w", padx=6
        )

        ctk.CTkLabel(folder_frame, text="Pasta de templates:").pack(
            anchor="w", padx=6, pady=(6, 0)
        )
        self.templates_folder_var = ctk.StringVar(
            value=self.config.get("templates_folder", "templates")
        )
        templates_row = ctk.CTkFrame(folder_frame)
        templates_row.pack(fill="x", padx=6, pady=2)
        self.templates_entry = ctk.CTkEntry(
            templates_row, textvariable=self.templates_folder_var
        )
        self.templates_entry.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(
            templates_row, text="...", width=32, command=self._choose_templates_folder
        ).pack(side="left", padx=6)

        ctk.CTkLabel(folder_frame, text="Pasta de exportação:").pack(
            anchor="w", padx=6, pady=(6, 0)
        )
        self.export_folder_var = ctk.StringVar(
            value=self.config.get("export_folder", "")
        )
        export_row = ctk.CTkFrame(folder_frame)
        export_row.pack(fill="x", padx=6, pady=2)
        self.export_entry = ctk.CTkEntry(
            export_row, textvariable=self.export_folder_var
        )
        self.export_entry.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(
            export_row, text="...", width=32, command=self._choose_export_folder
        ).pack(side="left", padx=6)

        # Toggles
        toggles_frame = ctk.CTkFrame(f)
        toggles_frame.pack(fill="x", padx=6, pady=(10, 6))
        ctk.CTkLabel(toggles_frame, text="Opções", font=("", 12, "bold")).pack(
            anchor="w", padx=6
        )

        self.notify_sound_var = ctk.BooleanVar(
            value=self.config.get("notifications", {}).get("sound", True)
        )
        self.notify_visual_var = ctk.BooleanVar(
            value=self.config.get("notifications", {}).get("visual", True)
        )
        self.animations_var = ctk.BooleanVar(value=self.config.get("animations", True))
        self.autosave_enabled_var = ctk.BooleanVar(
            value=self.config.get("autosave", {}).get("enabled", False)
        )
        self.autosave_timeout_var = ctk.IntVar(
            value=self.config.get("autosave", {}).get("timeout", 60)
        )
        self.smart_search_var = ctk.BooleanVar(
            value=self.config.get("smart_search", True)
        )
        self.enhanced_validation_var = ctk.BooleanVar(
            value=self.config.get("enhanced_validation", True)
        )

        ctk.CTkCheckBox(
            toggles_frame,
            text="Notificações sonoras",
            variable=self.notify_sound_var,
            command=self._on_general_change,
        ).pack(anchor="w", padx=6, pady=4)
        ctk.CTkCheckBox(
            toggles_frame,
            text="Notificações visuais",
            variable=self.notify_visual_var,
            command=self._on_general_change,
        ).pack(anchor="w", padx=6, pady=4)
        ctk.CTkCheckBox(
            toggles_frame,
            text="Animações",
            variable=self.animations_var,
            command=self._on_general_change,
        ).pack(anchor="w", padx=6, pady=4)
        ctk.CTkCheckBox(
            toggles_frame,
            text="Busca inteligente de templates",
            variable=self.smart_search_var,
            command=self._on_general_change,
        ).pack(anchor="w", padx=6, pady=4)
        ctk.CTkCheckBox(
            toggles_frame,
            text="Feedback visual aprimorado",
            variable=self.enhanced_validation_var,
            command=self._on_general_change,
        ).pack(anchor="w", padx=6, pady=4)

        autosave_row = ctk.CTkFrame(toggles_frame)
        autosave_row.pack(fill="x", padx=6, pady=6)
        ctk.CTkCheckBox(
            autosave_row,
            text="Auto-save templates",
            variable=self.autosave_enabled_var,
            command=self._on_general_change,
        ).pack(side="left")
        ctk.CTkLabel(autosave_row, text=" Timeout (s):").pack(side="left", padx=(8, 4))
        ctk.CTkEntry(
            autosave_row, textvariable=self.autosave_timeout_var, width=80
        ).pack(side="left")

        # Save button
        ctk.CTkButton(f, text="Salvar Geral", command=self._save_general).pack(
            anchor="e", padx=8, pady=10
        )

    def _choose_templates_folder(self):
        path = filedialog.askdirectory(
            initialdir=os.getcwd(), title="Escolha a pasta de templates"
        )
        if path:
            self.templates_folder_var.set(path)
            self._on_general_change()

    def _choose_export_folder(self):
        path = filedialog.askdirectory(
            initialdir=os.getcwd(), title="Escolha a pasta de exportação"
        )
        if path:
            self.export_folder_var.set(path)
            self._on_general_change()

    def _on_general_change(self):
        # Apply immediately to config dict and persist lightly
        self.config["templates_folder"] = self.templates_folder_var.get()
        self.config["export_folder"] = self.export_folder_var.get()
        self.config.setdefault("notifications", {})["sound"] = bool(
            self.notify_sound_var.get()
        )
        self.config.setdefault("notifications", {})["visual"] = bool(
            self.notify_visual_var.get()
        )
        self.config["animations"] = bool(self.animations_var.get())
        self.config.setdefault("autosave", {})["enabled"] = bool(
            self.autosave_enabled_var.get()
        )
        try:
            self.config.setdefault("autosave", {})["timeout"] = int(
                self.autosave_timeout_var.get()
            )
        except Exception:
            self.config.setdefault("autosave", {})["timeout"] = 60
        self.config["smart_search"] = bool(self.smart_search_var.get())
        self.config["enhanced_validation"] = bool(self.enhanced_validation_var.get())
        try:
            save_config(self.config, self.config_path)
        except Exception:
            pass

    def _on_theme_change(self, value):
        """Handle theme changes in real-time"""
        if self._in_theme_change:
            logger.debug(f"_on_theme_change: Re-entrancy guard active, skipping (value={value})")
            return

        self._in_theme_change = True
        self._in_theme_update = True  # Prevent window close during theme update
        try:
            logger.debug(f"_on_theme_change: User selected theme '{value}'")
            # Persist under the canonical key name
            self.config["theme_name"] = value
            try:
                # Only set theme if it actually changed to avoid redundant refreshes
                try:
                    current = getattr(self.theme_manager, "theme_name", None)
                except Exception:
                    current = None
                logger.debug(f"_on_theme_change: Current theme='{current}', new='{value}'")
                if value != current:
                    logger.debug(
                        f"_on_theme_change: Applying theme change via theme_manager"
                    )
                    self.theme_manager.set_theme(value)
                    logger.debug(
                        f"_on_theme_change: Theme set - theme_manager will call refresh and on_theme_changed()"
                    )
                else:
                    logger.debug(f"_on_theme_change: Theme unchanged, skipping")
                save_config(self.config, self.config_path)
                logger.debug(f"_on_theme_change: Config saved")
            except Exception as e:
                logger.exception(f"_on_theme_change: Error during theme change: {e}")
                messagebox.showerror("Erro", f"Erro ao alterar tema: {e}")
        finally:
            self._in_theme_change = False
            # Keep _in_theme_update True for a bit longer to allow async callback to complete
            self.after(500, lambda: setattr(self, "_in_theme_update", False))

    def _on_appearance_change(self, value):
        """Handle appearance mode changes in real-time"""
        if self._in_theme_change:
            logger.debug(f"_on_appearance_change: Re-entrancy guard active, skipping (value={value})")
            return

        self._in_theme_change = True
        self._in_theme_update = True  # Prevent window close during theme update
        try:
            logger.debug(f"_on_appearance_change: User selected appearance mode '{value}'")
            self.config["appearance_mode"] = value
            try:
                # Only change appearance mode if it actually differs
                try:
                    current = self.theme_manager.get_current_appearance()
                except Exception:
                    current = None
                logger.debug(f"_on_appearance_change: Current mode='{current}', new='{value}'")
                if value != current:
                    logger.debug(
                        f"_on_appearance_change: Applying appearance mode change via theme_manager"
                    )
                    self.theme_manager.set_appearance_mode(value)
                    logger.debug(
                        f"_on_appearance_change: Mode set - theme_manager will call refresh and on_theme_changed()"
                    )
                else:
                    logger.debug(f"_on_appearance_change: Mode unchanged, skipping")
                save_config(self.config, self.config_path)
                logger.debug(f"_on_appearance_change: Config saved")
            except Exception as e:
                logger.exception(f"_on_appearance_change: Error during mode change: {e}")
                messagebox.showerror("Erro", f"Erro ao alterar modo de aparência: {e}")
        finally:
            self._in_theme_change = False
            # Keep _in_theme_update True for a bit longer to allow async callback to complete
            self.after(500, lambda: setattr(self, "_in_theme_update", False))

    def _build_advanced_tab(self):
        f = ctk.CTkFrame(self.tabs.tab("Avançado"))
        f.pack(fill="both", expand=True, padx=10, pady=10)

        # Log settings section
        log_frame = ctk.CTkFrame(f)
        log_frame.pack(fill="x", padx=10, pady=(5, 10))

        ctk.CTkLabel(
            log_frame, text="Configurações de Log", font=("", 12, "bold")
        ).pack(anchor="w", padx=6, pady=(5, 10))

        # Log level selection
        log_level_frame = ctk.CTkFrame(log_frame)
        log_level_frame.pack(fill="x", padx=6, pady=2)
        ctk.CTkLabel(log_level_frame, text="Nível de Log:").pack(
            side="left", padx=(0, 10)
        )
        self.log_level_var = ctk.StringVar(value=self.config.get("log_level", "INFO"))
        log_level_combo = ctk.CTkComboBox(
            log_level_frame,
            values=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            variable=self.log_level_var,
            command=self._on_log_level_change,
        )
        log_level_combo.pack(side="left", fill="x", expand=True)

        # Log file manipulation removed from UI (kept configurable via config file)

        # Config import/export/reset
        cfg_frame = ctk.CTkFrame(f)
        cfg_frame.pack(fill="x", padx=10, pady=(10, 4))
        ctk.CTkLabel(
            cfg_frame, text="Configuração (Import/Export/Reset)", font=("", 12, "bold")
        ).pack(anchor="w", padx=6, pady=(4, 8))
        btns = ctk.CTkFrame(cfg_frame)
        btns.pack(fill="x", padx=6, pady=6)
        ctk.CTkButton(
            btns, text="Importar Config (JSON)", command=self._import_config
        ).pack(side="left", padx=6)
        ctk.CTkButton(
            btns, text="Exportar Config (JSON)", command=self._export_config
        ).pack(side="left", padx=6)
        ctk.CTkButton(
            btns,
            text="Resetar para Padrão",
            # Use theme defaults for colors so theme changes propagate
            command=self._reset_to_defaults,
        ).pack(side="right", padx=6)

    def _build_logs_tab(self):
        # Logs tab removed. Log viewing/export/clearing is intentionally not
        # available in the UI per project refactor decisions.
        return

    def _open_log_viewer(self):
        # Removed: log viewer is no longer part of the UI.
        raise RuntimeError("Log viewer has been removed from the application UI")

    def _export_logs(self):
        # Export removed from UI
        raise RuntimeError("Exporting logs from the UI is disabled")

    def _on_log_level_change(self, value):
        """Handle log level changes in real-time"""
        self.config["log_level"] = value
        try:
            set_log_level(value)
            save_config(self.config, self.config_path)
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao alterar nível de log: {e}")

    def _clear_logs(self):
        # Clearing logs via UI removed. Keep method stub for compatibility.
        raise RuntimeError("Clearing logs from the UI is disabled")

    def _save_all(self):
        try:
            save_config(self.config, self.config_path)
        except Exception:
            pass

        try:
            set_log_level(self.config.get("log_level", "INFO"))
        except Exception:
            pass

        try:
            if hasattr(self.master, "draw_all_fields"):
                self.master.draw_all_fields()
        except Exception:
            pass

        messagebox.showinfo("Salvo", "Configurações salvas e aplicadas.")

    def _save_general(self):
        # Persist general settings already applied by _on_general_change
        try:
            save_config(self.config, self.config_path)
            messagebox.showinfo("Salvo", "Configurações gerais salvas.")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar configuração: {e}")

    def _import_config(self):
        path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*")]
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                cfg = f.read()
            import json

            obj = json.loads(cfg)
            # Merge and save
            self.config.update(obj)
            save_config(self.config, self.config_path)
            messagebox.showinfo("Importado", "Configuração importada com sucesso.")
            # Apply some settings immediately; config uses 'theme_name'
            if "theme_name" in obj:
                try:
                    self.theme_manager.set_theme(obj["theme_name"])
                except Exception:
                    pass
            if "appearance_mode" in obj:
                try:
                    self.theme_manager.set_appearance_mode(obj["appearance_mode"])
                except Exception:
                    pass
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao importar configuração: {e}")

    def _export_config(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".json", filetypes=[("JSON files", "*.json")]
        )
        if not path:
            return
        try:
            import json

            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            messagebox.showinfo("Exportado", f"Config exportada para: {path}")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao exportar configuração: {e}")

    def _reset_to_defaults(self):
        if not messagebox.askyesno("Resetar", "Restaurar configurações para o padrão?"):
            return
        try:
            # Overwrite config with DEFAULT_CONFIG
            self.config = DEFAULT_CONFIG.copy()
            save_config(self.config, self.config_path)
            messagebox.showinfo(
                "Resetado",
                "Configurações restauradas para o padrão. Reinicie o app se necessário.",
            )
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao resetar configuração: {e}")

    def _close(self):
        logger.debug("_close: Closing settings window")
        
        # Prevent closing during theme updates
        if self._in_theme_update:
            logger.debug("_close: Theme update in progress, deferring window close")
            return
        
        if getattr(self, "_is_closing", False):
            logger.debug("_close: Already closing, skipping")
            return
        self._is_closing = True

        self._cancel_job("_resize_job")
        # log preview job removed
        try:
            self.grab_release()
        except Exception:
            pass

        # Check if any non-theme config changed
        # (Theme/appearance changes are already applied in real-time via _on_theme_change/_on_appearance_change)
        try:
            changed = False
            # Skip theme_name and appearance_mode - they're already applied via real-time handlers
            keys_to_check = ("animations", "fonts")
            for k in keys_to_check:
                old = self._initial_config.get(k)
                new = self.config.get(k)
                if old != new:
                    logger.debug(f"_close: Config changed - {k}: {old} → {new}")
                    changed = True
                    break

            if changed:
                logger.debug("_close: Non-theme config changed, saving")
                # Persist final config
                try:
                    save_config(self.config, self.config_path)
                except Exception:
                    pass
            else:
                logger.debug(
                    "_close: No config changes detected (theme already applied in real-time)"
                )

        except Exception as e:
            logger.exception(f"_close: Error checking config changes: {e}")

        # Unregister and destroy as usual
        logger.debug("_close: Unregistering from theme manager")
        if hasattr(self, "theme_manager"):
            try:
                self.theme_manager.unregister_window(self)
            except Exception:
                pass
        if hasattr(self.master, "_settings_window") and getattr(
            self.master, "_settings_window"
        ) is self:
            self.master._settings_window = None
            logger.debug("_close: Cleared _settings_window reference")
        try:
            super().destroy()
            logger.debug("_close: Window destroyed")
        except Exception:
            pass

    def destroy(self):
        """Ensure destroy always routes through cleanup logic."""
        if getattr(self, "_is_closing", False):
            try:
                super().destroy()
            except Exception:
                pass
            return
        self._close()

    def _update_colors_only(self):
        """Lightweight color-only update called from main window's apply_theme_globally.

        Does NOT trigger theme change callbacks - only updates widget colors.
        """
        logger.debug("_update_colors_only: Updating settings window colors")
        try:
            if hasattr(self, "theme_manager"):
                try:
                    # Prefer CTkToplevel theme default if present
                    try:
                        fg = self.theme_manager.get_theme_default_color(
                            ctk.CTkToplevel, "fg_color"
                        )
                        try:
                            self.configure(fg_color=fg)
                            logger.debug(f"_update_colors_only: Applied background color")
                        except Exception:
                            pass
                    except Exception:
                        pass

                    # Apply theme recursively to all children/widgets
                    try:
                        self.theme_manager.apply_theme_to(self)
                        logger.debug(f"_update_colors_only: Applied theme to all widgets")
                    except Exception:
                        pass
                except Exception:
                    pass
            try:
                self.update_idletasks()
            except Exception:
                pass
            logger.debug("_update_colors_only: Complete")
        except Exception:
            logger.exception("_update_colors_only: Error")

    def on_theme_changed(self):
        """Called by ThemeManager when the global theme/appearance changes.

        Apply the current theme to this window and attempt to reconfigure the
        toplevel background so it matches the active theme immediately.
        """
        logger.debug("on_theme_changed: Called by theme_manager")
        self._in_theme_update = True
        try:
            if hasattr(self, "theme_manager"):
                try:
                    # Prefer CTkToplevel theme default if present
                    try:
                        fg = self.theme_manager.get_theme_default_color(
                            ctk.CTkToplevel, "fg_color"
                        )
                        try:
                            self.configure(fg_color=fg)
                        except Exception:
                            pass
                    except Exception:
                        pass

                    # Apply theme recursively to all children/widgets
                    try:
                        self.theme_manager.apply_theme_to(self)
                    except Exception:
                        pass
                except Exception:
                    pass
            try:
                self.update_idletasks()
            except Exception:
                pass
            logger.debug("on_theme_changed: Complete")
        except Exception:
            logger.exception("on_theme_changed: Error")
        finally:
            self._in_theme_update = False
