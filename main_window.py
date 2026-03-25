import customtkinter as ctk
import pyperclip
import json
import os
import re
import datetime
import sys
import csv
import logging
import tkinter as tk
from template_editor import TemplateEditor
from template_manager import TemplateManager
from theme_manager import ThemeManager
from dpm import DailyPasswordManager
from settings_window import SettingsWindow
from settings_manager import load_config, save_config
from customtkinter import CTkInputDialog
from logger_config import auto_log_functions

# Get the module logger
logger = logging.getLogger(__name__)

try:
    from version import VERSION, COMMIT, BUILD_DATE
except ImportError:
    VERSION, COMMIT, BUILD_DATE = "dev", "dev", "dev"

# Configure logger for this module
logger = logging.getLogger("main_window")

# Define quais símbolos são exportados
__all__ = ["TemplateApp", "placeholder_engine"]


from utils.placeholder_engine import placeholder_engine, PlaceholderEngine


@auto_log_functions
class TemplateApp(ctk.CTk):
    def __init__(self):
        logger.info("Iniciando TemplateApp...")

        if sys.platform == "win32":
            import ctypes

            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(0)
            except Exception as e:
                logger.warning(f"Could not set DPI awareness: {e}")

        super().__init__()
        self.title("Linx Fast 2.0")
        self.geometry("360x535")
        self.visual_feedback_enabled = True
        self._after_ids = set()  # IDs dos afters agendados

        # Carrega config de campos expansíveis
        self.expandable_fields = self.load_expandable_fields_config()

        # Load persistent config (used for field definitions and other settings)
        try:
            self.config = load_config()
        except Exception:
            self.config = {}

        # Inicializar o ThemeManager primeiro (ele será usado por outras janelas)
        # Use canonical key 'theme_name' from settings_manager
        self.theme_name = self.config.get("theme_name", "green")
        self.appearance_mode = self.config.get("appearance_mode", "dark")

        # Criar e configurar o ThemeManager global
        self.theme_manager = ThemeManager(
            theme_name=self.theme_name, mode=self.appearance_mode
        )
        # Registrar a janela principal
        self.theme_manager.register_window(self)

        # Inicialização das outras classes
        self.template_manager = TemplateManager()
        # Load persistent config (used for field definitions and other settings)
        try:
            self.config = load_config()
        except Exception:
            self.config = {}
        self.password_manager = DailyPasswordManager()
        self.fixed_fields = [
            "Nome",
            "Problema Relatado",
            "CNPJ",
            "Telefone",
            "Email",
            "Protocolo",
            "Procedimento Executado",
        ]
        self.dynamic_fields = []
        self.entries = {}
        self.field_widgets = {}
        self.fixed_field_modes = {}

        self.current_template = "Selecione o template..."
        self.current_template_display = ctk.StringVar(
            value=self.template_manager.meta.get_display_name(self.current_template)
        )

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_main_interface()
        self.load_template_placeholders()

        # Garante largura mínima para caber todos os botões e campos
        self.update_idletasks()
        self.minsize(392, 525)  # 392px cobre selector + botões + paddings

        self._safe_after(0, self.apply_saved_geometry)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_main_interface(self):
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.main_frame.grid_columnconfigure(0, weight=1)

        selector_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        selector_frame.grid(row=0, column=0, sticky="w", padx=5, pady=(5, 5))

        self.pin_button = ctk.CTkButton(
            selector_frame, text="📍", command=self.toggle_always_on_top, width=30
        )
        self.pin_button.pack(side="left", padx=(0, 5))

        # Criando um frame para o selector garantir que ele não empurre o botão de configuração
        selector_container = ctk.CTkFrame(selector_frame, fg_color="transparent")
        selector_container.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.template_selector = ctk.CTkOptionMenu(
            selector_container,
            variable=self.current_template_display,
            values=self.template_manager.get_display_names(),
            command=self.on_template_change,
            width=300,
            dynamic_resizing=False,  # Evita que o menu cresça além do width especificado
        )
        self.template_selector.pack(side="left", fill="x", expand=True)

        # Botão de Configurações ao lado do seletor de template
        self.settings_button = ctk.CTkButton(
            selector_frame,
            text="⚙️",
            width=32,
            anchor="center",
            command=self.open_settings,
        )
        self.settings_button.pack(side="left", padx=(5, 0))

        # Favorite and Protected quick toggles for templates
        try:
            self.favorite_button = ctk.CTkButton(
                selector_frame,
                text="⭐",
                width=32,
                anchor="center",
                command=self.toggle_current_template_favorite,
            )
            self.favorite_button.pack(side="left", padx=(5, 0))

            self.protect_button = ctk.CTkButton(
                selector_frame,
                text="🔒",
                width=32,
                anchor="center",
                command=self.toggle_current_template_protected,
            )
            self.protect_button.pack(side="left", padx=(5, 0))
        except Exception:
            pass

        self.form_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.form_frame.grid(row=1, column=0, sticky="nsew")
        self.form_frame.grid_columnconfigure(0, weight=1)

        self.draw_all_fields()

        # Botão de Senha Diária com imagem colorida
        from PIL import Image

        # Caminho absoluto para o ícone
        base_dir = os.path.dirname(os.path.abspath(__file__))
        key_icon_path = os.path.join(base_dir, "assets", "icons", "pwkey.png")
        try:
            key_img = Image.open(key_icon_path).resize((22, 22))
            key_ctk_image = ctk.CTkImage(
                light_image=key_img, dark_image=key_img, size=(22, 22)
            )
        except Exception as e:
            key_ctk_image = None

        self.btn_daily_password = ctk.CTkButton(
            self.main_frame,
            text="",
            image=key_ctk_image,
            command=self.handle_daily_password,
            width=36,
            height=30,
            anchor="center",
            fg_color="transparent",
            hover_color=("#E0E0E0", "#222222"),  # Ajuste conforme o modo (light, dark)
            border_width=0,
        )
        self.btn_daily_password.grid(
            sticky="w", row=2, column=0, padx=(5, 0), pady=(5, 0)
        )
        self.btn_daily_password.bind(
            "<Button-3>",
            lambda e: (
                self.password_manager.set_today_password(None),
                self.show_snackbar("Senha diária resetada!", toast_type="info"),
            ),
        )
        self.btn_daily_password.image = key_ctk_image  # Evita garbage collection

        # --- Restore main action buttons below the fields ---
        # Botão de Limpar Campos (direita)
        try:
            self.btn_limpar_campos = ctk.CTkButton(
                self.main_frame,
                text="❌",
                fg_color="#A94444",
                hover_color="#912F2F",
                anchor="right",
                width=3,
                height=30,
                command=self.limpar_campos,
            )
            self.btn_limpar_campos.grid(row=2, column=0, pady=(5, 0), sticky="e")
            # Mark intentional custom-colour widgets so ThemeManager won't overwrite them
            try:
                self.btn_limpar_campos._custom_theme_overrides = True
            except Exception:
                pass
            # Tooltip para o botão de limpar campos
            try:
                self.create_tooltip(
                    self.btn_limpar_campos, "Limpar todos os campos", fg_color="#A94444"
                )
            except Exception:
                pass
        except Exception:
            # Não bloquear se CTkButton falhar em ambientes estranhos
            pass

        # Botões principais (mantemos referências para permitir atualização dinâmica de tema)
        try:
            default_btn_fg = self.theme_manager.get_theme_default_color(
                ctk.CTkButton, "fg_color"
            )
        except Exception:
            default_btn_fg = None

        # Copiar
        try:
            self.copy_button = ctk.CTkButton(
                self.main_frame,
                text="Copiar para área de transferência",
                fg_color=default_btn_fg,
                hover_color=(
                    self.theme_manager.get_darker_color(default_btn_fg, 0.08)
                    if default_btn_fg
                    else None
                ),
                command=self.copy_template,
            )
            self.copy_button.grid(row=2, column=0, pady=(5, 5))
        except Exception:
            pass

        # Visualizar
        try:
            self.preview_button = ctk.CTkButton(
                self.main_frame,
                text="Visualizar Resultado",
                fg_color=default_btn_fg,
                hover_color=(
                    self.theme_manager.get_darker_color(default_btn_fg, 0.08)
                    if default_btn_fg
                    else None
                ),
                command=self.preview_template,
            )
            self.preview_button.grid(row=3, column=0, pady=(5, 5))
        except Exception:
            pass

        # Editar (logo abaixo dos outros botões)
        try:
            self.edit_button = ctk.CTkButton(
                self.main_frame,
                text="Editar Templates",
                fg_color=default_btn_fg,
                hover_color=(
                    self.theme_manager.get_darker_color(default_btn_fg, 0.08)
                    if default_btn_fg
                    else None
                ),
                command=self.open_template_editor,
            )
            self.edit_button.grid(row=4, column=0, pady=(5, 5))
        except Exception:
            pass

        # Botão de Adicionar Campo
        try:
            self.add_btn = ctk.CTkButton(
                self.main_frame,
                text="+ Adicionar Campo",
                width=150,
                height=30,
                command=self.prompt_new_field,
                fg_color="#333",
                hover_color="#444",
                font=ctk.CTkFont(size=12),
            )
            self.add_btn.grid(row=5, column=0, pady=(5, 2))
            try:
                self.add_btn._custom_theme_overrides = True
            except Exception:
                pass
        except Exception:
            pass

        # Botão de Modo Simples
        try:
            tmp = ctk.CTkButton(
                self.main_frame,
                text="Modo Simples",
                fg_color="#5E35B1",
                hover_color="#4527A0",
                command=self.open_quick_mode,
            )
            tmp.grid(row=6, column=0, pady=(5, 5))
            try:
                tmp._custom_theme_overrides = True
            except Exception:
                pass
        except Exception:
            pass

        # --- Frame inferior para label de crédito e botão de info alinhados ---
        bottom_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        bottom_frame.grid(row=100, column=0, sticky="ew", pady=0, padx=0)
        bottom_frame.grid_columnconfigure(0, weight=0)  # Espaço Vazio
        bottom_frame.grid_columnconfigure(1, weight=1)  # Label centralizada
        bottom_frame.grid_columnconfigure(2, weight=0)  # Botão Info

        # Botão de Bug (esquerda)
        self.info_button = ctk.CTkButton(
            bottom_frame,
            text="?",
            width=32,
            anchor="center",
            command=self.on_bug_button_click,
        )
        self.info_button.grid(row=0, column=2, sticky="w", padx=(8, 2))

        # Label de Créditos do Autor (centralizada)
        label_autor = ctk.CTkLabel(
            bottom_frame,
            text="By Hamilton Junior",
            font=ctk.CTkFont(size=10, slant="italic"),
            text_color="#888888",
            anchor="s",
            justify="center",
        )
        label_autor.grid(row=0, column=1, sticky="ew", padx=(2, 2))
        try:
            label_autor._custom_theme_overrides = True
        except Exception:
            pass

        self.main_frame.grid_rowconfigure(100, weight=0)

        self._init_undo_redo()
        self._bind_undo_redo_shortcuts()

    def _create_toplevel(self, parent=None):
        """Helper to create a CTkToplevel and register it with ThemeManager.

        Use this instead of calling ctk.CTkToplevel(...) directly so all popups
        are registered and receive theme updates automatically.
        """
        p = parent or self
        win = ctk.CTkToplevel(p)
        try:
            if hasattr(self, "theme_manager") and self.theme_manager:
                try:
                    self.theme_manager.register_window(win)
                except Exception:
                    pass
        except Exception:
            pass
        return win

    def on_bug_button_click(self):
        # Abre uma janela com links para formulários do NocoDB e exibe uma imagem da pasta /assets/icons/images
        import webbrowser
        import os

        # Lista de botões: (nome, url, nome_da_imagem_alternativa)
        botoes_info = [
            (
                "Envio de Templates",
                "https://app.nocodb.com/#/nc/form/99e96b28-cb03-4710-9318-7b1d5849d9e0",
                "template.png",
            ),
            (
                "Sugestões",
                "https://app.nocodb.com/#/nc/form/0058474a-0f28-4d3d-af60-1727a29ab431",
                "sugestao.png",
            ),
            (
                "Report-a-bug",
                "https://app.nocodb.com/#/nc/form/5dd88074-bbf3-457f-b105-816652c79ddf",
                "bug.png",
            ),
        ]
        win = self._create_toplevel()
        win.title("Informações & Feedback")
        win.geometry("250x285")
        win.resizable(True, True)
        win.transient(self)
        win.grab_set()

        # --- Exibe uma pequena imagem no topo ---
        ctk.CTkLabel(
            win, text="Contribua com o app!", font=ctk.CTkFont(size=15, weight="bold")
        ).pack(pady=(8, 8))

        try:
            from PIL import Image

            base_dir = os.path.dirname(os.path.abspath(__file__))
            img_path = os.path.join(base_dir, "assets", "images", "logo.png")
            pil_image = Image.open(img_path)
            image = ctk.CTkImage(
                light_image=pil_image, dark_image=pil_image, size=(64, 64)
            )
            img_label = ctk.CTkLabel(win, image=image, text="", cursor="hand2")
            img_label.pack(pady=(12, 2))

            def open_logo_link(event=None):
                webbrowser.open_new(
                    "https://app.nocodb.com/#/base/d45b6596-528f-4eec-9ff5-4793831c07be"
                )

            img_label.bind("<Button-1>", open_logo_link)
        except Exception as e:
            print(f"Erro ao carregar imagem: {e}")
            img_label = None
            image = None

        # Crie os botões e associe cada um à sua imagem alternativa
        alt_images = {}
        btns = {}
        for name, url, img_file in botoes_info:
            btn = ctk.CTkButton(
                win, text=name, width=150, command=lambda u=url: webbrowser.open_new(u)
            )
            btn.pack(pady=6)
            btns[name] = btn
            # Carrega a imagem alternativa
            alt_img_path = os.path.join(base_dir, "assets", "images", img_file)
            if os.path.exists(alt_img_path):
                from PIL import Image

                pil_alt = Image.open(alt_img_path)
                alt_images[name] = ctk.CTkImage(
                    light_image=pil_alt, dark_image=pil_alt, size=(64, 64)
                )
            else:
                alt_images[name] = image  # fallback

            # Bind individual para cada botão, usando o nome como chave
            def make_set_img_alt(btn_name):
                def _set_img_alt(event):
                    if img_label and alt_images.get(btn_name):
                        img_label.configure(image=alt_images[btn_name])

                return _set_img_alt

            btn.bind("<Enter>", make_set_img_alt(name))
            btn.bind(
                "<Leave>",
                lambda e: (
                    img_label.configure(image=image) if img_label and image else None
                ),
            )

        ctk.CTkLabel(
            win,
            text="Ao enviar um formulário, gentileza informar seu email do Teams para facilitar o contato.",
            font=ctk.CTkFont(size=10),
            wraplength=245,
            text_color="#888",
        ).pack(pady=(10, 8))

    # TODO: Mover métodos auxiliares para módulos separados (fields.py, visual_feedback.py, utils.py)
    # TODO: Implementar feedback visual aprimorado nas próximas etapas

    def _init_undo_redo(self):
        self._undo_stack = []
        self._redo_stack = []
        self._undo_limit = 50  # Limite de histórico

    def _get_fields_snapshot(self):
        # Salva valores dos campos atuais
        snapshot = {}
        for k, v in self.entries.items():
            try:
                snapshot[k] = v.get()
            except Exception:
                try:
                    snapshot[k] = v.get("1.0", "end-1c")
                except Exception:
                    snapshot[k] = ""
        # Também salva ordem dos campos dinâmicos
        snapshot["_dynamic_fields"] = list(self.dynamic_fields)
        return snapshot

    def _restore_fields_snapshot(self, snapshot):
        self._restoring_undo_redo = True
        try:
            # Otimização: só redesenha tudo se a estrutura mudou
            current_keys = list(self.entries.keys())
            snapshot_keys = [k for k in snapshot.keys() if k != "_dynamic_fields"]

            # Checa se a estrutura mudou (campos diferentes, ordem diferente, tipos diferentes)
            structure_changed = current_keys != snapshot_keys or any(
                (
                    isinstance(self.entries.get(k), ctk.CTkTextbox)
                    != isinstance(snapshot.get(k, ""), str)
                    and "\n" in str(snapshot.get(k, ""))
                )
                for k in snapshot_keys
                if k in self.entries
            )

            if "_dynamic_fields" in snapshot and self.dynamic_fields != list(
                snapshot["_dynamic_fields"]
            ):
                structure_changed = True

            if structure_changed:
                # Redesenha tudo (caso campos mudaram, ordem mudou, ou tipo mudou)
                if "_dynamic_fields" in snapshot:
                    self.dynamic_fields = list(snapshot["_dynamic_fields"])
                self.draw_all_fields()
                for k in self.entries:
                    valor_antigo = snapshot.get(k, None)
                    entry = self.entries[k]
                    if valor_antigo not in (None, ""):
                        if isinstance(entry, ctk.CTkTextbox):
                            entry.delete("1.0", "end")
                            entry.insert("1.0", valor_antigo)
                        else:
                            entry.delete(0, "end")
                            entry.insert(0, valor_antigo)
            else:
                # Só restaura valores dos widgets existentes
                for k, entry in self.entries.items():
                    valor_antigo = snapshot.get(k, None)
                    if valor_antigo is not None:
                        if isinstance(entry, ctk.CTkTextbox):
                            entry.delete("1.0", "end")
                            entry.insert("1.0", valor_antigo)
                        else:
                            entry.delete(0, "end")
                            entry.insert(0, valor_antigo)
        finally:
            self._restoring_undo_redo = False

    def _handle_textbox_focusout(
        self, event, field_name: str, textbox: ctk.CTkTextbox, to_entry_fn
    ) -> None:
        """Gerencia a perda de foco de um campo textbox"""
        # Verifica se o textbox ainda existe
        if not hasattr(textbox, "winfo_exists") or not textbox.winfo_exists():
            logger.debug(f"Textbox {field_name} não existe mais")
            return

        # Se for um campo expansível, atualiza para a cor normal se estiver em erro
        if field_name in getattr(self, "expandable_fields", []):
            try:
                if textbox.cget("border_color") == self.ERROR_COLOR:
                    self._update_single_field_border(field_name, textbox)
            except Exception as e:
                logger.debug(f"Erro ao verificar cor da borda de {field_name}: {e}")
                return
        else:
            # Para outros campos, valida normalmente
            self._validate_field_and_update_color(textbox, field_name)

        # Verifica se o campo ainda tem foco após um pequeno delay
        def _check_focus() -> None:
            # Se o widget foi destruído, retorna
            if not hasattr(textbox, "winfo_exists") or not textbox.winfo_exists():
                return

            # Captura o widget com foco atual de forma segura
            try:
                focused_widget = textbox.focus_get()
            except Exception:
                focused_widget = None

            # Se não tem mais foco, converte para entry
            if focused_widget != textbox:
                try:
                    current_border_color = textbox.cget("border_color")
                    # Primeiro converte para entry
                    to_entry_fn(field_name)

                    def _after_convert() -> None:
                        # Verifica se o widget ainda existe após a conversão
                        if field_name in self.entries:
                            entry = self.entries.get(field_name)
                            if (
                                entry
                                and hasattr(entry, "winfo_exists")
                                and entry.winfo_exists()
                            ):
                                # Para campos expansíveis, sempre usa a cor normal
                                if field_name in getattr(self, "expandable_fields", []):
                                    self._update_single_field_border(field_name, entry)
                                else:
                                    # Para outros campos, mantém a cor anterior
                                    entry.configure(border_color=current_border_color)
                                    self._validate_field_and_update_color(
                                        entry, field_name
                                    )

                    # Agenda a atualização da cor apenas se o widget ainda existir
                    if hasattr(self, "_safe_after"):
                        self._safe_after(10, _after_convert)
                except Exception as e:
                    logger.debug(f"Erro ao converter campo {field_name}: {e}")

        # Aguarda um momento para verificar o estado do foco
        if hasattr(self, "_safe_after"):
            self._safe_after(50, _check_focus)

    def _validate_field_and_update_color(self, widget, field_name):
        """Valida o campo e atualiza a cor de acordo com o conteúdo"""
        if isinstance(widget, ctk.CTkTextbox):
            value = widget.get("1.0", "end-1c").strip()
        else:
            value = widget.get().strip()

        logger.debug(f"Validando campo: {field_name}")
        logger.debug(f"  Tipo de widget: {type(widget).__name__}")
        logger.debug(
            f"  É expansível: {field_name in getattr(self, 'expandable_fields', [])}"
        )
        logger.debug(f"  Valor: {value}")

        # Se for um campo expansível, nunca fica vermelho
        if field_name in getattr(self, "expandable_fields", []):
            # Se estiver vermelho, volta para a cor normal
            if widget.cget("border_color") == self.ERROR_COLOR:
                self._update_single_field_border(field_name, widget)
            return

        # Para outros campos, atualiza a cor com base no valor
        current_color = widget.cget("border_color")
        if not value:
            if current_color != self.ERROR_COLOR:
                widget.configure(border_color=self.ERROR_COLOR)
        else:
            if current_color == self.ERROR_COLOR:
                # Se saiu do estado de erro, faz a animação de sucesso
                self.animate_field_success(widget)
                self._update_single_field_border(field_name, widget)
            elif current_color != widget._apply_appearance_mode(widget._border_color):
                # Se a cor atual é diferente da que deveria ser
                self._update_single_field_border(field_name, widget)

    def _push_undo(self):
        if getattr(self, "_restoring_undo_redo", False):
            return
        if not hasattr(self, "_undo_stack"):
            self._init_undo_redo()
        snapshot = self._get_fields_snapshot()
        if not self._undo_stack or self._undo_stack[-1] != snapshot:
            self._undo_stack.append(snapshot)
            if len(self._undo_stack) > self._undo_limit:
                self._undo_stack.pop(0)
        # Limpa o redo ao novo push
        self._redo_stack.clear()

    def undo_fields(self, event=None):
        if not hasattr(self, "_undo_stack"):
            self._init_undo_redo()
        if len(self._undo_stack) > 1:
            current = self._undo_stack.pop()
            self._redo_stack.append(current)
            snapshot = self._undo_stack[-1]
            self._restore_fields_snapshot(snapshot)
            self.show_snackbar("Desfeito!", toast_type="info")

    def redo_fields(self, event=None):
        if not hasattr(self, "_redo_stack"):
            self._init_undo_redo()
        if self._redo_stack:
            snapshot = self._redo_stack.pop()
            self._restoring_undo_redo = True
            try:
                self._restore_fields_snapshot(snapshot)
                self._undo_stack.append(snapshot)
            finally:
                self._restoring_undo_redo = False
            self.show_snackbar("Refeito!", toast_type="info")

    def _bind_undo_redo_shortcuts(self):
        self.bind_all("<Control-z>", self.undo_fields)
        self.bind_all("<Control-y>", self.redo_fields)

    def on_theme_changed(self):
        """Called by ThemeManager when the global theme or appearance changes.

        Reapplies appearance recursively and updates key widget colours that
        were created with theme-dependent colours so the UI updates immediately.
        """
        try:
            if not hasattr(self, "theme_manager") or not self.theme_manager:
                return
            # ThemeManager already applies colors to all widgets before calling this method.
            # We only need to handle custom/special overrides here.

            # Update key buttons to use theme defaults (ensures colours update even if
            # they were created earlier with theme-derived colours)
            default_btn_fg = self.theme_manager.get_theme_default_color(
                ctk.CTkButton, "fg_color"
            )
            hover = self.theme_manager.get_darker_color(default_btn_fg, 0.08)

            for attr in (
                "copy_button",
                "preview_button",
                "edit_button",
                "add_btn",
                "pin_button",
                "settings_button",
                "favorite_button",
                "protect_button",
                "btn_daily_password",
            ):
                try:
                    w = getattr(self, attr, None)
                    if w:
                        try:
                            w.configure(fg_color=default_btn_fg)
                        except Exception:
                            pass
                        try:
                            w.configure(hover_color=hover)
                        except Exception:
                            pass
                except Exception:
                    pass

            # Special case: keep the 'limpar' button visually distinct (darker)
            try:
                if hasattr(self, "btn_limpar_campos") and self.btn_limpar_campos:
                    del_color = self.theme_manager.get_darker_color(
                        default_btn_fg, 0.35
                    )
                    try:
                        self.btn_limpar_campos.configure(fg_color=del_color)
                    except Exception:
                        pass
                    try:
                        self.btn_limpar_campos.configure(
                            hover_color=self.theme_manager.get_darker_color(
                                del_color, 0.1
                            )
                        )
                    except Exception:
                        pass
            except Exception:
                pass

        except Exception:
            logger.exception("Error in on_theme_changed of main window")

    # Note: a more comprehensive reload_theme_and_interface exists later in this
    # file and will be used by ThemeManager when available. We intentionally do
    # not alias it here to avoid duplicate definitions.

    # TODO: Mover métodos auxiliares para módulos separados (fields.py, visual_feedback.py, utils.py)
    # TODO: Implementar undo/redo e feedback visual aprimorado nas próximas etapas

    def draw_all_fields(self):
        # Salva valores antigos, tanto de Entry quanto de Textbox
        saved_values = {}
        for k, v in self.entries.items():
            try:
                saved_values[k] = v.get()
            except Exception:
                try:
                    saved_values[k] = v.get("1.0", "end-1c")
                except Exception:
                    saved_values[k] = ""

        # Para cada widget no form_frame
        for widget in self.form_frame.winfo_children():
            widget.destroy()
        self.entries.clear()
        self.field_widgets.clear()

        row = 0
        for field in self.fixed_fields:
            self._draw_field(field, row, saved_values.get(field, ""), is_dynamic=False)
            row += 1
        for field in self.dynamic_fields:
            self._draw_field(field, row, saved_values.get(field, ""), is_dynamic=True)
            row += 1

        self.adjust_window_height()

        # Define a cor de erro padrão
        self.ERROR_COLOR = "#FF0000"  # Vermelho vibrante

        # Atualiza as cores das bordas dos campos
        self._update_field_borders()

    def _update_single_field_border(self, field_name, entry):
        """Atualiza a cor da borda de um campo específico baseado no template atual."""
        if not hasattr(self, "theme_manager"):
            return

        # Obtém a cor padrão do tema
        default_border = self.theme_manager.get_theme_default_color(
            ctk.CTkEntry, "border_color"
        )

        # Escurece a cor padrão para campos não usados no template
        darker_border = self.theme_manager.get_darker_color(default_border, 0.3)

        # Se não há template selecionado, mantém a cor padrão escura
        if (
            not self.current_template
            or self.current_template == "Selecione o template..."
        ):
            entry.configure(border_color=darker_border)
            return

        # Analisa o template atual
        template = self.template_manager.get_template(self.current_template)
        if not template:
            entry.configure(border_color=darker_border)
            return

        # Extrai campos normais
        normal_fields = self.template_manager.extract_placeholders(template)
        field_in_template = False

        # Verifica campos normais
        if field_name in normal_fields:
            if (
                field_name not in placeholder_engine.handlers
                and not field_name.startswith("Agora")
            ):
                field_in_template = True

        # Verifica campos condicionais
        if not field_in_template:
            for match in re.findall(
                r"\$([a-zA-Z0-9 _\-çÇáéíóúãõâêîôûÀ-ÿ\[\]%:/]+)\?", template
            ):
                if match.strip() == field_name:
                    if (
                        field_name not in placeholder_engine.handlers
                        and not field_name.startswith("Agora")
                    ):
                        field_in_template = True
                        break

        # Configura a cor baseada no uso do campo no template
        if field_in_template:
            highlight_color = self.theme_manager.get_lighter_color(
                default_border, 0.6  # Mantendo o fator de claridade em 0.6
            )
            entry.configure(border_color=highlight_color)
        else:
            entry.configure(border_color=darker_border)

    def _reset_field_value(self, widget: ctk.CTkBaseClass) -> None:
        """Limpa o valor de um campo, tratando cada tipo de widget adequadamente"""
        if not widget:
            return

        try:
            # Primeiro verifica se o widget ainda existe
            exists = hasattr(widget, "winfo_exists") and widget.winfo_exists()

            # Se não existe mais, retorna
            if not exists and not isinstance(widget, (ctk.StringVar, ctk.BooleanVar)):
                return

            # Primeiro tenta a estratégia específica para cada tipo de widget
            if isinstance(widget, ctk.CTkTextbox):
                widget.delete("1.0", "end")
            elif isinstance(widget, ctk.CTkEntry):
                widget.delete(0, "end")
            elif isinstance(
                widget, (ctk.StringVar, ctk.BooleanVar)
            ):  # Para RadioButtons e outros Vars
                widget.set("")
            elif isinstance(widget, (ctk.CTkSwitch, ctk.CTkCheckBox)):
                try:
                    if hasattr(widget, "deselect"):
                        widget.deselect()
                    else:
                        # Fallback se deselect não existir
                        widget._check_state = False
                        widget._update_image()
                except Exception as e:
                    logger.debug(
                        f"Erro ao desmarcar widget {type(widget).__name__}: {e}"
                    )
            else:
                # Para outros widgets, tenta em ordem:
                # 1. delete("1.0", "end") - método específico para texto multilinha
                # 2. delete(0, "end") - método padrão para campos de texto
                # 3. set("") - comum em variables
                # 4. deselect() - comum em selecionáveis
                try:
                    if hasattr(widget, "delete"):
                        try:
                            widget.delete("1.0", "end")
                        except Exception:
                            widget.delete(0, "end")
                    elif hasattr(widget, "set"):
                        widget.set("")
                    elif hasattr(widget, "deselect"):
                        widget.deselect()
                except Exception as e:
                    logger.debug(f"Erro ao limpar widget {type(widget).__name__}: {e}")

        except Exception as e:
            logger.warning(f"Erro ao limpar campo: {e}")
            logger.debug(f"Tipo do widget: {type(widget)}")

    def _update_field_borders(self, placeholders=None):
        """Atualiza as cores das bordas dos campos baseado no template atual."""
        if not hasattr(self, "theme_manager") or not hasattr(self, "entries"):
            return

        # Obtém a cor padrão do tema
        default_border = self.theme_manager.get_theme_default_color(
            ctk.CTkEntry, "border_color"
        )

        # Escurece a cor padrão para campos não usados no template
        darker_border = self.theme_manager.get_darker_color(default_border, 0.3)

        # Primeiro configura TODOS os campos para a cor escurecida
        for entry in self.entries.values():
            if isinstance(entry, (ctk.CTkEntry, ctk.CTkTextbox)):
                entry.configure(border_color=darker_border)

        # Se não há template selecionado, mantém todos na cor padrão
        if (
            not self.current_template
            or self.current_template == "Selecione o template..."
        ):
            return

        # Se não recebeu placeholders, analisa o template atual
        if placeholders is None:
            template = self.template_manager.get_template(self.current_template)
            if not template:
                return

            # Obtém todos os campos do template atual
            placeholders = set()

            # Extrai campos normais
            normal_fields = self.template_manager.extract_placeholders(template)
            for field in normal_fields:
                # Remove campos automáticos
                if field not in placeholder_engine.handlers and not field.startswith(
                    "Agora"
                ):
                    placeholders.add(field.strip())

            # Adiciona campos condicionais (com ?), exceto automáticos
            for match in re.findall(
                r"\$([a-zA-Z0-9 _\-çÇáéíóúãõâêîôûÀ-ÿ\[\]%:/]+)\?", template
            ):
                field = match.strip()
                # Adiciona apenas se não for um campo automático
                if field not in placeholder_engine.handlers and not field.startswith(
                    "Agora"
                ):
                    placeholders.add(field)

        # Processa cada campo apenas uma vez
        processed_fields = set()
        for field_name, entry in self.entries.items():
            if field_name in processed_fields:
                continue

            if isinstance(entry, (ctk.CTkEntry, ctk.CTkTextbox)):
                # Já resetamos para a cor padrão no início, então só precisamos
                # alterar os campos que estão no template atual
                if field_name in placeholders:
                    # Campos usados no template atual ficam com borda muito mais clara
                    highlight_color = self.theme_manager.get_lighter_color(
                        default_border,
                        0.6,  # Aumentando o fator de claridade de 0.3 para 0.6
                    )
                    entry.configure(border_color=highlight_color)
                processed_fields.add(field_name)

    def _should_wrap_label(self, text):
        return len(text) > 15 and " " in text

    def _draw_field(self, name, row, value="", is_dynamic=True):
        row_frame = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        row_frame.grid(row=row, column=0, sticky="ew", padx=10, pady=4)
        row_frame.grid_columnconfigure(1, weight=1)

        # Detecta tipo especial de campo
        field_type = "entry"
        field_label = name
        radio_options = None

        m = re.match(r"\[(checkbox|switch)\](.+)", name)
        if m:
            field_type = m.group(1)
            field_label = m.group(2).strip()
        else:
            m = re.match(r"\[radio:([^\]]+)\](.+)", name)
            if m:
                field_type = "radio"
                radio_options = [opt.strip() for opt in m.group(1).split("|")]
                field_label = m.group(2).strip()

        # LABEL
        label = ctk.CTkLabel(
            row_frame, text=field_label, anchor="w", justify="left", width=160
        )
        label.grid(row=0, column=0, sticky="w", padx=(0, 5))

        # --- Campo inteligente ---
        # Checkbox: $[checkbox]Aceite$
        # Switch: $[switch]Ativo$
        # Radio: $[radio:Sim|Não|Talvez]Opção$
        # Condicional: $[checkbox]Aceite?Aceito|Não aceito$

        if field_type == "checkbox":
            var = ctk.BooleanVar(value=(value == "1" or value is True))
            entry = ctk.CTkCheckBox(row_frame, text="", variable=var)
            entry.grid(row=0, column=1, sticky="w")
            self.entries[name] = entry
        elif field_type == "switch":
            var = ctk.StringVar(value=value if value else "Sim")
            entry = ctk.CTkSwitch(
                row_frame,
                text="",
                variable=var,
                onvalue="Sim",
                offvalue="Não",
            )
            entry.grid(row=0, column=1, sticky="w")
            self.entries[name] = entry
        elif field_type == "radio" and radio_options:
            var = ctk.StringVar(
                value=value if value in radio_options else radio_options[0]
            )
            radio_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
            radio_frame.grid(row=0, column=1, sticky="w")
            for i, opt in enumerate(radio_options):
                btn = ctk.CTkRadioButton(radio_frame, text=opt, variable=var, value=opt)
                btn.pack(side="left", padx=2)
            self.entries[name] = var
        # --- Para campos expansíveis definidos pelo usuário ---
        elif name in getattr(self, "expandable_fields", []):
            entry = ctk.CTkEntry(row_frame, placeholder_text=f"{name}")
            if value not in (None, ""):
                entry.insert(0, value)
            entry.grid(row=0, column=1, sticky="ew")
            self.entries[name] = entry

            def to_textbox(field_name=name, val=None):
                current_widget = self.entries[field_name]
                if isinstance(current_widget, ctk.CTkTextbox):
                    return current_widget
                if val is None:
                    val = current_widget.get()
                # Se o campo estiver em estado de erro, atualiza para a cor normal
                if current_widget.cget("border_color") == self.ERROR_COLOR:
                    self._update_single_field_border(field_name, current_widget)
                current_widget.grid_forget()
                textbox = ctk.CTkTextbox(
                    row_frame, height=60, wrap="word", border_width=2
                )
                if val:
                    textbox.insert("1.0", val)
                textbox.grid(row=0, column=1, sticky="ew")
                # Configura a cor da borda para a cor normal
                self._update_single_field_border(field_name, textbox)
                self.entries[field_name] = textbox
                textbox.focus()
                # Adiciona validação de campo vazio
                textbox.bind(
                    "<FocusOut>",
                    lambda e, fn=field_name, tb=textbox: self._handle_textbox_focusout(
                        e, fn, tb, to_entry
                    ),
                )
                # Undo/redo: salva snapshot a cada digitação
                textbox.bind("<KeyRelease>", lambda e: self._push_undo())

                # TAB navega para o próximo campo (transforma em Entry antes de avançar)
                def on_tab(e, fn=field_name):
                    to_entry(fn)
                    self._safe_after(1, lambda: self._focus_next_field_linear(fn))
                    return "break"

                def on_shift_tab(e, fn=field_name):
                    to_entry(fn)
                    self._safe_after(1, lambda: self._focus_prev_field_linear(fn))
                    return "break"

                textbox.bind("<Tab>", on_tab)
                textbox.bind("<ISO_Left_Tab>", on_shift_tab)
                # Também suporta <Shift-Tab> para compatibilidade
                textbox.bind("<Shift-Tab>", on_shift_tab)
                self.adjust_window_height()
                return textbox

            def to_entry(field_name=name):
                current_widget = self.entries[field_name]
                if not isinstance(current_widget, ctk.CTkTextbox):
                    return
                val = current_widget.get("1.0", "end-1c")
                # Se o campo estiver em estado de erro, atualiza para a cor normal
                if current_widget.cget("border_color") == self.ERROR_COLOR:
                    self._update_single_field_border(field_name, current_widget)
                current_widget.grid_forget()
                entry = ctk.CTkEntry(row_frame, placeholder_text=f"{field_name}")
                if val:
                    entry.insert(0, val)
                entry.grid(row=0, column=1, sticky="ew")
                # Configura a cor da borda para a cor normal
                self._update_single_field_border(field_name, entry)
                # Adiciona validação na perda de foco
                entry.bind(
                    "<FocusOut>",
                    lambda e, ent=entry, fn=field_name: self._validate_field_and_update_color(
                        ent, fn
                    ),
                )
                self.entries[field_name] = entry
                # Se o campo estiver vazio, mostra o placeholder
                if not val:
                    entry.delete(0, "end")
                    entry.configure(placeholder_text=field_name)
                entry.bind("<FocusIn>", lambda e, fn=field_name: to_textbox(fn))
                entry.bind("<KeyRelease>", lambda e: self._push_undo())
                # Verifica se precisa fazer animação de sucesso
                if (
                    val
                    and getattr(current_widget, "border_color", None)
                    == self.ERROR_COLOR
                ):
                    self.animate_field_success(entry)
                # Redimensiona a janela ao voltar para Entry
                self.adjust_window_height()

            # Intercepta TAB e Shift+TAB no Entry ANTES de expandir
            def on_entry_tab(event, fn=name):
                if event.keysym == "Tab":
                    self._focus_next_field_linear(fn)
                    return "break"
                elif event.keysym in ("ISO_Left_Tab", "Shift_L", "Shift_R"):
                    # Transforma em Entry (caso esteja em Textbox) e foca o campo anterior
                    to_entry(fn)
                    self._safe_after(1, lambda: self._focus_prev_field_linear(fn))
                    return "break"
                return "break"

            entry.bind("<Tab>", on_entry_tab)
            entry.bind("<ISO_Left_Tab>", on_entry_tab)
            entry.bind("<Shift-Tab>", on_entry_tab)
            # Expande para textbox ao focar com mouse/click
            entry.bind("<FocusIn>", lambda e, fn=name: to_textbox(fn))

        # --- Para os demais campos, mantém lógica padrão ---
        else:
            # Decide modo: entry ou textbox (apenas para campos fixos)
            mode = "entry"
            if not is_dynamic:
                mode = self.fixed_field_modes.get(name, "entry")

            def toggle_fixed_field_mode(event=None, field_name=name):
                # Troca apenas o widget do campo clicado, sem redesenhar tudo
                current_widget = self.entries[field_name]
                row_frame = current_widget.master
                label = row_frame.grid_slaves(row=0, column=0)[0]
                # Salva valor ANTES de destruir o widget
                if isinstance(current_widget, ctk.CTkEntry):
                    val = current_widget.get()
                elif isinstance(current_widget, ctk.CTkTextbox):
                    val = current_widget.get("1.0", "end-1c")
                else:
                    val = ""
                # Agora sim, remove e destrói todos os widgets da coluna 1
                for widget in row_frame.grid_slaves(row=0, column=1):
                    widget.grid_forget()
                    widget.destroy()
                # Alterna entre Entry e Textbox
                if isinstance(current_widget, ctk.CTkEntry):
                    textbox = ctk.CTkTextbox(
                        row_frame, height=60, wrap="word", border_width=2
                    )
                    if val:
                        textbox.insert("1.0", val)
                    textbox.grid(row=0, column=1, sticky="ew")
                    self.entries[field_name] = textbox
                    # Remove binds antigos e adiciona apenas um bind para voltar para entry
                    label.unbind("<Button-3>")
                    label.bind(
                        "<Button-3>",
                        lambda e, fn=field_name: toggle_fixed_field_mode(e, fn),
                    )
                    # TAB e Shift+TAB navegam entre campos (cíclico)
                    textbox.bind(
                        "<Tab>",
                        lambda e, fn=field_name: (
                            self._focus_next_field_linear(fn),
                            "break",
                        ),
                    )
                    textbox.bind(
                        "<Shift-Tab>",
                        lambda e, fn=field_name: (
                            self._focus_prev_field_linear(fn),
                            "break",
                        ),
                    )
                    # Redimensiona a janela para manter botões visíveis
                    self.adjust_window_height()
                elif isinstance(current_widget, ctk.CTkTextbox):
                    entry = ctk.CTkEntry(row_frame, placeholder_text=f"{field_name}")
                    if val:
                        entry.insert(0, val)
                    entry.grid(row=0, column=1, sticky="ew")
                    self.entries[field_name] = entry
                    # Remove binds antigos e adiciona apenas um bind para ir para textbox
                    label.unbind("<Button-3>")
                    label.bind(
                        "<Button-3>",
                        lambda e, fn=field_name: toggle_fixed_field_mode(e, fn),
                    )
                    # Redimensiona a janela para manter botões visíveis
                    self.adjust_window_height()
                    # Atualiza o highlight dos campos
                    self._update_field_borders()

            if not is_dynamic:
                label.bind("<Button-3>", toggle_fixed_field_mode)

            # Inicialização padrão (Entry ou Textbox)
            if not is_dynamic and mode == "textbox":
                entry = ctk.CTkEntry(row_frame, placeholder_text=f"{name}")
                if value not in (None, ""):
                    entry.insert(0, value)
                entry.grid(row=0, column=1, sticky="ew")
                self.entries[name] = entry
                # Troca imediatamente para textbox
                toggle_fixed_field_mode(None, name)
            else:
                entry = ctk.CTkEntry(row_frame, placeholder_text=f"{name}")
                if value not in (None, ""):
                    entry.insert(0, value)
                entry.grid(row=0, column=1, sticky="ew")
                # Atualiza as bordas do novo campo
                self._update_single_field_border(name, entry)
                self.entries[name] = entry
                entry.bind("<KeyRelease>", lambda e: self._push_undo())

        if is_dynamic:
            btn_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
            btn_frame.grid(row=0, column=2, sticky="e", padx=(5, 0))

            up_btn = ctk.CTkButton(
                btn_frame, text="↑", width=30, command=lambda: self.move_field(name, -1)
            )
            down_btn = ctk.CTkButton(
                btn_frame, text="↓", width=30, command=lambda: self.move_field(name, 1)
            )
            del_btn = ctk.CTkButton(
                btn_frame,
                text="✕",
                width=30,
                fg_color="#A94444",
                command=lambda: self.remove_field(name),
            )

            up_btn.pack(side="left", padx=2)
            down_btn.pack(side="left", padx=2)
            del_btn.pack(side="left", padx=2)

        # Apply any field definition (mask/regex/default/required)
        try:
            widget = self.entries.get(name)
            if widget is not None:
                self._apply_field_definition(name, widget)
        except Exception:
            pass

    def _apply_field_definition(self, name, widget):
        """Apply runtime field definition (from config field_definitions) to a widget.

        Supported keys in definition: mask (telefone, CNPJ, numeric), regex (string),
        default, required (bool).
        """
        try:
            if not hasattr(self, "config"):
                return
            defs = self.config.get("field_definitions", {}) or {}

            # Normalize key: remove any leading [checkbox], [switch], [radio:...] blocks
            key = re.sub(r"^\[[^\]]+\]", "", name).strip()

            definition = defs.get(key) or defs.get(name)
            if not definition:
                return

            mask = definition.get("mask")
            regex = definition.get("regex")
            default = definition.get("default")
            required = definition.get("required", False)

            # Avoid re-binding handlers multiple times on the same object
            already = getattr(widget, "_field_def_applied", False)
            if already:
                return
            try:
                setattr(widget, "_field_def_applied", True)
            except Exception:
                pass

            # Helper to get/set widget value
            def _get_value(w):
                try:
                    if isinstance(w, ctk.CTkTextbox):
                        return w.get("1.0", "end-1c").strip()
                    # Tk variables (for radio) stored directly in entries
                    if isinstance(w, (ctk.StringVar, tk.StringVar, tk.Variable)):
                        return w.get().strip()
                    # Checkboxes/switches may store a variable attribute
                    if hasattr(w, "get") and not hasattr(w, "grid"):
                        return w.get().strip()
                    if hasattr(w, "get"):
                        return w.get().strip()
                except Exception:
                    return ""
                return ""

            def _set_value(w, val):
                try:
                    if isinstance(w, ctk.CTkTextbox):
                        w.delete("1.0", "end")
                        w.insert("1.0", val)
                        return
                    if isinstance(w, (ctk.StringVar, tk.StringVar, tk.Variable)):
                        w.set(val)
                        return
                    # For CTkEntry-like
                    if hasattr(w, "delete") and hasattr(w, "insert"):
                        w.delete(0, "end")
                        w.insert(0, val)
                        return
                    # For checkboxes/switches try variable attribute
                    var = getattr(w, "variable", None) or getattr(w, "_variable", None)
                    if var is not None and hasattr(var, "set"):
                        var.set(val)
                        return
                    # Fallback: try set/select
                    try:
                        if str(val).lower() in ("1", "true", "sim", "yes", "on"):
                            if hasattr(w, "select"):
                                w.select()
                        else:
                            if hasattr(w, "deselect"):
                                w.deselect()
                    except Exception:
                        pass
                except Exception:
                    pass

            # Apply default value if provided and field is empty
            try:
                if default is not None:
                    cur = _get_value(widget)
                    if not cur:
                        _set_value(widget, str(default))
            except Exception:
                pass

            # Regex validation on focusout
            if regex:
                try:
                    pattern = re.compile(regex)

                    def _validate_regex(event=None, w=widget, pat=pattern):
                        val = _get_value(w)
                        if not val:
                            # Let required/empty logic handle empties
                            return
                        try:
                            ok = bool(pat.fullmatch(val))
                        except Exception:
                            ok = False
                        if not ok:
                            try:
                                w.configure(border_color=self.ERROR_COLOR)
                            except Exception:
                                pass
                        else:
                            try:
                                # restore border according to template usage
                                self._update_single_field_border(name, w)
                            except Exception:
                                pass

                    # Bind focusout (works for Entry/Textbox); for variables we can skip
                    if hasattr(widget, "bind"):
                        widget.bind("<FocusOut>", _validate_regex)
                except Exception:
                    pass

            # Required: ensure on focusout we validate presence
            if required:
                try:
                    if hasattr(widget, "bind"):
                        widget.bind(
                            "<FocusOut>",
                            lambda e, w=widget, fn=name: self._validate_field_and_update_color(
                                w, fn
                            ),
                        )
                except Exception:
                    pass

            # Masks / formatting on key release
            if mask:
                try:

                    def _only_digits(s):
                        return re.sub(r"\D", "", s or "")

                    def _format_telefone(s):
                        d = _only_digits(s)
                        if len(d) <= 2:
                            return d
                        if len(d) <= 6:
                            return f"({d[:2]}) {d[2:]}"
                        if len(d) <= 10:
                            return f"({d[:2]}) {d[2:6]}-{d[6:]}"
                        # celular com 9 dígitos
                        return f"({d[:2]}) {d[2:7]}-{d[7:11]}"

                    def _format_cnpj(s):
                        d = _only_digits(s)
                        parts = []
                        if len(d) >= 2:
                            parts.append(d[:2])
                        if len(d) >= 5:
                            parts.append(d[2:5])
                        if len(d) >= 8:
                            parts.append(d[5:8])
                        if len(d) >= 12:
                            rest = d[8:12]
                            end = d[12:14]
                        else:
                            rest = d[8:12]
                            end = d[12:14]
                        formatted = ""
                        if len(d) <= 2:
                            formatted = d
                        elif len(d) <= 5:
                            formatted = f"{d[:2]}.{d[2:]}"
                        elif len(d) <= 8:
                            formatted = f"{d[:2]}.{d[2:5]}.{d[5:8]}"
                        elif len(d) <= 12:
                            formatted = f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}"
                        else:
                            formatted = (
                                f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:14]}"
                            )
                        return formatted

                    def _format_numeric(s):
                        return _only_digits(s)

                    def _make_formatter(fmt_name):
                        def _fmt(event=None, w=widget, name=fmt_name):
                            try:
                                if isinstance(w, ctk.CTkTextbox):
                                    cur = w.get("1.0", "end-1c")
                                    if fmt_name == "telefone":
                                        out = _format_telefone(cur)
                                    elif fmt_name == "CNPJ":
                                        out = _format_cnpj(cur)
                                    else:
                                        out = _format_numeric(cur)
                                    if out != cur:
                                        w.delete("1.0", "end")
                                        w.insert("1.0", out)
                                else:
                                    cur = w.get()
                                    if fmt_name == "telefone":
                                        out = _format_telefone(cur)
                                    elif fmt_name == "CNPJ":
                                        out = _format_cnpj(cur)
                                    else:
                                        out = _format_numeric(cur)
                                    if out != cur:
                                        # move cursor to end after replace
                                        w.delete(0, "end")
                                        w.insert(0, out)
                            except Exception:
                                pass

                        return _fmt

                    fmt = str(mask)
                    formatter = _make_formatter(fmt)
                    # expose formatter for testing and direct invocation
                    try:
                        setattr(widget, "_field_formatter", formatter)
                    except Exception:
                        pass
                    if hasattr(widget, "bind"):
                        widget.bind("<KeyRelease>", formatter)
                        # Apply formatter once immediately so pre-filled values are normalized.
                        try:
                            formatter()
                        except Exception:
                            pass
                        # Also schedule a follow-up run shortly after to catch
                        # programmatic inserts that occur immediately after apply.
                        try:
                            if hasattr(widget, "after"):
                                widget.after(50, formatter)
                                widget.after(150, formatter)
                                widget.after(300, formatter)
                        except Exception:
                            pass
                except Exception:
                    pass

        except Exception:
            # do not propagate errors from optional enhancements
            return

    def save_field_order(self):
        try:
            config = load_config()
            if "field_orders" not in config:
                config["field_orders"] = {}

            config["field_orders"][self.current_template] = self.dynamic_fields
            save_config(config)
        except Exception as e:
            print(f"[ERRO ao salvar ordem dos campos]: {e}")

    def load_field_order(self):
        """Carrega a ordem dos campos dinâmicos do template atual, se existir."""
        try:
            config = load_config()
            field_orders = config.get("field_orders", {})
            order = field_orders.get(self.current_template)
            if order:
                # Garante que só mantenha campos realmente presentes no template
                self.dynamic_fields = [
                    f for f in order if f in self.dynamic_fields
                ] + [f for f in self.dynamic_fields if f not in order]
        except Exception as e:
            print(f"[ERRO ao carregar ordem dos campos]: {e}")

    def move_field(self, field, direction):
        self._push_undo()
        idx = self.dynamic_fields.index(field)
        new_idx = idx + direction
        if 0 <= new_idx < len(self.dynamic_fields):
            self.dynamic_fields[idx], self.dynamic_fields[new_idx] = (
                self.dynamic_fields[new_idx],
                self.dynamic_fields[idx],
            )
            self.draw_all_fields()
            self.save_field_order()

    def remove_field(self, field):
        self._push_undo()
        if field in self.dynamic_fields:
            self.dynamic_fields.remove(field)
            self.draw_all_fields()
            self.save_field_order()

    def prompt_new_field(self):
        self._push_undo()
        popup = CTkInputDialog(
            text="Nome do novo campo (placeholder):", title="Adicionar Campo"
        )
        field_name = popup.get_input()
        if field_name:
            name = self.add_dynamic_field_from_placeholder(field_name)
            # If successfully added, ensure UI updates
            if name and name not in self.entries:
                try:
                    self.draw_all_fields()
                except Exception:
                    pass

    def _sanitize_field_name(self, raw: str) -> str:
        """
        Given a raw placeholder-like string, extract a clean field name.

        Handles forms like:
        - $[dropdown:Opt1|Opt2]Field$
        - $Field(arg1,arg2)$
        - Field?cond|alt
        - $Name|Default$
        Returns the cleaned field name (no args, brackets, defaults, or surrounding $).
        """
        if not raw:
            return ""
        s = raw.strip()
        # Strip surrounding $ if present
        if s.startswith("$") and s.endswith("$") and len(s) >= 2:
            s = s[1:-1].strip()

        # Remove top-level default (split on first '|' not inside brackets/paren)
        depth_br = 0
        depth_par = 0
        split_idx = None
        for i, ch in enumerate(s):
            if ch == "[":
                depth_br += 1
            elif ch == "]":
                if depth_br > 0:
                    depth_br -= 1
            elif ch == "(":
                depth_par += 1
            elif ch == ")":
                if depth_par > 0:
                    depth_par -= 1
            elif ch == "|" and depth_br == 0 and depth_par == 0 and split_idx is None:
                split_idx = i
                break
        if split_idx is not None:
            s = s[:split_idx].strip()

        # If conditional syntax with '?', take the part before '?'
        if "?" in s:
            s = s.split("?", 1)[0].strip()

        # If starts with a bracketed prefix like [dropdown:..]Name, remove the bracketed part
        if s.startswith("["):
            try:
                end = s.index("]")
                s = s[end + 1 :].strip()
            except ValueError:
                # malformed, ignore
                pass

        # Remove any trailing args (first '(' at top level)
        depth_br = 0
        depth_par = 0
        cut_idx = None
        for i, ch in enumerate(s):
            if ch == "[":
                depth_br += 1
            elif ch == "]":
                if depth_br > 0:
                    depth_br -= 1
            elif ch == "(":
                if depth_br == 0:
                    cut_idx = i
                    break
        if cut_idx is not None:
            s = s[:cut_idx].strip()

        # Final cleanup: remove any remaining surrounding punctuation
        return s.strip()

    def add_dynamic_field_from_placeholder(self, raw: str):
        """Add a dynamic field using a raw placeholder/string; sanitize name first.

        Returns the sanitized name or empty string if none.
        """
        name = self._sanitize_field_name(raw)
        if not name:
            return ""
        if name not in self.dynamic_fields:
            self.dynamic_fields.append(name)
            # Redraw fields and persist order
            try:
                self.draw_all_fields()
            except Exception:
                pass
            try:
                self.save_field_order()
            except Exception:
                pass
        return name

    def limpar_campos(self):
        """Limpa todos os campos e restaura suas cores padrão."""
        logger.info("Limpando todos os campos")
        self._push_undo()

        # Usa o método seguro para limpar cada campo
        for name, entry in self.entries.items():
            try:
                # Primeiro reseta o valor
                self._reset_field_value(entry)

                # Depois configura o placeholder se aplicável
                if isinstance(entry, ctk.CTkEntry):
                    entry.configure(placeholder_text=name)
                elif isinstance(entry, ctk.CTkTextbox):
                    # Para textbox, insere string vazia para garantir estado consistente
                    entry.insert("1.0", "")
            except Exception as e:
                logger.warning(f"Erro ao limpar campo {name}: {e}")

        # Atualiza o highlight dos campos após limpar
        self._update_field_borders()
        self.show_snackbar("Campos limpos!", toast_type="info")

    def _focus_next_field_linear(self, current_name):
        keys = list(self.entries.keys())
        try:
            idx = keys.index(current_name)
            next_key = keys[(idx + 1) % len(keys)]  # cíclico
            entry = self.entries[next_key]
            # Se for StringVar (radio), pula para o próximo campo
            if isinstance(entry, ctk.StringVar):
                self._focus_next_field_linear(next_key)
            else:
                entry.focus()
        except (ValueError, IndexError):
            pass

    def _focus_prev_field_linear(self, current_name):
        keys = list(self.entries.keys())
        try:
            idx = keys.index(current_name)
            # Volta para o campo anterior (cíclico)
            prev_idx = (idx - 1) % len(keys)
            for _ in range(len(keys)):
                prev_key = keys[prev_idx]
                entry = self.entries[prev_key]
                # Pula radios
                if isinstance(entry, ctk.StringVar):
                    prev_idx = (prev_idx - 1) % len(keys)
                    continue
                # Se for Textbox expansível, converte para Entry antes de focar
                if isinstance(entry, ctk.CTkTextbox):
                    entry.event_generate("<FocusOut>")
                    self._safe_after(1, lambda k=prev_key: self.entries[k].focus())
                else:
                    entry.focus()
                break
        except (ValueError, IndexError):
            pass

    def toggle_always_on_top(self):
        current = self.attributes("-topmost")
        new_state = not current
        self.attributes("-topmost", new_state)
        self.pin_button.configure(
            fg_color=(
                "green"
                if new_state
                else self.theme_manager.get_theme_default_color(
                    ctk.CTkButton, "fg_color"
                )
            )
        )
        self.pin_button.configure(text="📌" if new_state else "📍")
        if new_state:
            self.show_snackbar("PIN ativado!", toast_type="info")
        else:
            self.show_snackbar("PIN desativado!", toast_type="info")

    def copy_template(self):
        # Validate if a template is selected
        if (
            not self.current_template
            or self.current_template == "Selecione o template..."
        ):
            self.show_snackbar(
                "Selecione um template antes de copiar!", toast_type="error"
            )
            return

        template = self.template_manager.get_template(self.current_template)
        tem_vazios = False

        # Descobre quais campos realmente estão no template atual
        placeholders = set(self.template_manager.extract_placeholders(template))

        cond_fields = set()
        for match in re.findall(
            r"\$([a-zA-Z0-9 _\-çÇáéíóúãõâêîôûÀ-ÿ\[\]%:/]+)\?", template
        ):
            cond_fields.add(match.strip())

        all_fields = placeholders | cond_fields

        # Filtra apenas os campos presentes no template e que estão na interface
        fields_to_validate = [k for k in self.entries if k in all_fields]

        # 1. Coleta valores dos campos
        field_values = {}
        for key in fields_to_validate:
            entry = self.entries[key]
            # Só chama winfo_exists se for widget tkinter
            if hasattr(entry, "winfo_exists") and not entry.winfo_exists():
                continue
            # Campos inteligentes
            if isinstance(entry, ctk.CTkCheckBox):
                value = "Sim" if entry.get() else "Não"
            elif isinstance(entry, ctk.CTkSwitch):
                value = str(entry.get())
            elif isinstance(entry, ctk.StringVar):
                value = str(entry.get())
            elif isinstance(entry, ctk.CTkTextbox):
                value = entry.get("1.0", "end-1c")
            else:
                value = str(entry.get())
            field_values[key] = value
            if not value or value == "Não":
                if isinstance(entry, (ctk.CTkEntry, ctk.CTkTextbox)):
                    entry.configure(border_color=self.ERROR_COLOR)
                    # Ao ganhar foco, atualiza para a cor do template (se fizer parte)
                    entry.bind(
                        "<FocusIn>",
                        lambda e, fn=key, ent=entry: self._update_single_field_border(
                            fn, ent
                        ),
                    )
                    # Ao perder foco, verifica se tem valor: se tiver faz animação de sucesso e depois volta cor do template,
                    # se não tiver volta pra vermelho
                    entry.bind(
                        "<FocusOut>",
                        lambda e, ent=entry: (
                            self.animate_field_success(ent)
                            if (
                                ent.get("1.0", "end-1c")
                                if isinstance(ent, ctk.CTkTextbox)
                                else ent.get()
                            )
                            else None
                        ),
                    )
                tem_vazios = True

        # 2. Processa lógica condicional no template
        template = self.process_conditionals(template, field_values)

        # 3. Substitui placeholders simples
        for key, value in field_values.items():
            template = template.replace(f"${key}$", value if value else "")

        # 4. Substitui placeholders dinâmicos
        template = placeholder_engine.process(template)

        pyperclip.copy(template)
        self.pulse_window()
        if not tem_vazios:
            self.show_snackbar("Copiado com sucesso!", toast_type="success")
        else:
            self.show_snackbar("Existem campos em branco!", toast_type="warning")

    def preview_template(self):
        template = self.template_manager.get_template(self.current_template)
        # Coleta valores dos campos
        field_values = {}
        for key, entry in self.entries.items():
            if isinstance(entry, ctk.CTkCheckBox):
                value = "Sim" if entry.get() else "Não"
            elif isinstance(entry, ctk.CTkSwitch):
                value = str(entry.get())
            elif isinstance(entry, ctk.StringVar):
                value = str(entry.get())
            elif isinstance(entry, ctk.CTkTextbox):
                value = entry.get("1.0", "end-1c")
            else:
                value = str(entry.get())
            field_values[key] = value
        # Processa lógica condicional
        template = self.process_conditionals(template, field_values)
        # Substitui placeholders simples
        for key, value in field_values.items():
            template = template.replace(f"${key}$", value if value else "")
        # Substitui placeholders dinâmicos
        template = placeholder_engine.process(template)

        preview = self._create_toplevel()
        preview.title("Visualização do Template")
        preview.geometry("600x400")
        preview.transient(self)
        preview.grab_set()

        box = ctk.CTkTextbox(preview, wrap="word")
        box.insert("1.0", template)
        box.configure(state="disabled")
        box.pack(expand=True, fill="both", padx=20, pady=20)

    def load_template_placeholders(self):
        """Atualiza a interface para refletir os campos do template atual."""
        logger.info("Carregando placeholders do template")
        # Guarda os valores atuais dos campos
        old_values = {}
        for k, v in self.entries.items():
            if isinstance(v, ctk.CTkTextbox):
                old_values[k] = v.get("1.0", "end-1c")
            else:
                old_values[k] = v.get()

        if (
            not self.current_template
            or self.current_template == "Selecione o template..."
        ):
            # Se não há template selecionado, reseta todas as bordas
            self._update_field_borders()
            return

        template_content = self.template_manager.get_template(self.current_template)
        if not template_content:
            return

        # Extrai todos os campos do template (normais e condicionais)
        placeholders = set(self.template_manager.extract_placeholders(template_content))

        # Também considera campos usados em condicionais
        for match in re.findall(
            r"\$([a-zA-Z0-9 _\-çÇáéíóúãõâêîôûÀ-ÿ\[\]%:/]+)\?", template_content
        ):
            placeholders.add(match.strip())

        # Remove placeholders automáticos
        automatic_placeholders = set(placeholder_engine.handlers.keys())
        placeholders = {
            p
            for p in placeholders
            if p not in automatic_placeholders and not p.startswith("Agora")
        }

        # Atualiza as cores das bordas para refletir os campos do novo template
        self._update_field_borders(placeholders)

        if not hasattr(self, "theme_manager") or not hasattr(self, "entries"):
            return

        # Obtém a cor base da borda do tema atual
        border_color = self.theme_manager.get_theme_default_color(
            ctk.CTkEntry, "border_color"
        )
        # Cria uma versão mais clara para campos não utilizados
        lighter_border = self.theme_manager.get_lighter_color(border_color, 0.3)

        # Marca todos os campos como não utilizados primeiro
        for field_name, entry in self.entries.items():
            if isinstance(entry, (ctk.CTkEntry, ctk.CTkTextbox)):
                entry.configure(border_color=lighter_border)

        # Destaca os campos que são usados no template atual
        template = self.template_manager.get_template(self.current_template)
        if template:
            placeholders = self.template_manager.extract_placeholders(template)
            for field in placeholders:
                if field in self.entries and isinstance(
                    self.entries[field], (ctk.CTkEntry, ctk.CTkTextbox)
                ):
                    self.entries[field].configure(border_color=border_color)

        # Também considera campos usados em condicionais
        for match in re.findall(
            r"\$([a-zA-Z0-9 _\-çÇáéíóúãõâêîôûÀ-ÿ\[\]%:/]+)\?", template_content
        ):
            field = match.strip()
            if field in self.entries and isinstance(
                self.entries[field], (ctk.CTkEntry, ctk.CTkTextbox)
            ):
                self.entries[field].configure(border_color=border_color)

        # Atualiza as cores das bordas
        self._update_field_borders(
            placeholders
        )  # Filtra placeholders automáticos (handlers do PlaceholderEngine)
        automatic_placeholders = set(placeholder_engine.handlers.keys())

        # Também filtra placeholders do tipo $Agora[...]$
        def is_automatic(ph):
            if ph in automatic_placeholders:
                return True
            if ph == "Agora":
                return True
            if ph.startswith("Agora[") and ph.endswith("]"):
                return True
            return False

        # REDEFINIR CAMPOS DINÂMICOS com base no novo template
        cond_fields = set()
        for match in re.findall(
            r"\$([a-zA-Z0-9 _\-çÇáéíóúãõâêîôûÀ-ÿ\[\]%:/]+)\?", template_content
        ):
            cond_fields.add(match.strip())

        all_fields = set(placeholders) | cond_fields

        self.dynamic_fields = [
            ph
            for ph in all_fields
            if ph not in self.fixed_fields and not is_automatic(ph)
        ]

        # Carrega ordem persistida, se houver
        if hasattr(self, "load_field_order") and callable(self.load_field_order):
            self.load_field_order()

        # RECONSTRUIR OS CAMPOS
        self.draw_all_fields()
        # RESTAURAR APENAS VALORES NÃO NULOS/NÃO VAZIOS
        for k in self.entries:
            valor_antigo = old_values.get(k, None)
            entry = self.entries[k]
            if valor_antigo not in (None, ""):
                # Primeiro limpa o campo com segurança
                self._reset_field_value(entry)
                # Depois insere o valor antigo
                if isinstance(entry, ctk.CTkTextbox):
                    entry.insert("1.0", valor_antigo)
                elif isinstance(entry, ctk.CTkEntry):
                    entry.insert(0, valor_antigo)
                elif isinstance(entry, (ctk.CTkSwitch, ctk.CTkCheckBox)):
                    try:
                        if str(valor_antigo).lower() in ("true", "1", "yes", "on"):
                            if hasattr(entry, "select"):
                                entry.select()
                        else:
                            if hasattr(entry, "deselect"):
                                entry.deselect()
                    except Exception as e:
                        logger.warning(
                            f"Erro ao restaurar valor {valor_antigo} para {k}: {e}"
                        )
                elif isinstance(entry, ctk.StringVar) or hasattr(entry, "set"):
                    try:
                        entry.set(valor_antigo)
                    except Exception as e:
                        logger.warning(
                            f"Erro ao restaurar valor {valor_antigo} para {k}: {e}"
                        )
        # Se não houver valor antigo, deixa vazio para mostrar o placeholder

    def open_template_editor(self):
        def get_fields():
            return {"fixed": self.fixed_fields, "dynamic": sorted(self.dynamic_fields)}

        TemplateEditor(
            self,
            self.template_manager,
            get_fields,
            current_template=self.current_template,
        )

    def open_quick_mode(self):
        from quick_template_popup import QuickTemplatePopup

        QuickTemplatePopup(self, self.template_manager)

    def handle_daily_password(self):
        if senha := self.password_manager.get_today_password():
            try:
                pyperclip.copy(senha)
                self.show_snackbar("Senha diária copiada!")
            except Exception:
                self.show_snackbar(
                    "Falha ao copiar senha para a área de transferência!",
                    toast_type="error",
                )
        else:
            dialog = CTkInputDialog(
                title="Senha Diária", text="Informe a senha de hoje:"
            )
            if senha_input := dialog.get_input():
                self.password_manager.set_today_password(senha_input)
                pyperclip.copy(senha_input)
                self.show_snackbar("Senha diária salva e copiada!")

    def on_template_change(self, selected_display_name):
        real_name = self.template_manager.meta.get_real_name(selected_display_name)

        # Sempre recarrega lista atualizada
        self.template_manager.load_templates()
        self.template_selector.configure(
            values=self.template_manager.get_display_names()
        )

        self.current_template = real_name
        self.current_template_display.set(
            self.template_manager.meta.get_display_name(real_name)
        )
        self.load_template_placeholders()
        self._update_field_borders()

    def toggle_current_template_favorite(self):
        """Toggle favorite flag for the currently selected template and refresh selector."""
        try:
            display = self.current_template_display.get()
            real = self.template_manager.meta.get_real_name(display)
            if not real:
                return
            self.template_manager.meta.toggle_favorite(real)
            # refresh selector values and keep current selection
            vals = self.template_manager.get_display_names()
            try:
                self.template_selector.configure(values=vals)
            except Exception:
                pass
            self.current_template_display.set(
                self.template_manager.meta.get_display_name(real)
            )
        except Exception:
            pass

    def toggle_current_template_protected(self):
        """Toggle protected flag for the currently selected template and refresh selector."""
        try:
            display = self.current_template_display.get()
            real = self.template_manager.meta.get_real_name(display)
            if not real:
                return
            # If favorite, the meta will not allow toggling protected (handled in TemplateMeta)
            self.template_manager.meta.toggle_protected(real)
            vals = self.template_manager.get_display_names()
            try:
                self.template_selector.configure(values=vals)
            except Exception:
                pass
            self.current_template_display.set(
                self.template_manager.meta.get_display_name(real)
            )
        except Exception:
            pass

    def adjust_window_height(self):
        self.update_idletasks()

        # Altura real do conteúdo do formulário
        form_height = self.form_frame.winfo_reqheight()  # ← usa o tamanho *requisitado*
        # Calcula altura do label de crédito
        author_label_height = 0
        for widget in self.main_frame.grid_slaves(row=100, column=0):
            author_label_height = widget.winfo_reqheight()
            break
        extra_height = 250 + author_label_height

        screen_height = self.winfo_screenheight()
        max_height = int(screen_height * 0.9)

        desired_height = form_height + extra_height
        new_height = min(desired_height, max_height)

        # Largura atual (fallback se necessário)
        width = self.winfo_width()
        if width <= 10:
            width = 500  # valor padrão inicial

        # Mantém a posição atual
        x = self.winfo_x()
        y = self.winfo_y()

        # Garante altura mínima para evitar efeitos indesejados
        min_height = 415
        final_height = max(new_height, min_height)

        self.animate_resize_to(final_height, on_complete=self.save_window_config)

    def animate_resize_to(self, target_height, step=25, delay=10, on_complete=None):
        self.update_idletasks()

        current_width = self._get_current_width()
        current_height = self.winfo_height()
        x, y = self.winfo_x(), self.winfo_y()

        geometry_str = self._get_geometry_str(current_width, target_height, x, y)
        abs_diff = abs(target_height - current_height)
        direction = self._get_direction(target_height, current_height)
        new_height = self._get_new_height(current_height, step, direction)
        new_geometry_str = self._get_geometry_str(current_width, new_height, x, y)

        if self._should_set_final_height(current_height):
            self._set_final_geometry(geometry_str, on_complete)
            return

        if self._should_snap_to_target(abs_diff, step):
            self._set_final_geometry(geometry_str, on_complete)
            return

        self.geometry(new_geometry_str)
        self._safe_after(
            delay,
            lambda: self.animate_resize_to(target_height, step, delay, on_complete),
        )

    def _get_current_width(self):
        current_width = self.winfo_width()
        if current_width < 350:
            current_width = 350  # largura mínima
        return current_width

    def _get_geometry_str(self, width, height, x, y):
        return f"{width}x{height}+{x}+{y}"

    def _should_set_final_height(self, current_height):
        return current_height <= 1

    def _should_snap_to_target(self, abs_diff, step):
        return abs_diff <= step

    def _get_direction(self, target_height, current_height):
        return 1 if target_height > current_height else -1

    def _get_new_height(self, current_height, step, direction):
        return current_height + (step * direction)

    def _set_final_geometry(self, geometry_str, on_complete):
        self.geometry(geometry_str)
        if on_complete:
            self._safe_after(10, on_complete)

    def pulse_window(self, times=5, offset=3, delay=5):
        x, y = self.winfo_x(), self.winfo_y()

        def animate(count):
            if count == 0:
                self.geometry(f"+{x}+{y}")
                return
            dx = offset if count % 2 == 0 else -offset
            self.geometry(f"+{x + dx}+{y}")
            self._safe_after(delay, lambda: animate(count - 1))

        animate(times)


    def _refresh_all_template_selectors(self, select_template=None):
        # Atualiza todos os OptionMenus relevantes (main, editor, quick popup)
        # Main selector
        if hasattr(self, "template_selector"):
            self.template_selector.configure(
                values=self.template_manager.get_display_names()
            )
            # Seleciona o template alterado, se fornecido
            if select_template:
                display_name = self.template_manager.meta.get_display_name(
                    select_template
                )
                self.current_template = select_template
                self.current_template_display.set(display_name)
                self.template_selector.set(display_name)
                self.load_template_placeholders()
        # Template Editor
        for w in self.winfo_children():
            if w.__class__.__name__ == "TemplateEditor":
                try:
                    w.refresh_templates()
                    # Seleciona o template alterado, se fornecido
                    if select_template:
                        display_name = self.template_manager.meta.get_display_name(
                            select_template
                        )
                        w.template_var.set(display_name)
                        w.load_template(select_template)
                except Exception:
                    pass
            elif hasattr(w, "dropdown"):
                try:
                    w.dropdown.configure(
                        values=self.template_manager.get_display_names()
                    )
                except Exception:
                    pass
        # QuickTemplatePopup
        for w in self.winfo_children():
            if w.__class__.__name__ == "QuickTemplatePopup":
                try:
                    w.template_dropdown.configure(
                        values=self.template_manager.get_template_names()
                    )
                except Exception:
                    pass

    def importar_template(self, template):
        """
        Importa o template selecionado do NocoDB para o app.
        O usuário não pode escolher o nome do template, apenas a pasta (categoria).
        Se a ID já existir, pergunta se deseja atualizar o nome e, se sim, se deseja mover de pasta.
        A interface de seleção de pasta só mostra o campo de nova pasta ao clicar no botão '+'.
        """
        import customtkinter as ctk
        import os

        def prompt_pasta(categorias, pasta_atual=None):
            # Garante que pasta_atual seja só o nome da pasta, nunca o nome completo do template
            if pasta_atual and " / " in pasta_atual:
                pasta_atual = pasta_atual.split(" / ", 1)[0]
            pasta_escolhida = [None]

            def abrir_nova_pasta():
                win_nova = self._create_toplevel()
                win_nova.title("Nova Pasta")
                win_nova.geometry("320x140")
                win_nova.grab_set()
                ctk.CTkLabel(
                    win_nova, text="Nome da nova pasta:", font=ctk.CTkFont(size=13)
                ).pack(pady=(18, 8))
                entry = ctk.CTkEntry(win_nova)
                entry.pack(pady=(0, 8))
                entry.focus()
                info_label = ctk.CTkLabel(
                    win_nova, text="", text_color="#A94444", font=ctk.CTkFont(size=12)
                )
                info_label.pack(pady=(0, 2))

                def confirmar():
                    nome_pasta = entry.get().strip()
                    if not nome_pasta:
                        entry.configure(border_color="red")
                        info_label.configure(text="Digite o nome da nova pasta.")
                        return
                    # Verifica se já existe (case-insensitive)
                    for cat in categorias:
                        if cat.lower() == nome_pasta.lower():
                            info_label.configure(
                                text="Esta pasta já existe! Retornando para seleção."
                            )
                            win_nova.after(1200, win_nova.destroy)
                            pasta_escolhida[0] = cat
                            return
                    pasta_escolhida[0] = nome_pasta
                    win_nova.destroy()

                def cancelar():
                    win_nova.destroy()

                btn_frame = ctk.CTkFrame(win_nova)
                btn_frame.pack()
                ctk.CTkButton(btn_frame, text="Confirmar", command=confirmar).pack(
                    side="left", padx=10
                )
                ctk.CTkButton(btn_frame, text="Cancelar", command=cancelar).pack(
                    side="left", padx=10
                )
                win_nova.wait_window()

            def escolher():
                while True:
                    win = self._create_toplevel()
                    win.title("Escolher Pasta")
                    win.geometry("350x200")
                    win.grab_set()
                    win.grid_columnconfigure(0, weight=1)
                    win.grid_columnconfigure(1, weight=0)
                    ctk.CTkLabel(
                        win,
                        text="Escolha a pasta para salvar o template:",
                        font=ctk.CTkFont(size=13),
                    ).grid(
                        row=0, column=0, columnspan=2, pady=(18, 8), padx=10, sticky="w"
                    )
                    var = ctk.StringVar(value=pasta_atual or categorias[0])
                    opt = ctk.CTkOptionMenu(
                        win, values=categorias, variable=var, width=220
                    )
                    opt.grid(row=1, column=0, padx=(20, 0), pady=(0, 12), sticky="ew")

                    def nova_pasta():
                        win.destroy()
                        abrir_nova_pasta()

                    btn_add = ctk.CTkButton(win, text="+", width=30, command=nova_pasta)
                    btn_add.grid(
                        row=1, column=1, padx=(8, 20), pady=(0, 12), sticky="e"
                    )
                    btn_frame = ctk.CTkFrame(win)
                    btn_frame.grid(row=2, column=0, columnspan=2, pady=(0, 0))

                    def confirmar():
                        pasta_escolhida[0] = var.get()
                        win.destroy()

                    ctk.CTkButton(btn_frame, text="Confirmar", command=confirmar).pack(
                        side="left", padx=10
                    )
                    win.wait_window()
                    if pasta_escolhida[0] in categorias:
                        return pasta_escolhida[0]
                    if pasta_escolhida[0] is not None:
                        return pasta_escolhida[0]
                    return None

            return escolher()

        # Extrai os campos conforme a tabela NocoDB
        nome = template.get("Template Name")
        conteudo = template.get("Template Description")
        nocodb_id = template.get("Id") or template.get("id") or template.get("ID")
        nocodb_updated = (
            template.get("UpdatedAt")
            or template.get("updatedAt")
            or template.get("updated_at")
        )
        if not nome or not conteudo:
            self.show_snackbar("Template inválido!", toast_type="error")
            return

        base_dir = os.path.abspath("templates")
        categorias = ["Geral"]
        for root, dirs, files in os.walk(base_dir):
            rel = os.path.relpath(root, base_dir)
            if rel != ".":
                categorias.append(rel.replace("\\", "/"))
        categorias = sorted(set(categorias))

        # Procura todos os templates locais com esse nocodb_id
        duplicate_names = []
        for local_name, meta in self.template_manager.meta.meta.items():
            # Padroniza: se for "Geral / Nome", converte para "Nome"
            if local_name.startswith("Geral / "):
                local_name_check = local_name.split(" / ", 1)[1]
            else:
                local_name_check = local_name
            if meta.get("nocodb_id") == str(nocodb_id):
                duplicate_names.append(local_name_check)
        existing_name = duplicate_names[0] if duplicate_names else None

        # --- NOVO: Procura todos os templates locais com o MESMO CONTEÚDO ---
        same_content_names = []
        for local_name in self.template_manager.templates:
            local_content = self.template_manager.get_template(local_name)
            if local_content == conteudo:
                same_content_names.append(local_name)

        # Se houver mais de um template com o mesmo conteúdo, e pelo menos um deles tem nocodb_id, pergunta se deseja unificar
        if len(same_content_names) > 1:
            # Verifica se algum deles tem nocodb_id
            nocodb_templates = [
                n
                for n in same_content_names
                if self.template_manager.meta.meta.get(n, {}).get("nocodb_id")
            ]
            if nocodb_templates:
                import customtkinter as ctk

                unify_win = self._create_toplevel()
                unify_win.title("Unificar Templates Iguais")
                unify_win.geometry("600x260")
                unify_win.grab_set()
                ctk.CTkLabel(
                    unify_win,
                    text="Foram encontrados dois ou mais templates com o mesmo conteúdo.",
                    font=ctk.CTkFont(size=14, weight="bold"),
                ).pack(pady=(18, 8))
                ctk.CTkLabel(
                    unify_win,
                    text="Deseja unificar todos em apenas um, mantendo a versão do NocoDB?",
                    font=ctk.CTkFont(size=13),
                ).pack(pady=(0, 10))
                ctk.CTkLabel(
                    unify_win,
                    text="Templates encontrados:",
                    font=ctk.CTkFont(size=12, slant="italic"),
                ).pack(pady=(0, 2))
                for n in same_content_names:
                    id_str = self.template_manager.meta.meta.get(n, {}).get(
                        "nocodb_id", ""
                    )
                    id_str = f" (ID NocoDB: {id_str})" if id_str else ""
                    ctk.CTkLabel(
                        unify_win, text=f"- {n}{id_str}", font=ctk.CTkFont(size=12)
                    ).pack(anchor="w", padx=30)
                btn_frame = ctk.CTkFrame(unify_win)
                btn_frame.pack(pady=18)
                result = {"resp": None}

                def confirmar():
                    result["resp"] = True
                    unify_win.destroy()

                def cancelar():
                    result["resp"] = False
                    unify_win.destroy()

                ctk.CTkButton(
                    btn_frame,
                    text="Unificar (manter NocoDB)",
                    fg_color="#388E3C",
                    command=confirmar,
                    width=160,
                ).pack(side="left", padx=10)
                ctk.CTkButton(
                    btn_frame,
                    text="Cancelar",
                    fg_color="#A94444",
                    command=cancelar,
                    width=120,
                ).pack(side="left", padx=10)
                unify_win.wait_window()
                if result["resp"]:
                    # Mantém apenas o template do NocoDB (ou o primeiro com nocodb_id)
                    keep_name = None
                    for n in same_content_names:
                        if self.template_manager.meta.meta.get(n, {}).get(
                            "nocodb_id"
                        ) == str(nocodb_id):
                            keep_name = n
                            break
                    if not keep_name:
                        keep_name = nocodb_templates[0]
                    # Remove todos os outros
                    for n in same_content_names:
                        if n != keep_name:
                            self.template_manager.delete_template(n)
                    # Atualiza nome/pasta se necessário
                    pasta = prompt_pasta(categorias)
                    if pasta is None:
                        self.show_snackbar("Importação cancelada.", toast_type="info")
                        return
                    full_name = f"{pasta} / {nome}" if pasta != "Geral" else nome
                    if keep_name != full_name:
                        self.template_manager.save_template(
                            keep_name, full_name, conteudo
                        )
                        # Atualiza meta para garantir nocodb_id
                        self.template_manager.meta._ensure_entry(full_name)
                        self.template_manager.meta.meta[full_name]["nocodb_id"] = str(
                            nocodb_id
                        )
                        self.template_manager.meta._save()
                        self.template_manager.meta.remove_meta(keep_name)
                        self.show_snackbar(
                            f"Template movido para '{full_name}'!",
                            toast_type="success",
                            duration=2500,
                        )
                    else:
                        self.show_snackbar(
                            f"Templates unificados como '{full_name}'!",
                            toast_type="success",
                            duration=2500,
                        )
                    self.template_manager.load_templates()
                    self.template_selector.configure(
                        values=self.template_manager.get_display_names()
                    )
                    return
                # Se cancelar, não faz nada: NÃO remove nenhum template, segue para a lógica de comparação de ID/conteúdo normalmente

        # Se houver duplicados, verifica se o conteúdo é igual
        local_contents = []
        for name in duplicate_names:
            # Para "Geral", o nome do arquivo é só o nome, nunca "Geral / Nome"
            local_path = self.template_manager._template_path(name)
            if os.path.exists(local_path):
                # Sempre lê o conteúdo diretamente do arquivo para garantir que está atualizado
                with open(local_path, "r", encoding="utf-8") as f:
                    content = f.read()
                local_contents.append((name, content))
            else:
                local_contents.append((name, ""))

        # Se todos os conteúdos são iguais ao do NocoDB, unifica para o nome do NocoDB
        all_equal = all(content == conteudo for _, content in local_contents)
        if duplicate_names and all_equal:
            # Pergunta a pasta
            pasta = prompt_pasta(categorias)
            if pasta is None:
                self.show_snackbar("Importação cancelada.", toast_type="info")
                return
            full_name = f"{pasta} / {nome}" if pasta != "Geral" else nome

            # Se já existe apenas UM template local, com mesmo nome, conteúdo e pasta, não faz nada
            if (
                len(duplicate_names) == 1
                and duplicate_names[0] == full_name
                and self.template_manager.get_template(full_name) == conteudo
            ):
                self.show_snackbar(
                    "O template já existe e está atualizado. Nenhuma alteração foi necessária.",
                    toast_type="info",
                    duration=2500,
                )
                self.template_manager.load_templates()
                self._refresh_all_template_selectors()
                return

            # --- NOVO: verifica se já existe template com mesmo conteúdo em outra pasta ---
            same_content_names = []
            for local_name in self.template_manager.templates:
                local_content = self.template_manager.get_template(local_name)
                if local_content == conteudo and local_name != full_name:
                    same_content_names.append(local_name)
            # Se existir, unifica: remove todos os outros, mantém só o novo
            if same_content_names:
                for n in same_content_names:
                    self.template_manager.delete_template(n)
                for name, _ in local_contents:
                    if name != full_name:
                        self.template_manager.delete_template(name)
                self.template_manager.add_template(full_name, conteudo)
                self.template_manager.meta._ensure_entry(full_name)
                self.template_manager.meta.meta[full_name]["nocodb_id"] = str(nocodb_id)
                self.template_manager.meta._save()
                # Remove duplicados do meta.json
                for name in list(self.template_manager.meta.meta.keys()):
                    if name != full_name and self.template_manager.meta.meta[name].get(
                        "nocodb_id"
                    ) == str(nocodb_id):
                        self.template_manager.meta.remove_meta(name)
                pasta_str = f"{pasta} / {nome}"
                self.show_snackbar(
                    f"Templates unificados como '{pasta_str}'!",
                    toast_type="success",
                    duration=2500,
                )
                self.template_manager.load_templates()
                self._refresh_all_template_selectors()
                return
            # Caso contrário, remove todos, mantém só o nome do NocoDB (na pasta escolhida)
            for name, _ in local_contents:
                if name != full_name:
                    self.template_manager.delete_template(name)
            self.template_manager.add_template(full_name, conteudo)
            self.template_manager.meta._ensure_entry(full_name)
            self.template_manager.meta.meta[full_name]["nocodb_id"] = str(nocodb_id)
            self.template_manager.meta._save()
            # Remove duplicados do meta.json
            for name in list(self.template_manager.meta.meta.keys()):
                if name != full_name and self.template_manager.meta.meta[name].get(
                    "nocodb_id"
                ) == str(nocodb_id):
                    self.template_manager.meta.remove_meta(name)
            pasta_str = f"{pasta} / {nome}"
            if any(
                self.template_manager._split_name(name)[0] != pasta
                for name in duplicate_names
            ):
                self.show_snackbar(
                    f"Template movido para '{pasta_str}'!",
                    toast_type="success",
                    duration=2500,
                )
            else:
                self.show_snackbar(
                    f"Templates unificados como '{pasta_str}'!",
                    toast_type="success",
                    duration=2500,
                )
            self.template_manager.load_templates()
            self._refresh_all_template_selectors()
            return

        elif duplicate_names and not all_equal:
            # Se há conteúdos diferentes, mostrar tela de comparação para o usuário escolher qual manter
            # Mostra janela de comparação múltipla
            import customtkinter as ctk
            import datetime
            import os

            compare_win = self._create_toplevel()
            compare_win.title("Comparar Templates Duplicados")
            compare_win.update_idletasks()
            # Calcula tamanho do monitor
            screen_width = compare_win.winfo_screenwidth()
            screen_height = compare_win.winfo_screenheight()
            max_width = int(screen_width * 0.98)
            max_height = int(screen_height * 0.92)
            # Largura mínima por item
            min_item_width = 400
            n_items = 1 + len(local_contents)
            # Calcula quantos cabem na tela
            max_items_per_screen = max(1, (max_width - 40) // min_item_width)
            # Se couber tudo, usa o tamanho ideal, senão, limita ao máximo da tela
            if n_items <= max_items_per_screen:
                win_width = min_item_width * n_items + 40
                use_scroll = False
            else:
                win_width = max_width
                use_scroll = True
            win_height = min(600, max_height)
            compare_win.geometry(f"{win_width}x{win_height}")
            compare_win.grab_set()

            # Frame com scroll horizontal se necessário
            if use_scroll:
                scroll_frame = ctk.CTkScrollableFrame(
                    compare_win,
                    orientation="horizontal",
                    width=win_width - 10,
                    height=win_height - 80,
                )
                scroll_frame.grid(
                    row=0, column=0, sticky="nsew", padx=0, pady=0, columnspan=2
                )
                parent_frame = scroll_frame
            else:
                parent_frame = compare_win

            # Cabeçalhos
            ctk.CTkLabel(
                parent_frame,
                text="Template do NocoDB",
                font=ctk.CTkFont(size=14, weight="bold"),
            ).grid(row=0, column=0, padx=10, pady=10)
            for idx, (name, _) in enumerate(local_contents):
                ctk.CTkLabel(
                    parent_frame,
                    text=f"Template Local: {name}",
                    font=ctk.CTkFont(size=14, weight="bold"),
                ).grid(row=0, column=idx + 1, padx=10, pady=10)

            # NocoDB content
            nocodb_box = ctk.CTkTextbox(
                parent_frame, wrap="word", width=min_item_width, height=350
            )
            nocodb_box.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
            nocodb_box.insert("1.0", conteudo)
            nocodb_box.configure(state="disabled")

            # Local contents
            local_boxes = []
            for idx, (name, content) in enumerate(local_contents):
                local_box = ctk.CTkTextbox(
                    parent_frame, wrap="word", width=min_item_width, height=350
                )
                local_box.grid(row=1, column=idx + 1, padx=10, pady=10, sticky="nsew")
                local_box.insert("1.0", content if content is not None else "")
                local_box.configure(state="disabled")
                local_boxes.append((name, local_box))

            # Datas de criação e modificação
            # NocoDB
            nocodb_created = (
                template.get("CreatedAt", "")
                or template.get("createdAt", "")
                or template.get("created_at", "")
            )
            nocodb_updated = (
                template.get("UpdatedAt", "")
                or template.get("updatedAt", "")
                or template.get("updated_at", "")
            )

            def to_naive(dt):
                if dt is not None and dt.tzinfo is not None:
                    return dt.replace(tzinfo=None)
                return dt

            try:
                nocodb_created_dt = (
                    datetime.datetime.fromisoformat(
                        nocodb_created.replace("Z", "+00:00")
                    )
                    if nocodb_created
                    else None
                )
                nocodb_created_dt = to_naive(nocodb_created_dt)
            except Exception:
                nocodb_created_dt = None
            try:
                nocodb_updated_dt = (
                    datetime.datetime.fromisoformat(
                        nocodb_updated.replace("Z", "+00:00")
                    )
                    if nocodb_updated
                    else None
                )
                nocodb_updated_dt = to_naive(nocodb_updated_dt)
            except Exception:
                nocodb_updated_dt = None

            # Locais
            local_created_list = []
            local_modified_list = []
            for idx, (name, _) in enumerate(local_contents):
                local_path = self.template_manager._template_path(name)
                try:
                    local_created_dt = (
                        datetime.datetime.fromtimestamp(os.path.getctime(local_path))
                        if os.path.exists(local_path)
                        else None
                    )
                    local_created_dt = to_naive(local_created_dt)
                except Exception:
                    local_created_dt = None
                try:
                    local_modified_dt = (
                        datetime.datetime.fromtimestamp(os.path.getmtime(local_path))
                        if os.path.exists(local_path)
                        else None
                    )
                    local_modified_dt = to_naive(local_modified_dt)
                except Exception:
                    local_modified_dt = None
                local_created_list.append(local_created_dt)
                local_modified_list.append(local_modified_dt)

            # Coleta todos para destacar o mais recente
            all_created = [dt for dt in [nocodb_created_dt] + local_created_list if dt]
            all_modified = [
                dt for dt in [nocodb_updated_dt] + local_modified_list if dt
            ]
            max_created = max(all_created) if all_created else None
            max_modified = max(all_modified) if all_modified else None

            # Linha de datas: criação (esquerda), modificação (direita), cor verde se for o mais recente, vermelho caso contrário
            # NocoDB
            nocodb_created_fmt = (
                nocodb_created_dt.strftime("%d/%m/%Y %H:%M")
                if nocodb_created_dt
                else "-"
            )
            nocodb_updated_fmt = (
                nocodb_updated_dt.strftime("%d/%m/%Y %H:%M")
                if nocodb_updated_dt
                else "-"
            )
            created_color = (
                "#2ecc40"
                if nocodb_created_dt and nocodb_created_dt == max_created
                else "#e74c3c"
            )
            updated_color = (
                "#2ecc40"
                if nocodb_updated_dt and nocodb_updated_dt == max_modified
                else "#e74c3c"
            )
            ctk.CTkLabel(
                parent_frame,
                text=f"Criação: {nocodb_created_fmt}",
                font=ctk.CTkFont(size=11, slant="italic"),
                text_color=created_color,
                anchor="w",
                justify="left",
            ).grid(row=2, column=0, padx=(10, 2), sticky="w")
            ctk.CTkLabel(
                parent_frame,
                text=f"Atualizado em: {nocodb_updated_fmt}",
                font=ctk.CTkFont(size=11, slant="italic"),
                text_color=updated_color,
                anchor="e",
                justify="right",
            ).grid(row=2, column=0, padx=(2, 10), sticky="e")

            # Locais
            for idx, (name, _) in enumerate(local_contents):
                local_created_dt = local_created_list[idx]
                local_modified_dt = local_modified_list[idx]
                local_created_fmt = (
                    local_created_dt.strftime("%d/%m/%Y %H:%M")
                    if local_created_dt
                    else "-"
                )
                local_modified_fmt = (
                    local_modified_dt.strftime("%d/%m/%Y %H:%M")
                    if local_modified_dt
                    else "-"
                )
                created_color = (
                    "#2ecc40"
                    if local_created_dt and local_created_dt == max_created
                    else "#e74c3c"
                )
                updated_color = (
                    "#2ecc40"
                    if local_modified_dt and local_modified_dt == max_modified
                    else "#e74c3c"
                )
                ctk.CTkLabel(
                    parent_frame,
                    text=f"Criação: {local_created_fmt}",
                    font=ctk.CTkFont(size=11, slant="italic"),
                    text_color=created_color,
                    anchor="w",
                    justify="left",
                ).grid(row=2, column=idx + 1, padx=(10, 2), sticky="w")
                ctk.CTkLabel(
                    parent_frame,
                    text=f"Atualizado em: {local_modified_fmt}",
                    font=ctk.CTkFont(size=11, slant="italic"),
                    text_color=updated_color,
                    anchor="e",
                    justify="right",
                ).grid(row=2, column=idx + 1, padx=(2, 10), sticky="e")

            ctk.CTkLabel(
                compare_win,
                text="Escolha qual template deseja manter:",
                font=ctk.CTkFont(size=13),
            ).grid(row=4, column=0, columnspan=len(local_contents) + 1, pady=(0, 10))

            btn_frame = ctk.CTkFrame(compare_win)
            btn_frame.grid(row=5, column=0, columnspan=len(local_contents) + 1, pady=10)

            def manter_nocodb():
                # Garante que a pasta padrão seja só a pasta, não o nome completo do template
                if local_contents:
                    old_category, _ = self.template_manager._split_name(
                        local_contents[0][0]
                    )
                else:
                    old_category = "Geral"
                # Pergunta a pasta
                pasta = prompt_pasta(categorias, old_category)
                if pasta is None:
                    self.show_snackbar("Importação cancelada.", toast_type="info")
                    compare_win.destroy()
                    return
                full_name = f"{pasta} / {nome}" if pasta != "Geral" else nome

                # Salva todos os templates comparados em um dicionário
                templates_compared = {name: content for name, content in local_contents}

                # Remove o template escolhido do dicionário (vai ser recriado/atualizado)
                if full_name in templates_compared:
                    del templates_compared[full_name]

                # Marca todos os outros templates para remoção (nocodb_id = "-1")
                for name in templates_compared:
                    self.template_manager.meta._ensure_entry(name)
                    self.template_manager.meta.meta[name]["nocodb_id"] = "-1"
                    self.template_manager.meta._save()

                # Cria ou sobrescreve o template escolhido com o nome e conteúdo do NocoDB
                self.template_manager.add_template(full_name, conteudo)
                self.template_manager.meta._ensure_entry(full_name)
                self.template_manager.meta.meta[full_name]["nocodb_id"] = str(nocodb_id)
                self.template_manager.meta._save()

                # Remove duplicados do meta.json (com a mesma nocodb_id) exceto o escolhido
                for name in list(self.template_manager.meta.meta.keys()):
                    if name != full_name and self.template_manager.meta.meta[name].get(
                        "nocodb_id"
                    ) == str(nocodb_id):
                        self.template_manager.meta.remove_meta(name)

                pasta_str = f"{pasta} / {nome}"
                self.template_manager.load_templates()
                self._refresh_all_template_selectors(select_template=full_name)
                # Remove todos os templates marcados para exclusão
                self.remover_templates_nocodb_id_menos_um()

                # Atualiza o estado da interface principal
                self.current_template = full_name
                display_name = self.template_manager.meta.get_display_name(full_name)
                self.current_template_display.set(display_name)

                # Atualiza os seletores em toda a aplicação
                self._refresh_all_template_selectors(select_template=full_name)

                # Força o carregamento do template
                self.load_template_placeholders()

                # Notifica o usuário
                if old_category != pasta:
                    self.show_snackbar(
                        f"Template movido para '{pasta_str}' e carregado!",
                        toast_type="success",
                        duration=2500,
                    )
                else:
                    self.show_snackbar(
                        "Template atualizado e carregado!",
                        toast_type="success",
                        duration=2500,
                    )
                compare_win.destroy()

            def manter_local(idx):
                # Salva todos os templates comparados em um dicionário
                templates_compared = {name: content for name, content in local_contents}
                name, _ = local_contents[idx]
                current_category, current_nome = self.template_manager._split_name(name)
                # Pergunta a pasta para manter o local
                pasta = prompt_pasta(categorias, current_category)
                if pasta is None:
                    self.show_snackbar("Importação cancelada.", toast_type="info")
                    compare_win.destroy()
                    return
                keep_name = (
                    f"{pasta} / {current_nome}" if pasta != "Geral" else current_nome
                )

                # Se o nome mudou, move o template para a nova pasta
                if keep_name != name:
                    self.template_manager.save_template(
                        name, keep_name, self.template_manager.get_template(name)
                    )
                    self.template_manager.delete_template(name)

                # Atualiza meta para garantir unicidade e nocodb_id
                self.template_manager.meta._ensure_entry(keep_name)
                self.template_manager.meta.meta[keep_name]["nocodb_id"] = str(nocodb_id)
                self.template_manager.meta._save()

                # Remove o template escolhido do dicionário (vai ser mantido)
                if keep_name in templates_compared:
                    del templates_compared[keep_name]
                if name in templates_compared:
                    del templates_compared[name]

                # Marca todos os outros templates para remoção (nocodb_id = "-1")
                for n in templates_compared:
                    self.template_manager.meta._ensure_entry(n)
                    self.template_manager.meta.meta[n]["nocodb_id"] = "-1"
                    self.template_manager.meta._save()

                # Remove duplicados do meta.json (com a mesma nocodb_id) exceto o escolhido
                for n in list(self.template_manager.meta.meta.keys()):
                    if n != keep_name and self.template_manager.meta.meta[n].get(
                        "nocodb_id"
                    ) == str(nocodb_id):
                        self.template_manager.meta.remove_meta(n)

                pasta_str = f"{pasta} / {current_nome}"
                self.template_manager.load_templates()
                self._refresh_all_template_selectors(select_template=keep_name)
                self.remover_templates_nocodb_id_menos_um()
                self.show_snackbar(
                    f"Template local '{pasta_str}' mantido!",
                    toast_type="success",
                    duration=2500,
                )
                compare_win.destroy()

            ctk.CTkButton(
                btn_frame,
                text="Manter do NocoDB",
                fg_color="#388E3C",
                command=manter_nocodb,
            ).pack(side="left", padx=10)
            for idx, (name, _) in enumerate(local_contents):
                ctk.CTkButton(
                    btn_frame,
                    text=f"Manter Local: {name}",
                    fg_color="#A94444",
                    command=lambda i=idx: manter_local(i),
                ).pack(side="left", padx=10)
            compare_win.wait_window()
            return

        def prompt_pasta(categorias, pasta_atual=None):
            pasta_escolhida = [None]

            def abrir_nova_pasta():
                win_nova = self._create_toplevel()
                win_nova.title("Nova Pasta")
                win_nova.geometry("320x140")
                win_nova.grab_set()
                ctk.CTkLabel(
                    win_nova, text="Nome da nova pasta:", font=ctk.CTkFont(size=13)
                ).pack(pady=(18, 8))
                entry = ctk.CTkEntry(win_nova)
                entry.pack(pady=(0, 8))
                entry.focus()
                info_label = ctk.CTkLabel(
                    win_nova, text="", text_color="#A94444", font=ctk.CTkFont(size=12)
                )
                info_label.pack(pady=(0, 2))

                def confirmar():
                    nome_pasta = entry.get().strip()
                    if not nome_pasta:
                        entry.configure(border_color="red")
                        info_label.configure(text="Digite o nome da nova pasta.")
                        return
                    # Verifica se já existe (case-insensitive)
                    for cat in categorias:
                        if cat.lower() == nome_pasta.lower():
                            info_label.configure(
                                text="Esta pasta já existe! Retornando para seleção."
                            )
                            win_nova.after(1200, win_nova.destroy)
                            # Retorna para tela anterior já selecionando a pasta existente
                            pasta_escolhida[0] = cat
                            return
                    pasta_escolhida[0] = nome_pasta
                    win_nova.destroy()

                def cancelar():
                    win_nova.destroy()

                btn_frame = ctk.CTkFrame(win_nova)
                btn_frame.pack()
                ctk.CTkButton(btn_frame, text="Confirmar", command=confirmar).pack(
                    side="left", padx=10
                )
                ctk.CTkButton(btn_frame, text="Cancelar", command=cancelar).pack(
                    side="left", padx=10
                )
                win_nova.wait_window()

            def show_pasta_selector(parent, categorias, pasta_atual, on_nova_pasta):
                win = self._create_toplevel(parent)
                win.title("Escolher Pasta")
                win.geometry("350x200")
                win.grab_set()
                win.grid_columnconfigure(0, weight=1)
                win.grid_columnconfigure(1, weight=0)
                ctk.CTkLabel(
                    win,
                    text="Escolha a pasta para salvar o template:",
                    font=ctk.CTkFont(size=13),
                ).grid(row=0, column=0, columnspan=2, pady=(18, 8), padx=10, sticky="w")
                var = ctk.StringVar(value=pasta_atual or categorias[0])
                opt = ctk.CTkOptionMenu(win, values=categorias, variable=var, width=220)
                opt.grid(row=1, column=0, padx=(20, 0), pady=(0, 12), sticky="ew")

                def nova_pasta():
                    win.destroy()
                    on_nova_pasta()

                btn_add = ctk.CTkButton(win, text="+", width=30, command=nova_pasta)
                btn_add.grid(row=1, column=1, padx=(8, 20), pady=(0, 12), sticky="e")
                btn_frame = ctk.CTkFrame(win)
                btn_frame.grid(row=2, column=0, columnspan=2, pady=(0, 0))
                result = {"pasta": None}

                def confirmar():
                    result["pasta"] = var.get()
                    win.destroy()

                ctk.CTkButton(btn_frame, text="Confirmar", command=confirmar).pack(
                    side="left", padx=10
                )
                win.wait_window()
                return result["pasta"]

            def escolher():
                while True:

                    def abrir_nova_pasta():
                        win_nova = self._create_toplevel()
                        win_nova.title("Nova Pasta")
                        win_nova.geometry("320x140")
                        win_nova.grab_set()
                        ctk.CTkLabel(
                            win_nova,
                            text="Nome da nova pasta:",
                            font=ctk.CTkFont(size=13),
                        ).pack(pady=(18, 8))
                        entry = ctk.CTkEntry(win_nova)
                        entry.pack(pady=(0, 8))
                        entry.focus()
                        info_label = ctk.CTkLabel(
                            win_nova,
                            text="",
                            text_color="#A94444",
                            font=ctk.CTkFont(size=12),
                        )
                        info_label.pack(pady=(0, 2))

                        def confirmar():
                            nome_pasta = entry.get().strip()
                            if not nome_pasta:
                                entry.configure(border_color="red")
                                info_label.configure(
                                    text="Digite o nome da nova pasta."
                                )
                                return
                            # Verifica se já existe (case-insensitive)
                            for cat in categorias:
                                if cat.lower() == nome_pasta.lower():
                                    info_label.configure(
                                        text="Esta pasta já existe! Retornando para seleção."
                                    )
                                    win_nova.after(1200, win_nova.destroy)
                                    pasta_escolhida[0] = cat
                                    return
                            pasta_escolhida[0] = nome_pasta
                            win_nova.destroy()

                        def cancelar():
                            win_nova.destroy()

                        btn_frame = ctk.CTkFrame(win_nova)
                        btn_frame.pack()
                        ctk.CTkButton(
                            btn_frame, text="Confirmar", command=confirmar
                        ).pack(side="left", padx=10)
                        ctk.CTkButton(
                            btn_frame, text="Cancelar", command=cancelar
                        ).pack(side="left", padx=10)
                        win_nova.wait_window()

                    pasta_escolhida = [None]

                    def on_nova_pasta():
                        abrir_nova_pasta()

                    pasta = show_pasta_selector(
                        self, categorias, pasta_atual, on_nova_pasta
                    )
                    if pasta is not None:
                        return pasta
                    return None

            return escolher()

        if existing_name:
            # Verifica se o arquivo do template local existe e não está vazio
            local_path = self.template_manager._template_path(existing_name)
            local_exists = os.path.exists(local_path)
            local_content = (
                self.template_manager.get_template(existing_name)
                if local_exists
                else ""
            )
            old_category, old_nome = self.template_manager._split_name(existing_name)
            if (not local_exists) or (not local_content.strip()):
                # Se não existe ou está vazio, importa normalmente (sem comparação)
                full_name = (
                    f"{old_category} / {nome}" if old_category != "Geral" else nome
                )
                self.template_manager.add_template(full_name, conteudo)
                if nocodb_id:
                    self.template_manager.meta._ensure_entry(full_name)
                    self.template_manager.meta.meta[full_name]["nocodb_id"] = str(
                        nocodb_id
                    )
                    self.template_manager.meta._save()
                # Remove entradas duplicadas de meta.json (com o mesmo nocodb_id)
                for name in list(self.template_manager.meta.meta.keys()):
                    if name != full_name and self.template_manager.meta.meta[name].get(
                        "nocodb_id"
                    ) == str(nocodb_id):
                        self.template_manager.meta.remove_meta(name)
                if old_category != pasta:
                    self.show_snackbar(
                        f"Template movido para '{full_name}'!",
                        toast_type="success",
                        duration=2500,
                    )
                else:
                    self.show_snackbar(
                        f"Template '{full_name}' importado!",
                        toast_type="success",
                        duration=2500,
                    )
                self.template_manager.load_templates()
                self._refresh_all_template_selectors()
                return
            if local_content != conteudo:
                # Mostra janela de comparação lado a lado (NocoDB à esquerda, Local à direita)
                compare_win = self._create_toplevel()
                compare_win.title("Comparar Templates")
                compare_win.geometry("900x500")
                compare_win.grab_set()

                import datetime
                import os

                ctk.CTkLabel(
                    compare_win,
                    text="Template do NocoDB",
                    font=ctk.CTkFont(size=14, weight="bold"),
                ).grid(row=0, column=0, padx=10, pady=10)
                ctk.CTkLabel(
                    compare_win,
                    text="Template Local",
                    font=ctk.CTkFont(size=14, weight="bold"),
                ).grid(row=0, column=1, padx=10, pady=10)

                nocodb_box = ctk.CTkTextbox(
                    compare_win, wrap="word", width=400, height=350
                )
                nocodb_box.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
                nocodb_box.insert("1.0", conteudo)
                nocodb_box.configure(state="disabled")

                local_box = ctk.CTkTextbox(
                    compare_win, wrap="word", width=400, height=350
                )
                local_box.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
                local_box.insert("1.0", local_content)
                local_box.configure(state="disabled")

                # Datas de criação e modificação
                nocodb_created = (
                    template.get("CreatedAt", "")
                    or template.get("createdAt", "")
                    or template.get("created_at", "")
                )
                nocodb_updated = (
                    template.get("UpdatedAt", "")
                    or template.get("updatedAt", "")
                    or template.get("updated_at", "")
                )
                try:
                    nocodb_created_fmt = (
                        datetime.datetime.fromisoformat(
                            nocodb_created.replace("Z", "+00:00")
                        ).strftime("%d/%m/%Y %H:%M")
                        if nocodb_created
                        else "-"
                    )
                except Exception:
                    nocodb_created_fmt = "-"
                try:
                    nocodb_updated_fmt = (
                        datetime.datetime.fromisoformat(
                            nocodb_updated.replace("Z", "+00:00")
                        ).strftime("%d/%m/%Y %H:%M")
                        if nocodb_updated
                        else "-"
                    )
                except Exception:
                    nocodb_updated_fmt = "-"
                try:
                    local_created = (
                        datetime.datetime.fromtimestamp(
                            os.path.getctime(local_path)
                        ).strftime("%d/%m/%Y %H:%M")
                        if os.path.exists(local_path)
                        else "-"
                    )
                except Exception:
                    local_created = "-"
                try:
                    local_modified = (
                        datetime.datetime.fromtimestamp(
                            os.path.getmtime(local_path)
                        ).strftime("%d/%m/%Y %H:%M")
                        if os.path.exists(local_path)
                        else "-"
                    )
                except Exception:
                    local_modified = "-"

                # Row index to place informational labels below the textboxes
                row_info = 4

                ctk.CTkLabel(
                    compare_win,
                    text=f"Criação: {nocodb_created_fmt}",
                    font=ctk.CTkFont(size=11, slant="italic"),
                ).grid(row=2, column=0, padx=10, sticky="w")
                ctk.CTkLabel(
                    compare_win,
                    text=f"Modificação: {nocodb_updated_fmt}",
                    font=ctk.CTkFont(size=11, slant="italic"),
                ).grid(row=3, column=0, padx=10, sticky="w")
                ctk.CTkLabel(
                    compare_win,
                    text=f"Criação: {local_created}",
                    font=ctk.CTkFont(size=11, slant="italic"),
                ).grid(row=2, column=1, padx=10, sticky="w")
                ctk.CTkLabel(
                    compare_win,
                    text=f"Modificação: {local_modified}",
                    font=ctk.CTkFont(size=11, slant="italic"),
                ).grid(row=3, column=1, padx=10, sticky="w")
                row_info += 1

                # Tenta determinar datetimes para comparação (pode ser None)
                nocodb_dt = None
                local_dt = None
                try:
                    if nocodb_updated:
                        nocodb_dt = datetime.datetime.fromisoformat(
                            nocodb_updated.replace("Z", "+00:00")
                        )
                except Exception:
                    nocodb_dt = None
                try:
                    if os.path.exists(local_path):
                        local_dt = datetime.datetime.fromtimestamp(
                            os.path.getmtime(local_path)
                        )
                except Exception:
                    local_dt = None

                info_text = ""
                if nocodb_dt and local_dt:
                    if nocodb_dt > local_dt:
                        info_text = (
                            f"O template do NocoDB é mais recente ({nocodb_dt.strftime('%d/%m/%Y %H:%M')}) "
                            f"que o local ({local_dt.strftime('%d/%m/%Y %H:%M')})."
                        )
                    elif local_dt > nocodb_dt:
                        info_text = (
                            f"O template local é mais recente ({local_dt.strftime('%d/%m/%Y %H:%M')}) "
                            f"que o do NocoDB ({nocodb_dt.strftime('%d/%m/%Y %H:%M')})."
                        )
                    else:
                        info_text = (
                            "Ambos os templates têm a mesma data de modificação."
                        )
                else:
                    info_text = "Datas de atualização indisponíveis."

                ctk.CTkLabel(
                    compare_win,
                    text=info_text,
                    font=ctk.CTkFont(size=12, slant="italic"),
                ).grid(row=row_info, column=0, columnspan=2, pady=(0, 10))

                btn_frame = ctk.CTkFrame(compare_win)
                btn_frame.grid(row=3, column=0, columnspan=2, pady=10)

                def usar_nocodb():
                    # Pergunta se deseja atualizar o título do template usando customtkinter
                    if old_nome != nome:
                        # Janela customtkinter para atualizar título
                        update_win = self._create_toplevel()
                        update_win.title("Atualizar Título")
                        update_win.geometry("420x260")
                        update_win.grab_set()
                        ctk.CTkLabel(
                            update_win,
                            text="O nome do template local é:",
                            font=ctk.CTkFont(size=13),
                        ).pack(pady=(18, 2))
                        ctk.CTkLabel(
                            update_win,
                            text=f"'{old_nome}'",
                            font=ctk.CTkFont(size=15, weight="bold"),
                            text_color="#7E57C2",
                        ).pack(pady=(0, 8))
                        ctk.CTkLabel(
                            update_win,
                            text="O nome recebido do NocoDB é:",
                            font=ctk.CTkFont(size=13),
                        ).pack(pady=(0, 2))
                        ctk.CTkLabel(
                            update_win,
                            text=f"'{nome}'",
                            font=ctk.CTkFont(size=15, weight="bold"),
                            text_color="#388E3C",
                        ).pack(pady=(0, 10))
                        ctk.CTkLabel(
                            update_win,
                            text="Deseja atualizar o título do template para o nome do NocoDB?",
                            font=ctk.CTkFont(size=13),
                        ).pack(pady=(0, 10))

                        btn_frame = ctk.CTkFrame(update_win)
                        btn_frame.pack(pady=10)
                        result = {"resp": None}

                        def confirmar():
                            result["resp"] = True
                            update_win.destroy()

                        def cancelar():
                            result["resp"] = False
                            update_win.destroy()

                        ctk.CTkButton(
                            btn_frame,
                            text="Sim",
                            fg_color="#388E3C",
                            command=confirmar,
                            width=80,
                        ).pack(side="left", padx=10)
                        ctk.CTkButton(
                            btn_frame,
                            text="Não",
                            fg_color="#A94444",
                            command=cancelar,
                            width=80,
                        ).pack(side="left", padx=10)
                        update_win.wait_window()
                        resp = result["resp"]
                        if resp:
                            # Pergunta se deseja mover de pasta
                            mover = False
                            move_result = {"resp": None}

                            def mover_pasta():
                                move_result["resp"] = True
                                move_win.destroy()

                            def manter_pasta():
                                move_result["resp"] = False
                                move_win.destroy()

                            move_win = self._create_toplevel()
                            move_win.title("Mover de Pasta?")
                            move_win.geometry("420x170")
                            move_win.grab_set()
                            ctk.CTkLabel(
                                move_win,
                                text=f"O template está atualmente na pasta '{old_category}'.\nDeseja mover para outra pasta?",
                                font=ctk.CTkFont(size=13),
                            ).pack(pady=(18, 10))
                            btn_frame2 = ctk.CTkFrame(move_win)
                            btn_frame2.pack(pady=10)
                            ctk.CTkButton(
                                btn_frame2,
                                text="Sim",
                                fg_color="#388E3C",
                                command=mover_pasta,
                                width=80,
                            ).pack(side="left", padx=10)
                            ctk.CTkButton(
                                btn_frame2,
                                text="Não",
                                fg_color="#A94444",
                                command=manter_pasta,
                                width=80,
                            ).pack(side="left", padx=10)
                            move_win.wait_window()
                            mover = move_result["resp"]
                            if mover:
                                nova_pasta = prompt_pasta(
                                    categorias, pasta_atual=old_category
                                )
                                if not nova_pasta:
                                    self.show_snackbar(
                                        "Importação cancelada.", toast_type="info"
                                    )
                                    compare_win.destroy()
                                    return
                                full_new_name = (
                                    f"{nova_pasta} / {nome}"
                                    if nova_pasta != "Geral"
                                    else nome
                                )
                            else:
                                full_new_name = (
                                    f"{old_category} / {nome}"
                                    if old_category != "Geral"
                                    else nome
                                )
                            # Salva com novo nome (na pasta escolhida)
                            self.template_manager.save_template(
                                existing_name, full_new_name, conteudo
                            )
                            old_meta = self.template_manager.meta.meta.get(
                                existing_name, {}
                            ).copy()
                            self.template_manager.meta.meta[full_new_name] = old_meta
                            self.template_manager.meta._save()
                            if existing_name != full_new_name:
                                self.template_manager.meta.remove_meta(existing_name)
                            self.show_snackbar(
                                f"Título atualizado para '{full_new_name}' e template sincronizado!",
                                toast_type="success",
                            )
                        else:
                            # Só atualiza o conteúdo mantendo o nome antigo e pasta
                            self.template_manager.save_template(
                                existing_name, existing_name, conteudo
                            )
                            self.template_manager.meta._ensure_entry(existing_name)
                            self.template_manager.meta.meta[existing_name][
                                "nocodb_id"
                            ] = str(nocodb_id)
                            self.template_manager.meta._save()
                            self.show_snackbar(
                                f"Template '{existing_name}' atualizado pelo NocoDB!",
                                toast_type="success",
                            )
                    else:
                        # Só atualiza o conteúdo mantendo o nome e pasta
                        self.template_manager.save_template(
                            existing_name, existing_name, conteudo
                        )
                        self.template_manager.meta._ensure_entry(existing_name)
                        self.template_manager.meta.meta[existing_name]["nocodb_id"] = (
                            str(nocodb_id)
                        )
                        self.template_manager.meta._save()
                        self.show_snackbar(
                            f"Template '{existing_name}' atualizado pelo NocoDB!",
                            toast_type="success",
                        )
                    compare_win.destroy()
                    self.template_manager.load_templates()
                    self.template_selector.configure(
                        values=self.template_manager.get_display_names()
                    )

                def manter_local(idx=None):  # Keep parameter for consistency
                    self.show_snackbar("Template local mantido!", toast_type="info")
                    compare_win.destroy()

                ctk.CTkButton(
                    btn_frame,
                    text="Usar do NocoDB",
                    fg_color="#A94444",
                    command=usar_nocodb,
                ).pack(side="left", padx=20)
                ctk.CTkButton(
                    btn_frame,
                    text="Manter Local",
                    fg_color="#388E3C",
                    command=manter_local,
                ).pack(side="left", padx=20)
                compare_win.wait_window()
                return
            else:
                # Se o nome do NocoDB for diferente do local, perguntar se deseja atualizar o nome
                if old_nome != nome:
                    # Janela customtkinter para atualizar título
                    update_win = self._create_toplevel()
                    update_win.title("Atualizar Título")
                    update_win.geometry("420x260")
                    update_win.grab_set()
                    ctk.CTkLabel(
                        update_win,
                        text="O nome do template local é:",
                        font=ctk.CTkFont(size=13),
                    ).pack(pady=(18, 2))
                    ctk.CTkLabel(
                        update_win,
                        text=f"'{old_nome}'",
                        font=ctk.CTkFont(size=15, weight="bold"),
                        text_color="#7E57C2",
                    ).pack(pady=(0, 8))
                    ctk.CTkLabel(
                        update_win,
                        text="O nome recebido do NocoDB é:",
                        font=ctk.CTkFont(size=13),
                    ).pack(pady=(0, 2))
                    ctk.CTkLabel(
                        update_win,
                        text=f"'{nome}'",
                        font=ctk.CTkFont(size=15, weight="bold"),
                        text_color="#388E3C",
                    ).pack(pady=(0, 10))
                    ctk.CTkLabel(
                        update_win,
                        text="Deseja atualizar o título do template para o nome do NocoDB?",
                        font=ctk.CTkFont(size=13),
                    ).pack(pady=(0, 10))

                    btn_frame = ctk.CTkFrame(update_win)
                    btn_frame.pack(pady=10)
                    result = {"resp": None}

                    def confirmar():
                        result["resp"] = True
                        update_win.destroy()

                    def cancelar():
                        result["resp"] = False
                        update_win.destroy()

                    ctk.CTkButton(
                        btn_frame,
                        text="Sim",
                        fg_color="#388E3C",
                        command=confirmar,
                        width=80,
                    ).pack(side="left", padx=10)
                    ctk.CTkButton(
                        btn_frame,
                        text="Não",
                        fg_color="#A94444",
                        command=cancelar,
                        width=80,
                    ).pack(side="left", padx=10)
                    update_win.wait_window()
                    resp = result["resp"]
                    if resp:
                        mover = False
                        move_result = {"resp": None}

                        def mover_pasta():
                            move_result["resp"] = True
                            move_win.destroy()

                        def manter_pasta():
                            move_result["resp"] = False
                            move_win.destroy()

                        move_win = self._create_toplevel()
                        move_win.title("Mover de Pasta?")
                        move_win.geometry("420x170")
                        move_win.grab_set()
                        ctk.CTkLabel(
                            move_win,
                            text=f"O template está atualmente na pasta '{old_category}'.\nDeseja mover para outra pasta?",
                            font=ctk.CTkFont(size=13),
                        ).pack(pady=(18, 10))
                        btn_frame2 = ctk.CTkFrame(move_win)
                        btn_frame2.pack(pady=10)
                        ctk.CTkButton(
                            btn_frame2,
                            text="Sim",
                            fg_color="#388E3C",
                            command=mover_pasta,
                            width=80,
                        ).pack(side="left", padx=10)
                        ctk.CTkButton(
                            btn_frame2,
                            text="Não",
                            fg_color="#A94444",
                            command=manter_pasta,
                            width=80,
                        ).pack(side="left", padx=10)
                        move_win.wait_window()
                        mover = move_result["resp"]
                        if mover:
                            nova_pasta = prompt_pasta(
                                categorias, pasta_atual=old_category
                            )
                            if not nova_pasta:
                                self.show_snackbar(
                                    "Importação cancelada.", toast_type="info"
                                )
                                return
                            full_new_name = (
                                f"{nova_pasta} / {nome}"
                                if nova_pasta != "Geral"
                                else nome
                            )
                        else:
                            full_new_name = (
                                f"{old_category} / {nome}"
                                if old_category != "Geral"
                                else nome
                            )
                        self.template_manager.save_template(
                            existing_name, full_new_name, local_content
                        )
                        old_meta = self.template_manager.meta.meta.get(
                            existing_name, {}
                        ).copy()
                        self.template_manager.meta.meta[full_new_name] = old_meta
                        self.template_manager.meta._save()
                        if existing_name != full_new_name:
                            self.template_manager.meta.remove_meta(existing_name)
                        self.show_snackbar(
                            f"Título atualizado para '{full_new_name}'!",
                            toast_type="success",
                        )
                        self.template_manager.load_templates()
                        self.template_selector.configure(
                            values=self.template_manager.get_display_names()
                        )
                    else:
                        self.show_snackbar(
                            "Template já existe e está atualizado!", toast_type="info"
                        )
                else:
                    self.show_snackbar(
                        "Template já existe e está atualizado!", toast_type="info"
                    )
                return

        # Se não existe, pergunta a pasta e salva com o nome do NocoDB
        pasta = prompt_pasta(categorias)
        if pasta is None:
            self.show_snackbar("Importação cancelada.", toast_type="info")
            return
        full_name = f"{pasta} / {nome}" if pasta != "Geral" else nome
        self.template_manager.add_template(full_name, conteudo)
        if nocodb_id:
            # Sempre usa o método _ensure_entry, que já padroniza e garante a existência da entry
            self.template_manager.meta._ensure_entry(full_name)
            meta_key = self.template_manager.meta._find_meta_key(full_name)
            self.template_manager.meta.meta[meta_key]["nocodb_id"] = str(nocodb_id)
            self.template_manager.meta._save()
            # Remove entradas duplicadas de meta.json (com o mesmo nocodb_id)
            for name in list(self.template_manager.meta.meta.keys()):
                if name != full_name and self.template_manager.meta.meta[name].get(
                    "nocodb_id"
                ) == str(nocodb_id):
                    self.template_manager.meta.remove_meta(name)
        # Recarrega os templates e seleciona o novo
        self.template_manager.load_templates()

        # Atualiza o estado da interface principal
        self.current_template = full_name
        display_name = self.template_manager.meta.get_display_name(full_name)
        self.current_template_display.set(display_name)

        # Atualiza os seletores em toda a aplicação
        self._refresh_all_template_selectors(select_template=full_name)

        # Força o carregamento do template
        self.load_template_placeholders()

        # Notifica o usuário
        self.show_snackbar(
            f"Template '{display_name}' importado e carregado!",
            toast_type="success",
            duration=2500,
        )

    def remover_templates_nocodb_id_menos_um(self):
        # Remove todos os templates e metas com nocodb_id == "-1"
        to_remove = [
            name
            for name, meta in self.template_manager.meta.meta.items()
            if meta.get("nocodb_id") == "-1"
        ]
        for name in to_remove:
            self.template_manager.delete_template(name)
        self.template_manager.load_templates()
        self._refresh_all_template_selectors()

    def show_nocodb_templates(self):
        import customtkinter as ctk

        # Cria a janela principal do diálogo
        nocodb_templates_dialog = self._create_toplevel()
        nocodb_templates_dialog.title("Templates Compartilhados")
        nocodb_templates_dialog.geometry("700x500")
        nocodb_templates_dialog.grab_set()

        # Frame principal
        main_frame = ctk.CTkFrame(nocodb_templates_dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # OptionMenu para seleção
        nocodb_templates_list = ctk.CTkOptionMenu(main_frame, width=80)
        nocodb_templates_list.grid(
            row=0, column=0, sticky="ew", padx=(0, 20), pady=(0, 10)
        )

        # Card fixo (não expansível)
        card_frame = ctk.CTkFrame(main_frame, fg_color="#222", corner_radius=10)
        card_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 20), pady=(0, 10))
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)

        # Nome do template (expansível)
        label_nome = ctk.CTkTextbox(
            card_frame, height=1, font=ctk.CTkFont(size=16, weight="bold"), wrap="word"
        )
        label_nome.pack(fill="x", padx=16, pady=(16, 2))
        label_nome.configure(
            state="disabled", border_width=0, fg_color="#222", text_color="#fff"
        )

        # Descrição (sempre visível, com quebras de linha, expansível)
        desc_box = ctk.CTkTextbox(
            card_frame, wrap="word", height=1, font=ctk.CTkFont(size=13)
        )
        desc_box.pack(fill="both", expand=True, padx=16, pady=(0, 2))
        desc_box.configure(
            state="disabled", border_width=0, fg_color="#222", text_color="#fff"
        )

        # Linha separadora para detalhes extras
        sep = ctk.CTkFrame(card_frame, height=2, fg_color="#444")
        sep.pack(fill="x", padx=16, pady=(8, 4))

        # Rodapé do card (autor, criado, atualizado) em uma linha, todos como labels
        footer_frame = ctk.CTkFrame(card_frame, fg_color="#222")
        footer_frame.pack(fill="x", side="bottom", padx=8, pady=(0, 12))

        label_teams = ctk.CTkLabel(
            footer_frame,
            text="",
            font=ctk.CTkFont(size=12, slant="italic"),
            anchor="w",
            justify="left",
        )
        label_teams.pack(side="left", fill="x", expand=True, padx=(0, 8), pady=0)

        label_created = ctk.CTkLabel(
            footer_frame, text="", font=ctk.CTkFont(size=11), anchor="w", justify="left"
        )
        label_created.pack(side="left", fill="x", expand=True, padx=(0, 8), pady=0)

        label_updated = ctk.CTkLabel(
            footer_frame, text="", font=ctk.CTkFont(size=11), anchor="w", justify="left"
        )
        label_updated.pack(side="left", fill="x", expand=True, padx=(0, 0), pady=0)

        # Botão de importar
        btn_importar = ctk.CTkButton(main_frame, text="Importar", fg_color="#388E3C")
        btn_importar.grid(row=2, column=0, sticky="ew", pady=(10, 0))

        # --- Lógica de preenchimento e seleção ---
        api_url = "https://app.nocodb.com"
        base_name = "p02k6lvq2via5sv"
        table_name = "mpvh49wivawwdx7"
        token = "UifsYUdNbfJFWVz3t7oOIPo2Idd51ykk2I-9FnzK"

        try:
            from nocodb_api import fetch_nocodb_templates
            templates = fetch_nocodb_templates(api_url, base_name, table_name, token)
        except Exception as e:
            # Se a resposta da API tiver texto, printa no console
            if hasattr(e, "response") and e.response is not None:
                try:
                    print("[NocoDB API ERROR]", e.response.text)
                except Exception:
                    print("[NocoDB API ERROR] (sem texto de resposta)")
            else:
                print("[NocoDB API ERROR]", str(e))
            self.show_snackbar(
                "Erro ao buscar templates. Veja o log para detalhes.",
                toast_type="error",
            )
            templates = []
        if not templates:
            print("[NocoDB] Nenhum template retornado ou erro na consulta.")

        opcoes = []
        for template in templates:
            nome = template.get("Template Name", "")
            opcoes.append(nome)

        if opcoes:
            nocodb_templates_list.configure(values=opcoes)
            nocodb_templates_list.set(opcoes[0])
        else:
            nocodb_templates_list.configure(values=["Nenhum template"])
            nocodb_templates_list.set("Nenhum template")

        def mostrar_card(nome_template):
            idx = opcoes.index(nome_template) if nome_template in opcoes else 0
            template = templates[idx] if templates else {}

            # Nome sempre visível (expansível)
            label_nome.configure(state="normal")
            label_nome.delete("1.0", "end")
            label_nome.insert("1.0", template.get("Template Name", ""))
            label_nome.configure(state="disabled")

            # Descrição no textbox, com quebras de linha preservadas (expansível)
            desc = template.get("Template Description", "")
            desc_box.configure(state="normal")
            desc_box.delete("1.0", "end")
            desc_box.insert("1.0", desc)
            desc_box.configure(state="disabled")

            # Rodapé: autor, criado, atualizado (labels, sempre expandidos)
            label_teams.configure(text=f"Autor: {template.get('Teams', '')}")
            label_created.configure(text=f"Criado em: {template.get('CreatedAt', '')}")
            updated = template.get("UpdatedAt", "")
            if (
                not updated
                or str(updated).strip() == ""
                or updated == template.get("CreatedAt", "")
            ):
                label_updated.configure(text="Atualizado em: Nunca - Template Original")
            else:
                label_updated.configure(text=f"Atualizado em: {updated}")

        def importar_template():
            selecionado = nocodb_templates_list.get()
            if selecionado and selecionado in opcoes:
                idx = opcoes.index(selecionado)
                template = templates[idx]
                self.importar_template(template)
                nocodb_templates_dialog.destroy()

        nocodb_templates_list.configure(command=mostrar_card)
        btn_importar.configure(command=importar_template)

        # Mostra o card do primeiro template ao abrir
        if opcoes:
            mostrar_card(opcoes[0])

    def show_snackbar(
        self,
        message="Copiado com sucesso!",
        duration=1500,
        toast_type="success",
        parent=None,
    ):
        styles = {
            "success": {"fg": "#388E3C", "icon": "✔"},
            "error": {"fg": "#D32F2F", "icon": "✖"},
            "warning": {"fg": "#D4A326", "icon": "⚠"},
            "info": {"fg": "#1976D2", "icon": "ℹ"},
            "default": {"fg": "#AE00FF", "icon": "•"},
        }

        style = styles.get(toast_type, styles["default"])
        text = f"{style['icon']} {message}"

        # Usa o parent fornecido ou self
        target = parent if parent is not None else self

        # Cria a janela flutuante
        snackbar = self._create_toplevel(target)
        snackbar.overrideredirect(True)
        snackbar.attributes("-topmost", True)
        snackbar.configure(fg_color=style["fg"])

        label = ctk.CTkLabel(
            snackbar,
            text=text,
            text_color="white",
            font=ctk.CTkFont(size=12),
            padx=15,
            pady=8,
        )
        label.pack()

        target.update_idletasks()
        width = snackbar.winfo_reqwidth()
        height = snackbar.winfo_reqheight()
        x = target.winfo_x() + int((target.winfo_width() - width) / 2)
        y = target.winfo_y() + target.winfo_height() - height - 20

        snackbar.geometry(f"{width}x{height}+{x}+{y}")
        snackbar.attributes("-alpha", 0)

        # Fade in
        def fade_in(opacity=0.0):
            if opacity >= 1.0:
                snackbar.attributes("-alpha", 1.0)
            else:
                snackbar.attributes("-alpha", opacity)
                target.after(20, lambda: fade_in(opacity + 0.1))

        fade_in()

        # Desaparecer com fade out
        def fade_out(opacity=1.0):
            if opacity <= 0:
                snackbar.destroy()
            else:
                snackbar.attributes("-alpha", opacity)
                target.after(30, lambda: fade_out(opacity - 0.1))

        target.after(duration, lambda: fade_out())

    def process_conditionals(self, template, field_values):
        """
        Substitui todos os padrões $Campo?Texto|Alternativa$ no template.
        Se o campo estiver preenchido, usa Texto (pode conter outros placeholders).
        Se não, usa Alternativa (pode conter outros placeholders).
        """

        def cond_replacer(match):
            field = match.group(1)
            if "?" in field and "|" in field:
                # Suporte a aninhamento acidental, pega só o primeiro ?
                field_name, rest = field.split("?", 1)
                if "|" in rest:
                    text_true, text_false = rest.split("|", 1)
                else:
                    text_true, text_false = rest, ""
                value = field_values.get(field_name, "")
                # Se for checkbox, só considera "Sim" como verdadeiro
                if field_name.startswith("[checkbox]"):
                    is_true = value == "Sim"
                else:
                    is_true = bool(value)
                # Recursivo: processa condicional dentro de Texto/Alternativa
                if is_true:
                    return self.process_conditionals(text_true, field_values)
                else:
                    return self.process_conditionals(text_false, field_values)
            return match.group(0)

        # Regex: $Campo?Texto|Alternativa$
        return re.sub(
            r"\$([a-zA-Z0-9 _\-çÇáéíóúãõâêîôûÀ-ÿ\[\]%:/\?\|]+)\$",
            cond_replacer,
            template,
        )

    # Mantém uma lista global de tooltips abertos para garantir que todos sejam fechados ao passar o mouse novamente
    _all_tooltips: list[ctk.CTkToplevel] = []

    def create_tooltip(
        self, widget, text, fg_color="#222", text_color="#fff", immediate_hide=True
    ):
        """
        Attach a custom tooltip to a widget. The tooltip appears on hover and disappears on leave.

        Args:
            widget: The widget to attach the tooltip to.
            text (str): The text to display in the tooltip.
            fg_color (str, optional): Background color of the tooltip. Defaults to "#222".
            text_color (str, optional): Text color of the tooltip. Defaults to "#fff".
            immediate_hide (bool, optional): Se True, esconde o tooltip imediatamente ao sair do mouse.
        """
        tooltip = {"window": None, "after_ids": set()}

        def destroy_all_tooltips():
            # Fecha todos os tooltips abertos em toda a aplicação
            for t in list(TemplateApp._all_tooltips):
                try:
                    t.destroy()
                except Exception:
                    pass
                try:
                    TemplateApp._all_tooltips.remove(t)
                except Exception:
                    pass

        def show_tooltip(event=None):
            destroy_all_tooltips()
            hide_tooltip()
            if tooltip["window"] is not None:
                return
            try:
                tooltip["window"] = tw = self._create_toplevel(widget)
                tw.overrideredirect(True)
                tw.attributes("-topmost", True)
                tw.transient(
                    widget.winfo_toplevel()
                )  # Faz o tooltip acompanhar a janela principal
                label = ctk.CTkLabel(
                    tw,
                    text=text,
                    font=ctk.CTkFont(size=11),
                    text_color=text_color,
                    fg_color=fg_color,
                    padx=7,
                    pady=3,
                )
                label.pack()
                widget.update_idletasks()
                x = widget.winfo_rootx() + widget.winfo_width() + 7
                y = widget.winfo_rooty() - 3
                tw.geometry(f"+{x}+{y}")

                # Garante que o tooltip seja destruído em várias situações
                def on_widget_destroy(event=None):
                    hide_tooltip()

                def schedule_auto_hide():
                    # Agenda destruição automática após 0.5s
                    if tooltip.get("auto_hide_id"):
                        try:
                            widget.after_cancel(tooltip["auto_hide_id"])
                        except Exception:
                            pass
                    tooltip["auto_hide_id"] = widget.after(500, hide_tooltip)

                def cancel_auto_hide():
                    # Cancela destruição automática se o mouse voltar
                    if tooltip.get("auto_hide_id"):
                        try:
                            widget.after_cancel(tooltip["auto_hide_id"])
                        except Exception:
                            pass
                        tooltip["auto_hide_id"] = None

                widget.bind("<Destroy>", on_widget_destroy, add="+")
                tw.bind("<Destroy>", on_widget_destroy, add="+")
                tw.bind("<Button-1>", hide_tooltip, add="+")  # Fecha ao clicar
                widget.winfo_toplevel().bind("<Button-1>", hide_tooltip, add="+")

                # Gerencia auto-hide ao entrar/sair do tooltip
                tw.bind("<Enter>", lambda e: cancel_auto_hide(), add="+")
                tw.bind("<Leave>", lambda e: schedule_auto_hide(), add="+")
                # Agenda destruição automática
                schedule_auto_hide()
                # Adiciona à lista global
                TemplateApp._all_tooltips.append(tw)
            except Exception:
                pass

        def hide_tooltip(event=None):
            # Cancela todos os afters pendentes do tooltip
            for after_id in list(tooltip["after_ids"]):
                try:
                    widget.after_cancel(after_id)
                except Exception:
                    pass
                tooltip["after_ids"].discard(after_id)
            if tooltip["window"] is not None:
                try:
                    if tooltip["window"] in TemplateApp._all_tooltips:
                        TemplateApp._all_tooltips.remove(tooltip["window"])
                    tooltip["window"].destroy()
                    # Remove os bindings da janela principal
                    # Remove os bindings e cancela o auto-hide
                    try:
                        widget.winfo_toplevel().unbind(
                            "<Button-1>", tooltip.get("toplevel_binding")
                        )
                    except Exception:
                        pass
                    if tooltip.get("auto_hide_id"):
                        try:
                            widget.after_cancel(tooltip["auto_hide_id"])
                        except Exception:
                            pass
                        tooltip["auto_hide_id"] = None
                except Exception:
                    pass
                tooltip["window"] = None

        def force_hide_tooltip(event=None):
            # Força o fechamento do tooltip em qualquer situação, com pequeno delay para evitar race
            hide_tooltip()
            after_id = widget.after(1, hide_tooltip)
            tooltip["after_ids"].add(after_id)

        # Cancela tooltips ao fechar a janela principal
        def cancel_tooltip_on_app_close(event=None):
            hide_tooltip()
            for after_id in list(tooltip["after_ids"]):
                try:
                    widget.after_cancel(after_id)
                except Exception:
                    pass
                tooltip["after_ids"].discard(after_id)

        widget.bind("<Enter>", show_tooltip)
        widget.bind("<Leave>", force_hide_tooltip)
        widget.bind("<ButtonPress>", force_hide_tooltip)
        widget.bind("<FocusOut>", force_hide_tooltip)
        self.bind("<Destroy>", cancel_tooltip_on_app_close, add="+")
        return show_tooltip, hide_tooltip

    def animate_field_success(self, entry):
        """Anima um campo quando ele é validado com sucesso.

        Muda temporariamente a cor da borda para verde e faz uma animação
        de pulso suave. Depois restaura a cor da borda baseada no template
        atual.
        """
        if self.visual_feedback_enabled:
            entry.configure(border_color="#00C853")  # verde sucesso

            # Pulse: aumentar e voltar o tamanho da fonte levemente
            def pulse(step=0):
                size = 12 + (1 if step % 2 == 0 else 0)
                entry.configure(font=ctk.CTkFont(size=size))
                if step < 4:
                    self._safe_after(100, lambda: pulse(step + 1))
                else:
                    entry.configure(font=ctk.CTkFont(size=12))
                    # Procura o nome do campo para atualizar apenas sua borda
                    for name, field in self.entries.items():
                        if field == entry:
                            self._update_single_field_border(name, entry)
                            break

            pulse()

    def pulse_button_success(
        self, button, original_color="#7E57C2", success_color="#00C853"
    ):
        # Salva a cor original
        button.configure(fg_color=success_color)

        def restore():
            button.configure(fg_color=original_color)

        self._safe_after(500, restore)

    def save_window_config(self):
        self.update_idletasks()
        width, height = self.winfo_width(), self.winfo_height()

        if height >= 300:
            geometry_str = self.geometry()
            try:
                config = load_config()
                config["geometry"] = geometry_str
                save_config(config)
            except Exception as e:
                print(f"[ERRO ao salvar config]: {e}")

    def load_window_config(self):
        try:
            config = load_config()
            geometry = config.get("geometry")
            if geometry and "x" in geometry:
                self.geometry(geometry)
        except Exception:
            pass

    def apply_saved_geometry(self):
        self.load_window_config()

    # --- Configuração de campos expansíveis ---
    def load_expandable_fields_config(self):
        try:
            config = load_config()
            return config.get("expandable_fields", ["Procedimento Executado", "Problema Relatado"])
        except Exception:
            return ["Procedimento Executado", "Problema Relatado"]

    def save_expandable_fields_config(self):
        try:
            config = load_config()
            config["expandable_fields"] = self.expandable_fields
            save_config(config)
        except Exception:
            pass

    def open_settings(self):
        # Permite apenas uma janela de configurações por vez
        if hasattr(self, "_settings_window") and self._settings_window is not None:
            try:
                self._settings_window.focus()
                self._settings_window.lift()
                return
            except Exception:
                self._settings_window = None  # Se a janela foi fechada manualmente

        self._settings_window = SettingsWindow(self)
        try:
            self._settings_window.focus()
            self._settings_window.lift()
        except Exception:
            pass

        def _release_settings_ref(event=None):
            if getattr(self, "_settings_window", None) is event.widget:
                self._settings_window = None

        self._settings_window.bind("<Destroy>", _release_settings_ref)

    def open_log_viewer(self):
        # Log viewer removed from application UI.
        raise RuntimeError("Log viewer has been removed from the application UI")

    def reload_theme_and_interface(self):
        # 1. Salva o estado atual
        state = {
            "current_template": self.current_template,
            "current_template_display": self.current_template_display.get(),
            "dynamic_fields": list(self.dynamic_fields),
            "fixed_field_modes": dict(self.fixed_field_modes),
            "expandable_fields": list(self.expandable_fields),
            "field_values": {},
        }
        for k, v in self.entries.items():
            try:
                state["field_values"][k] = v.get()
            except Exception:
                try:
                    state["field_values"][k] = v.get("1.0", "end-1c")
                except Exception:
                    state["field_values"][k] = ""

        # 2. Destroi widgets principais
        for widget in self.winfo_children():
            widget.destroy()

        # 3. Recria interface
        self._build_main_interface()
        # 4. Restaura estado
        self.current_template = state["current_template"]
        self.current_template_display.set(state["current_template_display"])
        self.dynamic_fields = state["dynamic_fields"]
        self.fixed_field_modes = state["fixed_field_modes"]
        self.expandable_fields = state["expandable_fields"]
        self.load_template_placeholders()
        # 5. Restaura valores dos campos
        for k in self.entries:
            valor_antigo = state["field_values"].get(k, None)
            entry = self.entries[k]
            if valor_antigo not in (None, ""):
                # Primeiro limpa o campo com segurança
                self._reset_field_value(entry)
                # Depois insere o valor antigo
                try:
                    if isinstance(entry, ctk.CTkTextbox):
                        entry.insert("1.0", valor_antigo)
                    elif isinstance(entry, ctk.CTkEntry):
                        entry.insert(0, valor_antigo)
                    elif isinstance(entry, (ctk.StringVar, ctk.BooleanVar)):
                        entry.set(valor_antigo)
                    elif isinstance(entry, (ctk.CTkSwitch, ctk.CTkCheckBox)):
                        try:
                            if valor_antigo.lower() in ("true", "1", "yes", "on"):
                                if hasattr(entry, "select"):
                                    entry.select()
                                else:
                                    entry._check_state = True
                                    entry._update_image()
                        except Exception as e:
                            logger.debug(
                                f"Erro ao restaurar valor {valor_antigo} para {k}: {e}"
                            )
                    elif hasattr(entry, "insert"):
                        entry.insert(0, valor_antigo)
                    elif hasattr(entry, "set"):
                        entry.set(valor_antigo)
                except Exception as e:
                    logger.warning(
                        f"Erro ao restaurar valor {valor_antigo} para {k}: {e}"
                    )

    def load_theme_config(self):
        try:
            config = load_config()
            return config.get("theme_name", "green"), config.get("appearance_mode", "dark")
        except Exception:
            return "green", "dark"

    def save_theme_config(self, theme_name, appearance_mode):
        try:
            config = load_config()
            config["theme_name"] = theme_name
            config["appearance_mode"] = appearance_mode
            save_config(config)
        except Exception:
            pass

    def _safe_after(self, delay, callback):
        """Agende um after e registre o ID para cancelamento seguro."""
        after_id = self.after(delay, callback)
        self._after_ids.add(after_id)
        return after_id

    def _safe_after_cancel(self, after_id):
        """Cancele um after agendado e remova do registro."""
        try:
            self.after_cancel(after_id)
        except Exception:
            pass
        self._after_ids.discard(after_id)

    def _cancel_all_afters(self):
        """Cancele todos os afters agendados."""
        for after_id in list(self._after_ids):
            self._safe_after_cancel(after_id)
        self._after_ids.clear()

    def on_close(self):
        self._cancel_all_afters()
        self.update_idletasks()  # Garante que a geometria seja a real
        self.save_window_config()
        self.destroy()


# Define quais símbolos são exportados
__all__ = ["TemplateApp", "placeholder_engine"]
