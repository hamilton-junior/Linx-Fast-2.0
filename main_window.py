import customtkinter as ctk
import pyperclip
import json
import os
import re
import datetime
import sys
import requests
from template_editor import TemplateEditor
from template_manager import TemplateManager
from theme_manager import ThemeManager
from dpm import DailyPasswordManager
from settings_window import SettingsWindow
from customtkinter import CTkInputDialog
from nocodb_api import fetch_nocodb_templates

try:
    from version import VERSION, COMMIT, BUILD_DATE
except ImportError:
    VERSION, COMMIT, BUILD_DATE = "dev", "dev", "dev"

# --- PlaceholderEngine e instância global ---
class PlaceholderEngine:
    """
    Manages dynamic placeholder substitution in text templates.

    Allows registration of custom handlers for placeholders and provides built-in support for date/time placeholders like $Agora$ and $Agora[formato]$.
    """
    def __init__(self):
        self.handlers = {}

    def register_handler(self, name, func):
        self.handlers[name] = func

    def process(self, text):
        def replacer(match):
            ph = match.group(1)
            # Handler customizado: $Agora[formato]$ ou $Agora$
            if ph == "Agora":
                # Formato padrão para $Agora$
                fmt = "%H:%M"
                try:
                    return datetime.datetime.now().strftime(fmt)
                except Exception:
                    return match.group(0)
            if ph.startswith("Agora[") and ph.endswith("]"):
                fmt = ph[6:-1]
                try:
                    return datetime.datetime.now().strftime(fmt)
                except Exception:
                    return match.group(0)
            # Handler padrão
            handler = self.handlers.get(ph)
            if handler:
                return handler()
            return match.group(0)
        # Regex: $Nome$ ou $Agora[...formato...]$ ou $Agora$
        return re.sub(r"\$([a-zA-Z0-9 _\-çÇáéíóúãõâêîôûÀ-ÿ\[\]%:/]+)\$", replacer, text)

# Instância global da engine
placeholder_engine = PlaceholderEngine()
# Handlers padrões
placeholder_engine.register_handler("Hoje", lambda: datetime.datetime.now().strftime("%d/%m/%Y"))
DIAS_SEMANA_PT = {
    "Monday": "segunda-feira",
    "Tuesday": "terça-feira",
    "Wednesday": "quarta-feira",
    "Thursday": "quinta-feira",
    "Friday": "sexta-feira",
    "Saturday": "sábado",
    "Sunday": "domingo"
}

placeholder_engine.register_handler(
    "DiaSemana",
    lambda: DIAS_SEMANA_PT.get(datetime.datetime.now().strftime("%A"), datetime.datetime.now().strftime("%A"))
)
placeholder_engine.register_handler("HoraMinuto", lambda: datetime.datetime.now().strftime("%H:%M"))
placeholder_engine.register_handler("HoraMinutoSegundo", lambda: datetime.datetime.now().strftime("%H:%M:%S"))

