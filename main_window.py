import customtkinter as ctk
import pyperclip
import json
import os
import re
import datetime
import sys
from template_editor import TemplateEditor
from template_manager import TemplateManager
from theme_manager import ThemeManager
from dpm import DailyPasswordManager
from settings_window import SettingsWindow
from customtkinter import CTkInputDialog

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

        # --- Frame inferior para label de crédito e botão de config alinhados ---
        bottom_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        bottom_frame.grid(row=100, column=0, sticky="ew", pady=(8, 2), padx=0)
        bottom_frame.grid_columnconfigure(0, weight=1)
        bottom_frame.grid_columnconfigure(1, weight=0)

        # Label de Créditos do Autor centralizada
        label_autor = ctk.CTkLabel(
            bottom_frame,
            text="By Hamilton Junior",
            font=ctk.CTkFont(size=10, slant="italic"),
            text_color="#888888",
            anchor="center",
            justify="center"
        )
        label_autor.grid(row=0, column=0, sticky="ew", padx=(2, 5))

        # Botão de Configurações
        ctk.CTkButton(
            bottom_frame,
            text="⚙️",
            width=32,
            anchor="e",
            command=self.open_settings
        ).grid(row=0, column=1, sticky="e", padx=(5, 8))

        self.main_frame.grid_rowconfigure(100, weight=0)

        self._init_undo_redo()
        self._bind_undo_redo_shortcuts()

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

    def show_snackbar(self, message="Copiado com sucesso!", duration=1500, toast_type="success"):
        styles = {
            "success": {"fg": "#388E3C", "icon": "✔"},
            "error": {"fg": "#D32F2F", "icon": "✖"},
            "warning": {"fg": "#D4A326", "icon": "⚠"},
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
        import re

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