class TemplateApp(ctk.CTk):
    def __init__(self):
        if sys.platform == "win32":
            import ctypes
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(0)
            except Exception as e:
                print(f"[DPI WARNING] Could not set DPI awareness: {e}")

        super().__init__()
        self.title("Linx Fast 2.0")
        self.geometry("360x535")
        self.visual_feedback_enabled = True
        self._after_ids = set()  # IDs dos afters agendados

        # Carrega config de campos expansíveis
        self.expandable_fields = self.load_expandable_fields_config()

        # Carrega config de tema e aparência
        self.theme_name, self.appearance_mode = self.load_theme_config()
        ctk.set_appearance_mode(self.appearance_mode)
        theme_path = os.path.join("themes", f"{self.theme_name}.json")
        if self.theme_name in ("green", "blue", "dark-blue") or not os.path.exists(theme_path):
            ctk.set_default_color_theme(self.theme_name)
        else:
            ctk.set_default_color_theme(theme_path)

        # Inicialização das classes
        self.template_manager = TemplateManager()
        self.theme_manager = ThemeManager(theme_name=self.theme_name, mode=self.appearance_mode)
        self.password_manager = DailyPasswordManager()
        self.fixed_fields = [
            "Nome", "Problema Relatado", "CNPJ",
            "Telefone", "Email", "Protocolo", "Procedimento Executado"
        ]
        self.dynamic_fields = []
        self.entries = {}
        self.field_widgets = {}
        self.fixed_field_modes = {}

        self.current_template = "Selecione o template..."
        self.current_template_display = ctk.StringVar(value=self.template_manager.meta.get_display_name(self.current_template))

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
            selector_frame,
            text="📍",
            command=self.toggle_always_on_top,
            width=30
        )
        self.pin_button.pack(side="left", padx=(0, 5))

        self.template_selector = ctk.CTkOptionMenu(
            selector_frame,
            variable=self.current_template_display,
            values=self.template_manager.get_display_names(),
            command=self.on_template_change,
            width=300
        )
        self.template_selector.pack(side="left")

        # Botão de Configurações ao lado do seletor de template
        self.settings_button = ctk.CTkButton(
            selector_frame,
            text="⚙️",
            width=32,
            anchor="center",
            command=self.open_settings
        )
        self.settings_button.pack(side="left", padx=(5, 0))

        self.form_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.form_frame.grid(row=1, column=0, sticky="nsew")
        self.form_frame.grid_columnconfigure(0, weight=1)

        self.draw_all_fields()
        
        # Botão de Senha Diária
        self.btn_daily_password = ctk.CTkButton(self.main_frame, text="PW", command=self.handle_daily_password, width=1, height=30,anchor="center")
        self.btn_daily_password.grid(sticky="w",row=2, column=0, padx=(5,0),pady=(5, 0))
        self.btn_daily_password.bind("<Button-3>", lambda e: (self.password_manager.set_today_password(None), self.show_snackbar("Senha diária resetada!", toast_type="info")))

        # Botão de Limpar Campos
        self.btn_limpar_campos = ctk.CTkButton(
            self.main_frame,
            text="❌",
            fg_color="#A94444",
            hover_color="#912F2F",
            anchor="right",
            width=3,
            height=30,
            command=self.limpar_campos
        )
        self.btn_limpar_campos.grid(row=2, column=0, pady=(5, 0), sticky="e")
        # Tooltip para o botão de limpar campos
        self.create_tooltip(self.btn_limpar_campos, "Limpar todos os campos", fg_color="#A94444")



        #Botão de Copiar Template
        ctk.CTkButton(self.main_frame, text="Copiar para área de transferência",
                        fg_color="#7E57C2", hover_color="#6A4BB3",
                        command=self.copy_template).grid(row=2, column=0, pady=(5, 5))
        #Botão de Visualizar Template
        ctk.CTkButton(self.main_frame, text="Visualizar Resultado",
                        fg_color="#5E35B1", hover_color="#512DA8",
                        command=self.preview_template).grid(row=3, column=0, pady=(5, 5))
        #Botão de Editar Template
        ctk.CTkButton(self.main_frame, text="Editar Templates",
                        fg_color="#7E57C2", hover_color="#6A4BB3",
                        command=self.open_template_editor).grid(row=4, column=0, pady=(5, 5))
        #Botão de Adicionar Campo
        self.add_btn = ctk.CTkButton(self.main_frame, text="+ Adicionar Campo", width=150, height=30,
                        command=self.prompt_new_field,
                        fg_color="#333", hover_color="#444", font=ctk.CTkFont(size=12))
        self.add_btn.grid(row=5, column=0, pady=(5, 2))
        #Botão de Modo Simples
        ctk.CTkButton(self.main_frame, text="Modo Simples",
                        fg_color="#5E35B1", hover_color="#4527A0",
                        command=self.open_quick_mode).grid(row=6, column=0, pady=(5, 5))

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
            command=self.on_bug_button_click
        )
        self.info_button.grid(row=0, column=2, sticky="w", padx=(8, 2))

        # Label de Créditos do Autor (centralizada)
        label_autor = ctk.CTkLabel(
            bottom_frame,
            text="By Hamilton Junior",
            font=ctk.CTkFont(size=10, slant="italic"),
            text_color="#888888",
            anchor="s",
            justify="center"
        )
        label_autor.grid(row=0, column=1, sticky="ew", padx=(2, 2))


        self.main_frame.grid_rowconfigure(100, weight=0)

        self._init_undo_redo()
        self._bind_undo_redo_shortcuts()

    def on_bug_button_click(self):
        # Abre uma janela com links para formulários do NocoDB e exibe uma imagem da pasta /assets/icons/images
        import webbrowser
        import os

        links = [
            ("Envio de Templates", "https://app.nocodb.com/#/nc/form/99e96b28-cb03-4710-9318-7b1d5849d9e0"),
            ("Sugestões", "https://app.nocodb.com/#/nc/form/0058474a-0f28-4d3d-af60-1727a29ab431"),
            ("Report-a-bug", "https://app.nocodb.com/#/nc/form/5dd88074-bbf3-457f-b105-816652c79ddf"),
        ]

        win = ctk.CTkToplevel(self)
        win.title("Informações & Feedback")
        win.geometry("250x285")
        win.resizable(True, True)
        win.transient(self)
        win.grab_set()

        # --- Exibe uma pequena imagem no topo ---
        ctk.CTkLabel(win, text="Contribua com o app!", font=ctk.CTkFont(size=15, weight="bold")).pack(pady=(8, 8))

        try:
            from PIL import Image
            base_dir = os.path.dirname(os.path.abspath(__file__))
            img_path = os.path.join(base_dir, "assets", "images", "logo.png")
            if os.path.exists(img_path):
                pil_image = Image.open(img_path)
                image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(64, 64))
                ctk.CTkLabel(win, image=image, text="").pack(pady=(12, 2))
        except Exception as e:
            print(f"Erro ao carregar imagem: {e}")

        for name, url in links:
            def open_link(u=url):
                webbrowser.open_new(u)
            btn = ctk.CTkButton(
                win,
                text=name,
                width=150,
                command=open_link
            )
            btn.pack(pady=6)

        ctk.CTkLabel(
            win,
            text="Ao enviar um formulário, gentileza informar seu email do Teams para facilitar o contato.",
            font=ctk.CTkFont(size=10),
            wraplength=245,
            text_color="#888"
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
            structure_changed = (
                current_keys != snapshot_keys or
                any(
                    (isinstance(self.entries.get(k), ctk.CTkTextbox) != isinstance(snapshot.get(k, ""), str) and "\n" in str(snapshot.get(k, "")))
                    for k in snapshot_keys if k in self.entries
                )
            )

            if "_dynamic_fields" in snapshot and self.dynamic_fields != list(snapshot["_dynamic_fields"]):
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


    # TODO: Mover métodos auxiliares para módulos separados (fields.py, visual_feedback.py, utils.py)
    # TODO: Implementar undo/redo e feedback visual aprimorado nas próximas etapas


    def draw_all_fields(self):
        # Salva valores antigos, tanto de Entry quanto de Textbox
        old_values = {}
        for k, v in self.entries.items():
            try:
                old_values[k] = v.get()
            except Exception:
                try:
                    old_values[k] = v.get("1.0", "end-1c")
                except Exception:
                    old_values[k] = ""

        for widget in self.form_frame.winfo_children():
            widget.destroy()
        self.entries.clear()
        self.field_widgets.clear()

        row = 0
        for field in self.fixed_fields:
            self._draw_field(field, row, old_values.get(field, ""), is_dynamic=False)
            row += 1
        for field in self.dynamic_fields:
            self._draw_field(field, row, old_values.get(field, ""), is_dynamic=True)
            row += 1

        self._safe_after(100, self.adjust_window_height)
        # Só salva snapshot se não estiver restaurando undo/redo
        if not getattr(self, "_restoring_undo_redo", False):
            self._push_undo()


    def _should_wrap_label(self, text):
        return len(text) > 15 and " " in text

    def _draw_field(self, name, row, value="", is_dynamic=True):
        import re
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
            row_frame,
            text=field_label,
            anchor="w",
            justify="left",
            width=160
        )
        label.grid(row=0, column=0, sticky="w", padx=(0, 5))

        # --- Campo inteligente ---
        #Checkbox: $[checkbox]Aceite$
        #Switch: $[switch]Ativo$
        #Radio: $[radio:Sim|Não|Talvez]Opção$
        #Condicional: $[checkbox]Aceite?Aceito|Não aceito$
        
        if field_type == "checkbox":
            var = ctk.BooleanVar(value=(value == "1" or value is True))
            entry = ctk.CTkCheckBox(row_frame, text="", variable=var)
            entry.grid(row=0, column=1, sticky="w")
            self.entries[name] = entry
        elif field_type == "switch":
            var = ctk.StringVar(value=value if value else "Sim")
            entry = ctk.CTkSwitch(row_frame, text="", variable=var, onvalue="Sim", offvalue="Não", )
            entry.grid(row=0, column=1, sticky="w")
            self.entries[name] = entry
        elif field_type == "radio" and radio_options:
            var = ctk.StringVar(value=value if value in radio_options else radio_options[0])
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
            entry.original_border_color = entry.cget("border_color")
            self.entries[name] = entry
            

            def to_textbox(field_name=name, val=None, border_color=None):
                current_widget = self.entries[field_name]
                if isinstance(current_widget, ctk.CTkTextbox):
                    return current_widget
                if val is None:
                    val = current_widget.get()
                if border_color is None:
                    border_color = current_widget.cget("border_color")
                current_widget.grid_forget()
                textbox = ctk.CTkTextbox(row_frame, height=60, wrap="word", border_width=2)
                if val:
                    textbox.insert("1.0", val)
                textbox.grid(row=0, column=1, sticky="ew")
                textbox.original_border_color = textbox.cget("border_color")
                self.entries[field_name] = textbox
                textbox.after(1, lambda: textbox.configure(border_color=border_color))
                textbox.border_color = border_color
                textbox.focus()
                textbox.bind("<FocusOut>", lambda e, fn=field_name: to_entry(fn))
                # Undo/redo: salva snapshot a cada digitação
                textbox.bind("<KeyRelease>", lambda e: self._push_undo())
                # TAB navega para o próximo campo (transforma em Entry antes de avançar)
                def on_tab(e, fn=field_name):
                    to_entry(fn)
                    self._safe_after(1, lambda: self.focus_next_field(fn))
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
                current_widget.grid_forget()
                entry = ctk.CTkEntry(row_frame, placeholder_text=f"{field_name}")
                if val:
                    entry.insert(0, val)
                entry.grid(row=0, column=1, sticky="ew")
                entry.original_border_color = entry.cget("border_color")
                self.entries[field_name] = entry
                # Se o campo estiver vazio, mostra o placeholder
                if not val:
                    entry.delete(0, "end")
                    entry.configure(placeholder_text=field_name)
                entry.bind("<FocusIn>", lambda e, fn=field_name: to_textbox(fn))
                entry.bind("<KeyRelease>", lambda e: self._push_undo())
                if val and getattr(current_widget, "border_color", None) == "red":
                    self.animate_field_success(entry)
                # Redimensiona a janela ao voltar para Entry
                self.adjust_window_height()


            # Intercepta TAB e Shift+TAB no Entry ANTES de expandir
            def on_entry_tab(event, fn=name):
                if event.keysym == "Tab":
                    self.focus_next_field(fn)
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
                # Salva valor e cor da borda ANTES de destruir o widget
                if isinstance(current_widget, ctk.CTkEntry):
                    val = current_widget.get()
                    current_border_color = current_widget.cget("border_color")
                elif isinstance(current_widget, ctk.CTkTextbox):
                    val = current_widget.get("1.0", "end-1c")
                    current_border_color = current_widget.cget("border_color")
                else:
                    val = ""
                    current_border_color = "#3a3a3a"
                # Agora sim, remove e destrói todos os widgets da coluna 1
                for widget in row_frame.grid_slaves(row=0, column=1):
                    widget.grid_forget()
                    widget.destroy()
                # Alterna entre Entry e Textbox
                if isinstance(current_widget, ctk.CTkEntry):
                    textbox = ctk.CTkTextbox(row_frame, height=60, wrap="word", border_width=2)
                    if val:
                        textbox.insert("1.0", val)
                    textbox.grid(row=0, column=1, sticky="ew")
                    textbox.original_border_color = textbox.cget("border_color")
                    textbox.configure(border_color=current_border_color)
                    textbox.border_color = current_border_color
                    self.entries[field_name] = textbox
                    # Remove binds antigos e adiciona apenas um bind para voltar para entry
                    label.unbind("<Button-3>")
                    label.bind("<Button-3>", lambda e, fn=field_name: toggle_fixed_field_mode(e, fn))
                    # TAB e Shift+TAB navegam entre campos (cíclico)
                    textbox.bind("<Tab>", lambda e, fn=field_name: (self.focus_next_field(fn), "break"))
                    textbox.bind("<Shift-Tab>", lambda e, fn=field_name: (self.focus_prev_field(fn), "break"))
                    # Redimensiona a janela para manter botões visíveis
                    self.adjust_window_height()
                elif isinstance(current_widget, ctk.CTkTextbox):
                    entry = ctk.CTkEntry(row_frame, placeholder_text=f"{field_name}")
                    if val:
                        entry.insert(0, val)
                    entry.grid(row=0, column=1, sticky="ew")
                    entry.original_border_color = entry.cget("border_color")
                    entry.configure(border_color=current_border_color)
                    entry.border_color = current_border_color
                    self.entries[field_name] = entry
                    # Remove binds antigos e adiciona apenas um bind para ir para textbox
                    label.unbind("<Button-3>")
                    label.bind("<Button-3>", lambda e, fn=field_name: toggle_fixed_field_mode(e, fn))
                    # Redimensiona a janela para manter botões visíveis
                    self.adjust_window_height()

            if not is_dynamic:
                label.bind("<Button-3>", toggle_fixed_field_mode)

            # Inicialização padrão (Entry ou Textbox)
            if not is_dynamic and mode == "textbox":
                entry = ctk.CTkEntry(row_frame, placeholder_text=f"{name}")
                if value not in (None, ""):
                    entry.insert(0, value)
                entry.grid(row=0, column=1, sticky="ew")
                entry.original_border_color = entry.cget("border_color")
                self.entries[name] = entry
                entry.configure(border_color=entry.original_border_color)
                entry.border_color = entry.original_border_color
                # Troca imediatamente para textbox
                toggle_fixed_field_mode(None, name)
                entry.insert(0, value)
                entry.grid(row=0, column=1, sticky="ew")
                entry.original_border_color = entry.cget("border_color")
                self.entries[name] = entry
                entry.configure(border_color=entry.original_border_color)
                entry.border_color = entry.original_border_color
                # Troca imediatamente para textbox
                toggle_fixed_field_mode(None, name)
            else:
                entry = ctk.CTkEntry(row_frame, placeholder_text=f"{name}")
                if value not in (None, ""):
                    entry.insert(0, value)
                entry.grid(row=0, column=1, sticky="ew")
                self.entries[name] = entry
                entry.original_border_color = entry.cget("border_color")
                entry.configure(border_color=entry.original_border_color)
                entry.border_color = entry.original_border_color
                entry.configure(border_color=entry.original_border_color)
                entry.border_color = entry.original_border_color
                entry.bind("<KeyRelease>", lambda e: self._push_undo())

        if is_dynamic:
            btn_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
            btn_frame.grid(row=0, column=2, sticky="e", padx=(5, 0))

            up_btn = ctk.CTkButton(btn_frame, text="↑", width=30, command=lambda: self.move_field(name, -1))
            down_btn = ctk.CTkButton(btn_frame, text="↓", width=30, command=lambda: self.move_field(name, 1))
            del_btn = ctk.CTkButton(btn_frame, text="✕", width=30, fg_color="#A94444",
                                    command=lambda: self.remove_field(name))

            up_btn.pack(side="left", padx=2)
            down_btn.pack(side="left", padx=2)
            del_btn.pack(side="left", padx=2)



    def save_field_order(self):
        """Salva a ordem dos campos dinâmicos do template atual no arquivo config.json."""
        try:
            if os.path.exists("config.json"):
                with open("config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
            else:
                config = {}

            if "field_orders" not in config:
                config["field_orders"] = {}

            config["field_orders"][self.current_template] = self.dynamic_fields

            with open("config.json", "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            print(f"[ERRO ao salvar ordem dos campos]: {e}")

    def load_field_order(self):
        """Carrega a ordem dos campos dinâmicos do template atual, se existir."""
        try:
            if os.path.exists("config.json"):
                with open("config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
                field_orders = config.get("field_orders", {})
                order = field_orders.get(self.current_template)
                if order:
                    # Garante que só mantenha campos realmente presentes no template
                    self.dynamic_fields = [f for f in order if f in self.dynamic_fields] + [f for f in self.dynamic_fields if f not in order]
        except Exception as e:
            print(f"[ERRO ao carregar ordem dos campos]: {e}")



    def move_field(self, field, direction):
        self._push_undo()
        idx = self.dynamic_fields.index(field)
        new_idx = idx + direction
        if 0 <= new_idx < len(self.dynamic_fields):
            self.dynamic_fields[idx], self.dynamic_fields[new_idx] = self.dynamic_fields[new_idx], self.dynamic_fields[idx]
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
        popup = CTkInputDialog(text="Nome do novo campo (placeholder):", title="Adicionar Campo")
        field_name = popup.get_input()
        if field_name and field_name not in self.entries:
            self.dynamic_fields.append(field_name)
            self.draw_all_fields()
            self.save_field_order()

    def limpar_campos(self):
        self._push_undo()
        for name, entry in self.entries.items():
            if isinstance(entry, ctk.CTkTextbox):
                entry.delete("1.0", "end")
                entry.insert("1.0", "")
                entry.configure(border_color=entry.original_border_color)
            else:
                entry.delete(0, "end")
                entry.insert(0, "")
                entry.configure(placeholder_text=name)
                entry.configure(border_color=entry.original_border_color)

        self.show_snackbar("Campos limpos!", toast_type="info")


    def focus_next_field(self, current_name):
        keys = list(self.entries.keys())
        try:
            idx = keys.index(current_name)
            next_key = keys[(idx + 1) % len(keys)]  # cíclico
            entry = self.entries[next_key]
            # Se for StringVar (radio), pula para o próximo campo
            if isinstance(entry, ctk.StringVar):
                self.focus_next_field(next_key)
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
        self.pin_button.configure(fg_color="green" if new_state else self.theme_manager.get_theme_default_color(ctk.CTkButton, "fg_color"))
        self.pin_button.configure(text="📌" if new_state else "📍")
        if new_state:
            self.show_snackbar("PIN ativado!", toast_type="info")
        else:
            self.show_snackbar("PIN desativado!", toast_type="info")

    def copy_template(self):
        # Validate if a template is selected
        if not self.current_template or self.current_template == "Selecione o template...":
            self.show_snackbar("Selecione um template antes de copiar!", toast_type="error")
            return

        template = self.template_manager.get_template(self.current_template)
        tem_vazios = False

        # Descobre quais campos realmente estão no template atual
        placeholders = set(self.template_manager.extract_placeholders(template))

        # Também inclui campos usados em condicionais ($Campo?Texto|Alternativa$)
        import re
        cond_fields = set()
        for match in re.findall(r"\$([a-zA-Z0-9 _\-çÇáéíóúãõâêîôûÀ-ÿ\[\]%:/]+)\?", template):
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
                if hasattr(entry, "configure"):
                    entry.configure(border_color="red")
                    entry.border_color = "red"
                    entry.bind("<FocusIn>", lambda e, ent=entry: ent.configure(border_color=ent.original_border_color))
                    entry.bind(
                        "<FocusOut>",
                        lambda e, ent=entry: self.animate_field_success(ent)
                        if (ent.get("1.0", "end-1c") if isinstance(ent, ctk.CTkTextbox) else ent.get())
                        else None
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

        preview = ctk.CTkToplevel(self)
        preview.title("Visualização do Template")
        preview.geometry("600x400")
        preview.transient(self)
        preview.grab_set()

        box = ctk.CTkTextbox(preview, wrap="word")
        box.insert("1.0", template)
        box.configure(state="disabled")
        box.pack(expand=True, fill="both", padx=20, pady=20)


    def load_template_placeholders(self):
        template_content = self.template_manager.get_template(self.current_template)
        placeholders = self.template_manager.extract_placeholders(template_content)

        # SALVAR VALORES EXISTENTES (Entry ou Textbox)
        old_values = {}
        for k, v in self.entries.items():
            if isinstance(v, ctk.CTkTextbox):
                old_values[k] = v.get("1.0", "end-1c")
            else:
                old_values[k] = v.get()

        # Filtra placeholders automáticos (handlers do PlaceholderEngine)
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
        # Também inclui campos usados em condicionais
        import re
        cond_fields = set()
        for match in re.findall(r"\$([a-zA-Z0-9 _\-çÇáéíóúãõâêîôûÀ-ÿ\[\]%:/]+)\?", template_content):
            cond_fields.add(match.strip())

        all_fields = set(placeholders) | cond_fields

        self.dynamic_fields = [
            ph for ph in all_fields
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
                if isinstance(entry, ctk.CTkTextbox):
                    entry.delete("1.0", "end")
                    entry.insert("1.0", valor_antigo)
                else:
                    entry.delete(0, "end")
                    entry.insert(0, valor_antigo)
        # Se não houver valor antigo, deixa vazio para mostrar o placeholder




    def open_template_editor(self):
        def get_fields():
            return {
                "fixed": self.fixed_fields,
                "dynamic": sorted(self.dynamic_fields)
            }

        TemplateEditor(self, self.template_manager, get_fields, current_template=self.current_template)
        
    def open_quick_mode(self):
        from quick_template_popup import QuickTemplatePopup
        QuickTemplatePopup(self, self.template_manager)

    def handle_daily_password(self):
        if senha := self.password_manager.get_today_password():
            try:
                pyperclip.copy(senha)
                self.show_snackbar("Senha diária copiada!")
            except Exception:
                self.show_snackbar("Falha ao copiar senha para a área de transferência!", toast_type="error")
        else:
            dialog = CTkInputDialog(title="Senha Diária", text="Informe a senha de hoje:")
            if senha_input := dialog.get_input():
                self.password_manager.set_today_password(senha_input)
                pyperclip.copy(senha_input)
                self.show_snackbar("Senha diária salva e copiada!")

    def on_template_change(self, selected_display_name):
        real_name = self.template_manager.meta.get_real_name(selected_display_name)

        # Sempre recarrega lista atualizada
        self.template_manager.load_templates()
        self.template_selector.configure(values=self.template_manager.get_display_names())

        self.current_template = real_name
        self.current_template_display.set(self.template_manager.meta.get_display_name(real_name))
        self.load_template_placeholders()

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
        self._safe_after(delay, lambda: self.animate_resize_to(target_height, step, delay, on_complete))

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

    def fetch_nocodb_templates(self, api_url, base_name, table_name, token):
        """
        Busca todos os templates do NocoDB via API REST, trazendo todos os registros.
        """
        import requests
        headers = {
            "xc-token": token,
            "accept": "application/json"
        }
        # Busca todos os registros (até 1000) usando pageSize
        url = f"{api_url}/api/v1/db/data/v1/{base_name}/{table_name}?pageSize=1000"
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            # Mostra todos os registros para depuração
            if data.get("list"):
                print(f"[NocoDB] {len(data['list'])} registros retornados.")
            else:
                print("[NocoDB] Nenhum registro encontrado.")
            return data.get("list", [])
        except Exception as e:
            # Se a resposta da API tiver texto, printa no console
            if hasattr(e, 'response') and e.response is not None:
                try:
                    print("[NocoDB API ERROR]", e.response.text)
                except Exception:
                    print("[NocoDB API ERROR] (sem texto de resposta)")
            else:
                print("[NocoDB API ERROR]", str(e))
            self.show_snackbar("Erro ao buscar templates. Veja o log para detalhes.", toast_type="error")
            return []

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
            pasta_escolhida = [None]
            def abrir_nova_pasta():
                win_nova = ctk.CTkToplevel(self)
                win_nova.title("Nova Pasta")
                win_nova.geometry("320x140")
                win_nova.grab_set()
                ctk.CTkLabel(win_nova, text="Nome da nova pasta:", font=ctk.CTkFont(size=13)).pack(pady=(18, 8))
                entry = ctk.CTkEntry(win_nova)
                entry.pack(pady=(0, 8))
                entry.focus()
                info_label = ctk.CTkLabel(win_nova, text="", text_color="#A94444", font=ctk.CTkFont(size=12))
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
                            info_label.configure(text="Esta pasta já existe! Retornando para seleção.")
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
                ctk.CTkButton(btn_frame, text="Confirmar", command=confirmar).pack(side="left", padx=10)
                ctk.CTkButton(btn_frame, text="Cancelar", command=cancelar).pack(side="left", padx=10)
                win_nova.wait_window()
            def escolher():
                while True:
                    win = ctk.CTkToplevel(self)
                    win.title("Escolher Pasta")
                    win.geometry("350x200")
                    win.grab_set()
                    win.grid_columnconfigure(0, weight=1)
                    win.grid_columnconfigure(1, weight=0)
                    ctk.CTkLabel(
                        win,
                        text="Escolha a pasta para salvar o template:",
                        font=ctk.CTkFont(size=13)
                    ).grid(row=0, column=0, columnspan=2, pady=(18, 8), padx=10, sticky="w")
                    var = ctk.StringVar(value=pasta_atual or categorias[0])
                    opt = ctk.CTkOptionMenu(win, values=categorias, variable=var, width=220)
                    opt.grid(row=1, column=0, padx=(20, 0), pady=(0, 12), sticky="ew")
                    def nova_pasta():
                        win.destroy()
                        abrir_nova_pasta()
                    btn_add = ctk.CTkButton(win, text="+", width=30, command=nova_pasta)
                    btn_add.grid(row=1, column=1, padx=(8, 20), pady=(0, 12), sticky="e")
                    btn_frame = ctk.CTkFrame(win)
                    btn_frame.grid(row=2, column=0, columnspan=2, pady=(0, 0))
                    def confirmar():
                        pasta_escolhida[0] = var.get()
                        win.destroy()
                    ctk.CTkButton(btn_frame, text="Confirmar", command=confirmar).pack(side="left", padx=10)
                    win.wait_window()
                    # Se o usuário tentou criar uma nova pasta que já existe, retorna para cá com pasta_escolhida[0] já preenchida
                    if pasta_escolhida[0] in categorias:
                        # Seleciona a pasta já existente e retorna
                        return pasta_escolhida[0]
                    # Se foi criada uma nova pasta válida, retorna
                    if pasta_escolhida[0] is not None:
                        return pasta_escolhida[0]
                    # Se cancelou, retorna None
                    return None
            return escolher()

        # Extrai os campos conforme a tabela NocoDB
        nome = template.get("Template Name")
        conteudo = template.get("Template Description")
        nocodb_id = template.get("Id") or template.get("id") or template.get("ID")
        nocodb_updated = template.get("UpdatedAt") or template.get("updatedAt") or template.get("updated_at")
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
        duplicate_names = [
            local_name for local_name, meta in self.template_manager.meta.meta.items()
            if meta.get("nocodb_id") == str(nocodb_id)
        ]
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
                n for n in same_content_names
                if self.template_manager.meta.meta.get(n, {}).get("nocodb_id")
            ]
            if nocodb_templates:
                import customtkinter as ctk
                unify_win = ctk.CTkToplevel(self)
                unify_win.title("Unificar Templates Iguais")
                unify_win.geometry("600x260")
                unify_win.grab_set()
                ctk.CTkLabel(
                    unify_win,
                    text="Foram encontrados dois ou mais templates com o mesmo conteúdo.",
                    font=ctk.CTkFont(size=14, weight="bold")
                ).pack(pady=(18, 8))
                ctk.CTkLabel(
                    unify_win,
                    text="Deseja unificar todos em apenas um, mantendo a versão do NocoDB?",
                    font=ctk.CTkFont(size=13)
                ).pack(pady=(0, 10))
                ctk.CTkLabel(
                    unify_win,
                    text="Templates encontrados:",
                    font=ctk.CTkFont(size=12, slant="italic")
                ).pack(pady=(0, 2))
                for n in same_content_names:
                    id_str = self.template_manager.meta.meta.get(n, {}).get("nocodb_id", "")
                    id_str = f" (ID NocoDB: {id_str})" if id_str else ""
                    ctk.CTkLabel(
                        unify_win,
                        text=f"- {n}{id_str}",
                        font=ctk.CTkFont(size=12)
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
                ctk.CTkButton(btn_frame, text="Unificar (manter NocoDB)", fg_color="#388E3C", command=confirmar, width=160).pack(side="left", padx=10)
                ctk.CTkButton(btn_frame, text="Cancelar", fg_color="#A94444", command=cancelar, width=120).pack(side="left", padx=10)
                unify_win.wait_window()
                if result["resp"]:
                    # Mantém apenas o template do NocoDB (ou o primeiro com nocodb_id)
                    keep_name = None
                    for n in same_content_names:
                        if self.template_manager.meta.meta.get(n, {}).get("nocodb_id") == str(nocodb_id):
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
                        self.template_manager.save_template(keep_name, full_name, conteudo)
                        # Atualiza meta para garantir nocodb_id
                        self.template_manager.meta._ensure_entry(full_name)
                        self.template_manager.meta.meta[full_name]["nocodb_id"] = str(nocodb_id)
                        self.template_manager.meta._save()
                        self.template_manager.meta.remove_meta(keep_name)
                        self.show_snackbar(f"Template movido para '{full_name}'!", toast_type="success", duration=2500)
                    else:
                        self.show_snackbar(f"Templates unificados como '{full_name}'!", toast_type="success", duration=2500)
                    self.template_manager.load_templates()
                    self.template_selector.configure(values=self.template_manager.get_display_names())
                    return
                # Se cancelar, não faz nada: NÃO remove nenhum template, segue para a lógica de comparação de ID/conteúdo normalmente

        # Se houver duplicados, verifica se o conteúdo é igual
        local_contents = []
        for name in duplicate_names:
            local_path = self.template_manager._template_path(name)
            if os.path.exists(local_path):
                local_contents.append((name, self.template_manager.get_template(name)))
            else:
                local_contents.append((name, ""))

        # Se todos os conteúdos são iguais ao do NocoDB, unifica para o nome do NocoDB
        all_equal = all(content == conteudo for _, content in local_contents)
        if duplicate_names and all_equal:
            # Remove todos, mantém só o nome do NocoDB (na pasta escolhida)
            for name, _ in local_contents:
                if name != f"Geral / {nome}" and name != nome:
                    self.template_manager.delete_template(name)
            # Pergunta a pasta
            pasta = prompt_pasta(categorias)
            if pasta is None:
                self.show_snackbar("Importação cancelada.", toast_type="info")
                return
            full_name = f"{pasta} / {nome}" if pasta != "Geral" else nome
            self.template_manager.add_template(full_name, conteudo)
            self.template_manager.meta._ensure_entry(full_name)
            self.template_manager.meta.meta[full_name]["nocodb_id"] = str(nocodb_id)
            self.template_manager.meta._save()
            # Remove duplicados do meta.json
            for name in list(self.template_manager.meta.meta.keys()):
                if name != full_name and self.template_manager.meta.meta[name].get("nocodb_id") == str(nocodb_id):
                    self.template_manager.meta.remove_meta(name)
            if any(self.template_manager._split_name(name)[0] != pasta for name in duplicate_names):
                self.show_snackbar(f"Template movido para '{full_name}'!", toast_type="success", duration=2500)
            else:
                self.show_snackbar(f"Templates unificados como '{full_name}'!", toast_type="success", duration=2500)
            self.template_manager.load_templates()
            self.template_selector.configure(values=self.template_manager.get_display_names())
            return

        elif duplicate_names and not all_equal:
            # Se há conteúdos diferentes, mostrar tela de comparação para o usuário escolher qual manter
            # Mostra janela de comparação múltipla
            import customtkinter as ctk
            compare_win = ctk.CTkToplevel(self)
            compare_win.title("Comparar Templates Duplicados")
            compare_win.geometry("1000x600")
            compare_win.grab_set()

            ctk.CTkLabel(compare_win, text="Template do NocoDB", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, padx=10, pady=10)
            for idx, (name, _) in enumerate(local_contents):
                ctk.CTkLabel(compare_win, text=f"Template Local: {name}", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=idx+1, padx=10, pady=10)

            # NocoDB content
            nocodb_box = ctk.CTkTextbox(compare_win, wrap="word", width=400, height=350)
            nocodb_box.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
            nocodb_box.insert("1.0", conteudo)
            nocodb_box.configure(state="disabled")

            # Local contents
            local_boxes = []
            for idx, (name, content) in enumerate(local_contents):
                local_box = ctk.CTkTextbox(compare_win, wrap="word", width=400, height=350)
                local_box.grid(row=1, column=idx+1, padx=10, pady=10, sticky="nsew")
                local_box.insert("1.0", content)
                local_box.configure(state="disabled")
                local_boxes.append((name, local_box))

            ctk.CTkLabel(compare_win, text="Escolha qual template deseja manter:", font=ctk.CTkFont(size=13)).grid(row=2, column=0, columnspan=len(local_contents)+1, pady=(0, 10))

            btn_frame = ctk.CTkFrame(compare_win)
            btn_frame.grid(row=3, column=0, columnspan=len(local_contents)+1, pady=10)

            def manter_nocodb():
                # Pergunta a pasta
                pasta = prompt_pasta(categorias)
                if pasta is None:
                    self.show_snackbar("Importação cancelada.", toast_type="info")
                    compare_win.destroy()
                    return
                full_name = f"{pasta} / {nome}" if pasta != "Geral" else nome
                self.template_manager.add_template(full_name, conteudo)
                self.template_manager.meta._ensure_entry(full_name)
                self.template_manager.meta.meta[full_name]["nocodb_id"] = str(nocodb_id)
                self.template_manager.meta._save()
                # Remove todos os outros duplicados
                for name, _ in local_contents:
                    if name != full_name:
                        self.template_manager.delete_template(name)
                if old_category != pasta:
                    self.show_snackbar(f"Template movido para '{full_name}'!", toast_type="success", duration=2500)
                else:
                    self.show_snackbar(f"Template do NocoDB mantido como '{full_name}'!", toast_type="success", duration=2500)
                self.template_manager.load_templates()
                self.template_selector.configure(values=self.template_manager.get_display_names())
                compare_win.destroy()

            def manter_local(idx):
                name, _ = local_contents[idx]
                # Remove todos os outros duplicados e mantém só esse
                for n, _ in local_contents:
                    if n != name:
                        self.template_manager.delete_template(n)
                # Atualiza meta para garantir unicidade
                self.template_manager.meta._ensure_entry(name)
                self.template_manager.meta.meta[name]["nocodb_id"] = str(nocodb_id)
                self.template_manager.meta._save()
                if old_category != self.template_manager._split_name(name)[0]:
                    self.show_snackbar(f"Template movido para '{name}'!", toast_type="success", duration=2500)
                else:
                    self.show_snackbar(f"Template local '{name}' mantido!", toast_type="success", duration=2500)
                self.template_manager.load_templates()
                self.template_selector.configure(values=self.template_manager.get_display_names())
                compare_win.destroy()

            ctk.CTkButton(btn_frame, text="Manter do NocoDB", fg_color="#388E3C", command=manter_nocodb).pack(side="left", padx=10)
            for idx, (name, _) in enumerate(local_contents):
                ctk.CTkButton(btn_frame, text=f"Manter Local: {name}", fg_color="#A94444", command=lambda i=idx: manter_local(i)).pack(side="left", padx=10)
            compare_win.wait_window()
            return

        def prompt_pasta(categorias, pasta_atual=None):
            pasta_escolhida = [None]
            def abrir_nova_pasta():
                win_nova = ctk.CTkToplevel(self)
                win_nova.title("Nova Pasta")
                win_nova.geometry("320x140")
                win_nova.grab_set()
                ctk.CTkLabel(win_nova, text="Nome da nova pasta:", font=ctk.CTkFont(size=13)).pack(pady=(18, 8))
                entry = ctk.CTkEntry(win_nova)
                entry.pack(pady=(0, 8))
                entry.focus()
                info_label = ctk.CTkLabel(win_nova, text="", text_color="#A94444", font=ctk.CTkFont(size=12))
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
                            info_label.configure(text="Esta pasta já existe! Retornando para seleção.")
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
                ctk.CTkButton(btn_frame, text="Confirmar", command=confirmar).pack(side="left", padx=10)
                ctk.CTkButton(btn_frame, text="Cancelar", command=cancelar).pack(side="left", padx=10)
                win_nova.wait_window()
            def show_pasta_selector(parent, categorias, pasta_atual, on_nova_pasta):
                win = ctk.CTkToplevel(parent)
                win.title("Escolher Pasta")
                win.geometry("350x200")
                win.grab_set()
                win.grid_columnconfigure(0, weight=1)
                win.grid_columnconfigure(1, weight=0)
                ctk.CTkLabel(
                    win,
                    text="Escolha a pasta para salvar o template:",
                    font=ctk.CTkFont(size=13)
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
                ctk.CTkButton(btn_frame, text="Confirmar", command=confirmar).pack(side="left", padx=10)
                win.wait_window()
                return result["pasta"]

            def escolher():
                while True:
                    def abrir_nova_pasta():
                        win_nova = ctk.CTkToplevel(self)
                        win_nova.title("Nova Pasta")
                        win_nova.geometry("320x140")
                        win_nova.grab_set()
                        ctk.CTkLabel(win_nova, text="Nome da nova pasta:", font=ctk.CTkFont(size=13)).pack(pady=(18, 8))
                        entry = ctk.CTkEntry(win_nova)
                        entry.pack(pady=(0, 8))
                        entry.focus()
                        info_label = ctk.CTkLabel(win_nova, text="", text_color="#A94444", font=ctk.CTkFont(size=12))
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
                                    info_label.configure(text="Esta pasta já existe! Retornando para seleção.")
                                    win_nova.after(1200, win_nova.destroy)
                                    pasta_escolhida[0] = cat
                                    return
                            pasta_escolhida[0] = nome_pasta
                            win_nova.destroy()
                        def cancelar():
                            win_nova.destroy()
                        btn_frame = ctk.CTkFrame(win_nova)
                        btn_frame.pack()
                        ctk.CTkButton(btn_frame, text="Confirmar", command=confirmar).pack(side="left", padx=10)
                        ctk.CTkButton(btn_frame, text="Cancelar", command=cancelar).pack(side="left", padx=10)
                        win_nova.wait_window()

                    pasta_escolhida = [None]
                    def on_nova_pasta():
                        abrir_nova_pasta()
                    pasta = show_pasta_selector(self, categorias, pasta_atual, on_nova_pasta)
                    if pasta is not None:
                        return pasta
                    return None
            return escolher()

        if existing_name:
            # Verifica se o arquivo do template local existe e não está vazio
            local_path = self.template_manager._template_path(existing_name)
            local_exists = os.path.exists(local_path)
            local_content = self.template_manager.get_template(existing_name) if local_exists else ""
            old_category, old_nome = self.template_manager._split_name(existing_name)
            if (not local_exists) or (not local_content.strip()):
                # Se não existe ou está vazio, importa normalmente (sem comparação)
                full_name = f"{old_category} / {nome}" if old_category != "Geral" else nome
                self.template_manager.add_template(full_name, conteudo)
                if nocodb_id:
                    self.template_manager.meta._ensure_entry(full_name)
                    self.template_manager.meta.meta[full_name]["nocodb_id"] = str(nocodb_id)
                    self.template_manager.meta._save()
                # Remove entradas duplicadas de meta.json (com o mesmo nocodb_id)
                for name in list(self.template_manager.meta.meta.keys()):
                    if name != full_name and self.template_manager.meta.meta[name].get("nocodb_id") == str(nocodb_id):
                        self.template_manager.meta.remove_meta(name)
                if old_category != pasta:
                    self.show_snackbar(f"Template movido para '{full_name}'!", toast_type="success", duration=2500)
                else:
                    self.show_snackbar(f"Template '{full_name}' importado!", toast_type="success", duration=2500)
                self.template_manager.load_templates()
                self.template_selector.configure(values=self.template_manager.get_display_names())
                return
            if local_content != conteudo:
                # Mostra janela de comparação lado a lado (NocoDB à esquerda, Local à direita)
                compare_win = ctk.CTkToplevel(self)
                compare_win.title("Comparar Templates")
                compare_win.geometry("900x500")
                compare_win.grab_set()

                ctk.CTkLabel(compare_win, text="Template do NocoDB", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, padx=10, pady=10)
                ctk.CTkLabel(compare_win, text="Template Local", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=1, padx=10, pady=10)

                nocodb_box = ctk.CTkTextbox(compare_win, wrap="word", width=400, height=350)
                nocodb_box.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
                nocodb_box.insert("1.0", conteudo)
                nocodb_box.configure(state="disabled")

                local_box = ctk.CTkTextbox(compare_win, wrap="word", width=400, height=350)
                local_box.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
                local_box.insert("1.0", local_content)
                local_box.configure(state="disabled")

                # Datas de atualização
                import datetime
                try:
                    nocodb_dt = datetime.datetime.fromisoformat(nocodb_updated.replace("Z", "+00:00")) if nocodb_updated else None
                    if nocodb_dt and nocodb_dt.tzinfo is not None:
                        nocodb_dt = nocodb_dt.replace(tzinfo=None)
                except Exception:
                    nocodb_dt = None
                try:
                    local_mtime = os.path.getmtime(local_path)
                    local_dt = datetime.datetime.fromtimestamp(local_mtime)
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
                        info_text = "Ambos os templates têm a mesma data de modificação."
                else:
                    info_text = "Datas de atualização indisponíveis."

                ctk.CTkLabel(compare_win, text=info_text, font=ctk.CTkFont(size=12, slant="italic")).grid(row=2, column=0, columnspan=2, pady=(0, 10))

                btn_frame = ctk.CTkFrame(compare_win)
                btn_frame.grid(row=3, column=0, columnspan=2, pady=10)

                def usar_nocodb():
                    # Pergunta se deseja atualizar o título do template usando customtkinter
                    if old_nome != nome:
                        # Janela customtkinter para atualizar título
                        update_win = ctk.CTkToplevel(self)
                        update_win.title("Atualizar Título")
                        update_win.geometry("420x260")
                        update_win.grab_set()
                        ctk.CTkLabel(
                            update_win,
                            text="O nome do template local é:",
                            font=ctk.CTkFont(size=13)
                        ).pack(pady=(18, 2))
                        ctk.CTkLabel(
                            update_win,
                            text=f"'{old_nome}'",
                            font=ctk.CTkFont(size=15, weight="bold"),
                            text_color="#7E57C2"
                        ).pack(pady=(0, 8))
                        ctk.CTkLabel(
                            update_win,
                            text="O nome recebido do NocoDB é:",
                            font=ctk.CTkFont(size=13)
                        ).pack(pady=(0, 2))
                        ctk.CTkLabel(
                            update_win,
                            text=f"'{nome}'",
                            font=ctk.CTkFont(size=15, weight="bold"),
                            text_color="#388E3C"
                        ).pack(pady=(0, 10))
                        ctk.CTkLabel(
                            update_win,
                            text="Deseja atualizar o título do template para o nome do NocoDB?",
                            font=ctk.CTkFont(size=13)
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
                        ctk.CTkButton(btn_frame, text="Sim", fg_color="#388E3C", command=confirmar, width=80).pack(side="left", padx=10)
                        ctk.CTkButton(btn_frame, text="Não", fg_color="#A94444", command=cancelar, width=80).pack(side="left", padx=10)
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
                            move_win = ctk.CTkToplevel(self)
                            move_win.title("Mover de Pasta?")
                            move_win.geometry("420x170")
                            move_win.grab_set()
                            ctk.CTkLabel(
                                move_win,
                                text=f"O template está atualmente na pasta '{old_category}'.\nDeseja mover para outra pasta?",
                                font=ctk.CTkFont(size=13)
                            ).pack(pady=(18, 10))
                            btn_frame2 = ctk.CTkFrame(move_win)
                            btn_frame2.pack(pady=10)
                            ctk.CTkButton(btn_frame2, text="Sim", fg_color="#388E3C", command=mover_pasta, width=80).pack(side="left", padx=10)
                            ctk.CTkButton(btn_frame2, text="Não", fg_color="#A94444", command=manter_pasta, width=80).pack(side="left", padx=10)
                            move_win.wait_window()
                            mover = move_result["resp"]
                            if mover:
                                nova_pasta = prompt_pasta(categorias, pasta_atual=old_category)
                                if not nova_pasta:
                                    self.show_snackbar("Importação cancelada.", toast_type="info")
                                    compare_win.destroy()
                                    return
                                full_new_name = f"{nova_pasta} / {nome}" if nova_pasta != "Geral" else nome
                            else:
                                full_new_name = f"{old_category} / {nome}" if old_category != "Geral" else nome
                            # Salva com novo nome (na pasta escolhida)
                            self.template_manager.save_template(existing_name, full_new_name, conteudo)
                            old_meta = self.template_manager.meta.meta.get(existing_name, {}).copy()
                            self.template_manager.meta.meta[full_new_name] = old_meta
                            self.template_manager.meta._save()
                            if existing_name != full_new_name:
                                self.template_manager.meta.remove_meta(existing_name)
                            self.show_snackbar(f"Título atualizado para '{full_new_name}' e template sincronizado!", toast_type="success")
                        else:
                            # Só atualiza o conteúdo mantendo o nome antigo e pasta
                            self.template_manager.save_template(existing_name, existing_name, conteudo)
                            self.template_manager.meta._ensure_entry(existing_name)
                            self.template_manager.meta.meta[existing_name]["nocodb_id"] = str(nocodb_id)
                            self.template_manager.meta._save()
                            self.show_snackbar(f"Template '{existing_name}' atualizado pelo NocoDB!", toast_type="success")
                    else:
                        # Só atualiza o conteúdo mantendo o nome e pasta
                        self.template_manager.save_template(existing_name, existing_name, conteudo)
                        self.template_manager.meta._ensure_entry(existing_name)
                        self.template_manager.meta.meta[existing_name]["nocodb_id"] = str(nocodb_id)
                        self.template_manager.meta._save()
                        self.show_snackbar(f"Template '{existing_name}' atualizado pelo NocoDB!", toast_type="success")
                    compare_win.destroy()
                    self.template_manager.load_templates()
                    self.template_selector.configure(values=self.template_manager.get_display_names())

                def manter_local():
                    self.show_snackbar("Template local mantido!", toast_type="info")
                    compare_win.destroy()

                ctk.CTkButton(btn_frame, text="Usar do NocoDB", fg_color="#A94444", command=usar_nocodb).pack(side="left", padx=20)
                ctk.CTkButton(btn_frame, text="Manter Local", fg_color="#388E3C", command=manter_local).pack(side="left", padx=20)
                compare_win.wait_window()
                return
            else:
                # Se o nome do NocoDB for diferente do local, perguntar se deseja atualizar o nome
                if old_nome != nome:
                    # Janela customtkinter para atualizar título
                    update_win = ctk.CTkToplevel(self)
                    update_win.title("Atualizar Título")
                    update_win.geometry("420x260")
                    update_win.grab_set()
                    ctk.CTkLabel(
                        update_win,
                        text="O nome do template local é:",
                        font=ctk.CTkFont(size=13)
                    ).pack(pady=(18, 2))
                    ctk.CTkLabel(
                        update_win,
                        text=f"'{old_nome}'",
                        font=ctk.CTkFont(size=15, weight="bold"),
                        text_color="#7E57C2"
                    ).pack(pady=(0, 8))
                    ctk.CTkLabel(
                        update_win,
                        text="O nome recebido do NocoDB é:",
                        font=ctk.CTkFont(size=13)
                    ).pack(pady=(0, 2))
                    ctk.CTkLabel(
                        update_win,
                        text=f"'{nome}'",
                        font=ctk.CTkFont(size=15, weight="bold"),
                        text_color="#388E3C"
                    ).pack(pady=(0, 10))
                    ctk.CTkLabel(
                        update_win,
                        text="Deseja atualizar o título do template para o nome do NocoDB?",
                        font=ctk.CTkFont(size=13)
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
                    ctk.CTkButton(btn_frame, text="Sim", fg_color="#388E3C", command=confirmar, width=80).pack(side="left", padx=10)
                    ctk.CTkButton(btn_frame, text="Não", fg_color="#A94444", command=cancelar, width=80).pack(side="left", padx=10)
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
                        move_win = ctk.CTkToplevel(self)
                        move_win.title("Mover de Pasta?")
                        move_win.geometry("420x170")
                        move_win.grab_set()
                        ctk.CTkLabel(
                            move_win,
                            text=f"O template está atualmente na pasta '{old_category}'.\nDeseja mover para outra pasta?",
                            font=ctk.CTkFont(size=13)
                        ).pack(pady=(18, 10))
                        btn_frame2 = ctk.CTkFrame(move_win)
                        btn_frame2.pack(pady=10)
                        ctk.CTkButton(btn_frame2, text="Sim", fg_color="#388E3C", command=mover_pasta, width=80).pack(side="left", padx=10)
                        ctk.CTkButton(btn_frame2, text="Não", fg_color="#A94444", command=manter_pasta, width=80).pack(side="left", padx=10)
                        move_win.wait_window()
                        mover = move_result["resp"]
                        if mover:
                            nova_pasta = prompt_pasta(categorias, pasta_atual=old_category)
                            if not nova_pasta:
                                self.show_snackbar("Importação cancelada.", toast_type="info")
                                return
                            full_new_name = f"{nova_pasta} / {nome}" if nova_pasta != "Geral" else nome
                        else:
                            full_new_name = f"{old_category} / {nome}" if old_category != "Geral" else nome
                        self.template_manager.save_template(existing_name, full_new_name, local_content)
                        old_meta = self.template_manager.meta.meta.get(existing_name, {}).copy()
                        self.template_manager.meta.meta[full_new_name] = old_meta
                        self.template_manager.meta._save()
                        if existing_name != full_new_name:
                            self.template_manager.meta.remove_meta(existing_name)
                        self.show_snackbar(f"Título atualizado para '{full_new_name}'!", toast_type="success")
                        self.template_manager.load_templates()
                        self.template_selector.configure(values=self.template_manager.get_display_names())
                    else:
                        self.show_snackbar("Template já existe e está atualizado!", toast_type="info")
                else:
                    self.show_snackbar("Template já existe e está atualizado!", toast_type="info")
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
                if name != full_name and self.template_manager.meta.meta[name].get("nocodb_id") == str(nocodb_id):
                    self.template_manager.meta.remove_meta(name)
        self.show_snackbar(f"Template '{full_name}' importado!", toast_type="success", duration=2500)
        self.template_manager.load_templates()
        self.template_selector.configure(values=self.template_manager.get_display_names())

    def show_nocodb_templates(self):
        import customtkinter as ctk

        # Cria a janela principal do diálogo
        nocodb_templates_dialog = ctk.CTkToplevel(self)
        nocodb_templates_dialog.title("Templates Compartilhados")
        nocodb_templates_dialog.geometry("700x500")
        nocodb_templates_dialog.grab_set()

        # Frame principal
        main_frame = ctk.CTkFrame(nocodb_templates_dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # OptionMenu para seleção
        nocodb_templates_list = ctk.CTkOptionMenu(main_frame, width=80)
        nocodb_templates_list.grid(row=0, column=0, sticky="ew", padx=(0, 20), pady=(0, 10))

        # Card fixo (não expansível)
        card_frame = ctk.CTkFrame(main_frame, fg_color="#222", corner_radius=10)
        card_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 20), pady=(0, 10))
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)

        # Nome do template (expansível)
        label_nome = ctk.CTkTextbox(card_frame, height=1, font=ctk.CTkFont(size=16, weight="bold"), wrap="word")
        label_nome.pack(fill="x", padx=16, pady=(16, 2))
        label_nome.configure(state="disabled", border_width=0, fg_color="#222", text_color="#fff")

        # Descrição (sempre visível, com quebras de linha, expansível)
        desc_box = ctk.CTkTextbox(card_frame, wrap="word", height=1, font=ctk.CTkFont(size=13))
        desc_box.pack(fill="both", expand=True, padx=16, pady=(0, 2))
        desc_box.configure(state="disabled", border_width=0, fg_color="#222", text_color="#fff")

        # Linha separadora para detalhes extras
        sep = ctk.CTkFrame(card_frame, height=2, fg_color="#444")
        sep.pack(fill="x", padx=16, pady=(8, 4))

        # Rodapé do card (autor, criado, atualizado) em uma linha, todos como labels
        footer_frame = ctk.CTkFrame(card_frame, fg_color="#222")
        footer_frame.pack(fill="x", side="bottom", padx=8, pady=(0, 12))

        label_teams = ctk.CTkLabel(footer_frame, text="", font=ctk.CTkFont(size=12, slant="italic"), anchor="w", justify="left")
        label_teams.pack(side="left", fill="x", expand=True, padx=(0, 8), pady=0)

        label_created = ctk.CTkLabel(footer_frame, text="", font=ctk.CTkFont(size=11), anchor="w", justify="left")
        label_created.pack(side="left", fill="x", expand=True, padx=(0, 8), pady=0)

        label_updated = ctk.CTkLabel(footer_frame, text="", font=ctk.CTkFont(size=11), anchor="w", justify="left")
        label_updated.pack(side="left", fill="x", expand=True, padx=(0, 0), pady=0)

        # Botão de importar
        btn_importar = ctk.CTkButton(main_frame, text="Importar", fg_color="#388E3C")
        btn_importar.grid(row=2, column=0, sticky="ew", pady=(10, 0))

        # --- Lógica de preenchimento e seleção ---
        api_url = "https://app.nocodb.com"
        base_name = "p02k6lvq2via5sv"
        table_name = "Templates"
        token = 'UifsYUdNbfJFWVz3t7oOIPo2Idd51ykk2I-9FnzK'

        templates = self.fetch_nocodb_templates(api_url, base_name, table_name, token)
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
            updated = template.get('UpdatedAt', '')
            if not updated or str(updated).strip() == "" or updated == template.get('CreatedAt', ''):
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


    def show_snackbar(self, message="Copiado com sucesso!", duration=1500, toast_type="success"):
        styles = {
            "success": {"fg": "#388E3C", "icon": "✔"},
            "error": {"fg": "#D32F2F", "icon": "✖"},
            "warning": {"fg": "#D4A326", "icon": "⚠"},
            "info": {"fg": "#1976D2", "icon": "ℹ"},
            "default": {"fg": "#AE00FF", "icon": "•"},
        }

        style = styles.get(toast_type, styles["default"])
        text = f"{style['icon']} {message}"

        # Cria a janela flutuante
        snackbar = ctk.CTkToplevel(self)
        snackbar.overrideredirect(True)
        snackbar.attributes("-topmost", True)
        snackbar.configure(fg_color=style["fg"])

        label = ctk.CTkLabel(snackbar, text=text, text_color="white", font=ctk.CTkFont(size=12), padx=15, pady=8)
        label.pack()

        self.update_idletasks()
        width = snackbar.winfo_reqwidth()
        height = snackbar.winfo_reqheight()
        x = self.winfo_x() + int((self.winfo_width() - width) / 2)
        y = self.winfo_y() + self.winfo_height() - height - 20

        snackbar.geometry(f"{width}x{height}+{x}+{y}")
        snackbar.attributes("-alpha", 0)

        # Fade in
        def fade_in(opacity=0.0):
            if opacity >= 1.0:
                snackbar.attributes("-alpha", 1.0)
            else:
                snackbar.attributes("-alpha", opacity)
                self._safe_after(20, lambda: fade_in(opacity + 0.1))

        fade_in()

        # Desaparecer com fade out
        def fade_out(opacity=1.0):
            if opacity <= 0:
                snackbar.destroy()
            else:
                snackbar.attributes("-alpha", opacity)
                self._safe_after(30, lambda: fade_out(opacity - 0.1))

        self._safe_after(duration, lambda: fade_out())

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
        return re.sub(r"\$([a-zA-Z0-9 _\-çÇáéíóúãõâêîôûÀ-ÿ\[\]%:/\?\|]+)\$", cond_replacer, template)


    # Mantém uma lista global de tooltips abertos para garantir que todos sejam fechados ao passar o mouse novamente
    _all_tooltips = []

    def create_tooltip(self, widget, text, fg_color="#222", text_color="#fff", immediate_hide=True):
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
                tooltip["window"] = tw = ctk.CTkToplevel(widget)
                tw.overrideredirect(True)
                tw.attributes("-topmost", True)
                label = ctk.CTkLabel(
                    tw,
                    text=text,
                    font=ctk.CTkFont(size=11),
                    text_color=text_color,
                    fg_color=fg_color,
                    padx=7, pady=3
                )
                label.pack()
                widget.update_idletasks()
                x = widget.winfo_rootx() + widget.winfo_width() + 7
                y = widget.winfo_rooty() - 3
                tw.geometry(f"+{x}+{y}")

                # Garante que o tooltip seja destruído se o widget principal for destruído
                def on_widget_destroy(event=None):
                    hide_tooltip()
                widget.bind("<Destroy>", on_widget_destroy, add="+")
                tw.bind("<Destroy>", on_widget_destroy, add="+")
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
                    entry.configure(border_color=entry.original_border_color)

            pulse()

    def pulse_button_success(self, button, original_color="#7E57C2", success_color="#00C853"):
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
                # Carrega o config existente, se houver
                if os.path.exists("config.json"):
                    with open("config.json", "r", encoding="utf-8") as f:
                        config = json.load(f)
                else:
                    config = {}

                # Atualiza a geometria
                config["geometry"] = geometry_str

                # Salva o arquivo atualizado
                with open("config.json", "w", encoding="utf-8") as f:
                    json.dump(config, f)

            except Exception as e:
                print(f"[ERRO ao salvar config]: {e}")


    def load_window_config(self):
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
                geometry = config.get("geometry")
                if geometry and "x" in geometry:
                    self.geometry(geometry)
        except Exception:
            pass

    def apply_saved_geometry(self):
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
                geometry = config.get("geometry")
                if geometry and "x" in geometry:
                    self.geometry(geometry)
        except Exception:
            pass

    # --- Configuração de campos expansíveis ---
    def load_expandable_fields_config(self):
        import json
        if os.path.exists("config.json"):
            try:
                with open("config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
                return config.get("expandable_fields", ["Procedimento Executado", "Problema Relatado"])
            except Exception:
                return ["Procedimento Executado", "Problema Relatado"]
        return ["Procedimento Executado", "Problema Relatado"]

    def save_expandable_fields_config(self):
        import json
        config = {}
        if os.path.exists("config.json"):
            try:
                with open("config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
            except Exception:
                config = {}
        config["expandable_fields"] = self.expandable_fields
        with open("config.json", "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)

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
        # Quando a janela for fechada, remove a referência
        def on_close_settings():
            win = self._settings_window
            self._settings_window = None
            if win is not None:
                win.destroy()
        self._settings_window.protocol("WM_DELETE_WINDOW", on_close_settings)

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
                if isinstance(entry, ctk.CTkTextbox):
                    entry.delete("1.0", "end")
                    entry.insert("1.0", valor_antigo)
                else:
                    entry.delete(0, "end")
                    entry.insert(0, valor_antigo)
    def load_theme_config(self):
        import json
        if os.path.exists("config.json"):
            try:
                with open("config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
                theme = config.get("theme_name", "green")
                mode = config.get("appearance_mode", "dark")
                return theme, mode
            except Exception:
                return "green", "dark"
        return "green", "dark"

    def save_theme_config(self, theme_name, appearance_mode):
        import json
        config = {}
        if os.path.exists("config.json"):
            try:
                with open("config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
            except Exception:
                config = {}
        config["theme_name"] = theme_name
        config["appearance_mode"] = appearance_mode
        with open("config.json", "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)

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



__all__ = ["TemplateApp", "placeholder_engine"]

