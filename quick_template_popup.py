import customtkinter as ctk
from tkinter import StringVar
from tkinter import messagebox
from app import TemplateApp
from theme_manager import ThemeManager
import logging
from logger_config import auto_log_functions

# Get the module logger
logger = logging.getLogger(__name__)


@auto_log_functions
class QuickTemplatePopup(ctk.CTkToplevel):
    def __init__(self, master, manager):
        logger.info("Iniciando Quick Template Popup")
        super().__init__(master)
        self.title("Modo Simples – Linx Fast")
        self._after_ids = set()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.manager = manager
        # Não instancia ThemeManager para alterar modo de aparência!
        self.theme_manager = ThemeManager(theme_name=getattr(master, "theme_name", "green"))
        self.geometry("325x250")
        self.entries = {}
        # Referência ao app principal para funções de UI
        self.app = master

        # Configura logging
        if not isinstance(master, TemplateApp):
            logging.warning(
                "QuickTemplatePopup master não é um TemplateApp, algumas funções de UI podem não funcionar."
            )

        logging.info("Iniciando QuickTemplatePopup...")

        # Corrige o modo de aparência do popup para ser igual ao app principal
        # Não altera o modo de aparência aqui! Apenas no _build_interface, e só se necessário.
        self.template_var = StringVar(value="")
        self._build_interface()

    def _build_interface(self):
        self.grid_columnconfigure(0, weight=0)  # coluna do botão pin
        self.grid_columnconfigure(1, weight=1)  # coluna do dropdown expansível
        self.grid_columnconfigure(2, weight=0)  # coluna do toggle

        # Garante que o tema e o modo de aparência do popup sejam iguais ao do app principal
        try:
            # Aplica o tema de cores (isso é seguro, pois só afeta o tema de cor, não o modo claro/escuro)
            if hasattr(self.master, "theme_name"):
                theme = self.master.theme_name
                import os
                theme_path = os.path.join("themes", f"{theme}.json")
                if theme in ("green", "blue", "dark-blue") or not os.path.exists(theme_path):
                    ctk.set_default_color_theme(theme)
                else:
                    ctk.set_default_color_theme(theme_path)
            # NÃO ALTERA O MODO DE APARÊNCIA GLOBAL!
            # O popup herda o modo de aparência do app principal automaticamente.
        except Exception:
            pass

        # Título
        title = ctk.CTkLabel(self, text="Selecionar Template", font=("Arial", 14, "bold"))
        title.grid(row=0, column=0, columnspan=3, pady=(5, 0), padx=10, sticky="ew")

        # Botão fixo à esquerda
        self.pin_button = ctk.CTkButton(
            self,
            text="📍",
            width=36,
            command=self.toggle_always_on_top
        )
        self.pin_button.grid(row=1, column=0, padx=(10, 5), pady=5, sticky="w")

        # Toggle para limpar campos ao trocar template
        self.clear_on_switch = ctk.BooleanVar(value=False)
        self.clear_toggle = ctk.CTkCheckBox(
            self,
            text="",  # Sem texto, só o checkbox
            variable=self.clear_on_switch,
            width=1
        )
        self.clear_toggle.grid(row=1, column=2, padx=(10, 10), pady=5, sticky="e")

        # Tooltip customizado
        self.tooltip = None
        def show_tooltip(event=None):
            if self.tooltip is not None:
                return
            self.tooltip = ctk.CTkToplevel(self)
            self.tooltip.overrideredirect(True)
            self.tooltip.attributes("-topmost", True)
            label = ctk.CTkLabel(
                self.tooltip,
                text="Limpar valores ao trocar de template?",
                font=ctk.CTkFont(size=11),
                text_color="#fff",
                fg_color="#222",
                padx=8, pady=4
            )
            label.pack()
            # Posição ao lado do ícone
            x = self.clear_toggle.winfo_rootx() + 24
            y = self.clear_toggle.winfo_rooty() - 8
            self.tooltip.geometry(f"+{x}+{y}")

        def hide_tooltip(event=None):
            if self.tooltip is not None:
                self.tooltip.destroy()
                self.tooltip = None

        self.clear_toggle.bind("<Enter>", show_tooltip)
        self.clear_toggle.bind("<Leave>", lambda e: self._safe_after(1, hide_tooltip))
        # Dropdown expansível ocupando o espaço restante
        self.template_dropdown = ctk.CTkOptionMenu(
            self,
            values=self.manager.get_template_names(),
            variable=self.template_var,
            command=self.load_template
        )
        self.template_dropdown.grid(row=1, column=1, padx=(0, 0), pady=5, sticky="ew")

        # Frame para os campos
        self.form_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.form_frame.grid(
            row=2, column=0, columnspan=3, padx=10, pady=(1, 0), sticky="nsew"
        )
        self.form_frame.grid_columnconfigure(0, weight=1)

        # Botão copiar (centralizado)
        self.copy_btn = ctk.CTkButton(
            self.form_frame,
            text="Copiar",
            fg_color="#7E57C2",
            font=ctk.CTkFont(size=13, weight="bold"),
            width=3,
            anchor="center",
            command=self.copy_template,
        )
        self.copy_btn.grid(row=0, column=0, padx=(0, 37), sticky="ew")

        # Botão limpar campos (direita, igual ao main_window)
        self.clear_btn = ctk.CTkButton(
            self.form_frame,
            text="❌",
            fg_color="#A94444",
            hover_color="#FF5252",
            font=ctk.CTkFont(size=13, weight="bold"),
            width=3,
            anchor="center",
            command=self.clear_fields,
        )
        self.clear_btn.grid(row=0, column=0, padx=(37, 0), sticky="e")

    def toggle_always_on_top(self):
        current = self.attributes("-topmost")
        new_state = not current
        self.attributes("-topmost", new_state)
        self.pin_button.configure(fg_color="green" if new_state else self.theme_manager.get_theme_default_color(ctk.CTkButton, "fg_color"))
        self.pin_button.configure(text="📌" if new_state else "📍")
        if hasattr(self.app, "show_snackbar"):
            self.app.show_snackbar(
                "PIN " + ("ativado!" if new_state else "desativado!"),
                toast_type="info",
                parent=self,
            )

    def load_template(self, template_name):
        """Carrega o template selecionado e configura os campos dinamicamente"""
        logger.info(f"Carregando template: {template_name}")
        from main_window import placeholder_engine  # Importa aqui para evitar import circular
        import json
        import os

        logging.info(f"Carregando template '{template_name}' no Modo Simples...")

        # Salva valores antigos dos campos antes de trocar de template
        old_values = {}
        for k, v in self.entries.items():
            if isinstance(v, ctk.CTkTextbox):
                old_values[k] = v.get("1.0", "end-1c")
            else:
                old_values[k] = v.get()

        # Sempre limpa widgets do frame
        for widget in self.form_frame.winfo_children():
            widget.destroy()
        self.entries.clear()

        content = self.manager.get_template(template_name)
        placeholders = self.manager.extract_placeholders(content)

        # Filtra placeholders automáticos
        automatic_placeholders = set(placeholder_engine.handlers.keys())
        def is_automatic(ph):
            if ph in automatic_placeholders:
                return True
            if ph == "Agora":
                return True
            if ph.startswith("Agora[") and ph.endswith("]"):
                return True
            return False

        # --- ORDEM PERSISTENTE DOS CAMPOS DINÂMICOS ---
        # Tenta carregar ordem salva do config.json - INICIANDO
        fixed_fields = [
            "Nome", "Problema Relatado", "CNPJ",
            "Telefone", "Email", "Protocolo", "Procedimento Executado"
        ]
        # Se quiser manter sincronizado com o app principal, pode importar de lá

        # Separa placeholders em fixos e dinâmicos
        fixed_present = [ph for ph in fixed_fields if ph in placeholders]
        dynamic_fields = [ph for ph in placeholders if ph not in fixed_fields and not is_automatic(ph)]

        order = None
        config_path = "config.json"
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                field_orders = config.get("field_orders", {})
                order = field_orders.get(template_name)
            except Exception:
                order = None
        if order:
            # Garante que só mantenha campos realmente presentes no template
            dynamic_ordered = [f for f in order if f in dynamic_fields] + [f for f in dynamic_fields if f not in order]
        else:
            dynamic_ordered = dynamic_fields

        # Campos fixos sempre primeiro, na ordem padrão, depois os dinâmicos na ordem salva
        used_fields = fixed_present + dynamic_ordered

        import re
        def detect_field_type(name):
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
            return field_type, field_label, radio_options

        for i, field in enumerate(used_fields):
            field_type, field_label, radio_options = detect_field_type(field)
            label = ctk.CTkLabel(self.form_frame, text=field_label)
            label.grid(row=i, column=0, sticky="w", pady=(2, 2))

            if field_type == "checkbox":
                var = ctk.BooleanVar(value=False)
                entry = ctk.CTkCheckBox(self.form_frame, text="", variable=var)
                entry.grid(row=i, column=0, sticky="e", padx=(100, 0), pady=(2, 2))
                self.entries[field] = entry
            elif field_type == "switch":
                var = ctk.StringVar(value="Sim")
                entry = ctk.CTkSwitch(self.form_frame, text="", variable=var, onvalue="Sim", offvalue="Não")
                entry.grid(row=i, column=0, sticky="e", padx=(100, 0), pady=(2, 2))
                self.entries[field] = entry
            elif field_type == "radio" and radio_options:
                var = ctk.StringVar(value=radio_options[0])
                radio_frame = ctk.CTkFrame(self.form_frame, fg_color="transparent")
                radio_frame.grid(row=i, column=0, sticky="e", padx=(100, 0), pady=(2, 2))
                for opt in radio_options:
                    btn = ctk.CTkRadioButton(radio_frame, text=opt, variable=var, value=opt)
                    btn.pack(side="left", padx=2)
                self.entries[field] = var
            elif field in ("Procedimento Executado", "Problema Relatado"):
                entry = ctk.CTkEntry(self.form_frame, placeholder_text=f"{field_label}")
                if hasattr(self, "clear_on_switch") and not self.clear_on_switch.get():
                    valor_antigo = old_values.get(field)
                    if valor_antigo not in (None, ""):
                        entry.insert(0, valor_antigo)
                entry.grid(row=i, column=0, sticky="e", padx=(10, 0), pady=(2, 2))
                self.entries[field] = entry

                def to_textbox(event, field_name=field, row_idx=i):
                    current_widget = self.entries[field_name]
                    if isinstance(current_widget, ctk.CTkTextbox):
                        return
                    val = current_widget.get()
                    current_border_color = current_widget.cget("border_color")
                    current_widget.grid_forget()
                    textbox = ctk.CTkTextbox(self.form_frame, height=60, wrap="word", border_width=2)
                    if val:
                        textbox.insert("1.0", val)
                    textbox.grid(
                        row=row_idx, column=0, sticky="e", padx=(10, 0), pady=(2, 2)
                    )
                    self.entries[field_name] = textbox
                    # Aplica a cor da borda e faz log da mudança
                    textbox.configure(border_color=current_border_color)
                    logging.debug(
                        f"Cor da borda atualizada para {current_border_color} no campo {field_name}"
                    )
                    textbox.focus()
                    textbox.bind("<FocusOut>", lambda e, fn=field_name, r=row_idx: to_entry(e, fn, r))

                def to_entry(event, field_name=field, row_idx=i):
                    current_widget = self.entries[field_name]
                    if not isinstance(current_widget, ctk.CTkTextbox):
                        return
                    val = current_widget.get("1.0", "end-1c")
                    current_widget.grid_forget()
                    entry = ctk.CTkEntry(self.form_frame, placeholder_text=f"{field_label}")
                    if val:
                        entry.insert(0, val)
                    entry.grid(
                        row=row_idx, column=0, sticky="e", padx=(10, 0), pady=(2, 2)
                    )
                    self.entries[field_name] = entry
                    entry.bind("<FocusIn>", lambda e, fn=field_name, r=row_idx: to_textbox(e, fn, r))

                entry.bind("<FocusIn>", lambda e, fn=field, r=i: to_textbox(e, fn, r))
            else:
                entry = ctk.CTkEntry(self.form_frame, placeholder_text=f"{field_label}")
                if hasattr(self, "clear_on_switch") and not self.clear_on_switch.get():
                    valor_antigo = old_values.get(field)
                    if valor_antigo not in (None, ""):
                        entry.insert(0, valor_antigo)
                entry.grid(row=i, column=0, sticky="e", padx=(10, 0), pady=(2, 2))
                self.entries[field] = entry

            # Se o campo for 'Nome', adiciona trace para atualizar o título
            if field == "Nome":

                def update_title_nome(*args):
                    nome_val = self.entries["Nome"].get()
                    if nome_val:
                        self.title(f"{nome_val} - Modo Simples - Linx Fast")
                    else:
                        self.title("Modo Simples - Linx Fast")

                # Adiciona trace para atualizar o título ao mudar o valor
                try:
                    self.entries["Nome"].bind(
                        "<KeyRelease>", lambda e: update_title_nome()
                    )
                    update_title_nome()
                except Exception:
                    pass

        # Adiciona os botões ao final do form_frame (sempre na última linha)
        btn_row = len(used_fields)
        self.form_frame.grid_columnconfigure(0, weight=1)
        self.form_frame.grid_columnconfigure(1, weight=0)
        self.form_frame.grid_columnconfigure(2, weight=0)

        self.copy_btn = ctk.CTkButton(
            self.form_frame,
            text="Copiar",
            fg_color="#7E57C2",
            font=ctk.CTkFont(size=13, weight="bold"),
            width=3,
            command=self.copy_template,
        )
        self.copy_btn.grid(
            row=btn_row, column=0, padx=(0, 37), pady=(15, 0), sticky="ew"
        )

        self.clear_btn = ctk.CTkButton(
            self.form_frame,
            text="❌",
            fg_color="#A94444",
            hover_color="#FF5252",
            font=ctk.CTkFont(size=13, weight="bold"),
            width=3,
            command=self.clear_fields,
        )
        self.clear_btn.grid(
            row=btn_row, column=0, padx=(37, 0), pady=(15, 0), sticky="e"
        )

        # Ajusta o tamanho da janela com base nos campos
        self.update_idletasks()
        form_height = self.form_frame.winfo_reqheight()

        if len(self.entries) == 0:
            # Reposiciona o botão Copiar logo abaixo do dropdown
            self.copy_btn.grid_configure(row=0, column=0, pady=(10, 0))
            self.clear_btn.grid_configure(row=0, column=0, pady=(10, 0))
            self.update_idletasks()
            # Altura dos elementos fixos
            title_height = 0
            dropdown_height = 0
            copy_btn_height = self.copy_btn.winfo_reqheight()
            # Busca altura do título
            for widget in self.grid_slaves(row=0, column=0):
                title_height = widget.winfo_reqheight()
                break
            # Busca altura do dropdown (pode estar em (1,1) ou (1,0) dependendo do layout)
            for widget in self.grid_slaves():
                info = widget.grid_info()
                if info.get("row") == 1 and info.get("column") in (0, 1):
                    dropdown_height = max(dropdown_height, widget.winfo_reqheight())    
            # Margens e paddings
            padding = 15  # espaço para margens/paddings
            min_height = title_height + dropdown_height + copy_btn_height + padding
            if min_height < 150:
                min_height = 150
            self.geometry(f"400x{min_height}")
        else:
            # Mantém os botões abaixo dos campos
            base_height = 140
            if form_height < 40:
                form_height = 40
            desired_height = form_height + base_height
            screen_height = self.winfo_screenheight()
            max_height = int(screen_height * 0.9)
            min_height = 220
            final_height = max(min(desired_height, max_height), min_height)
            self.geometry(f"400x{final_height}")                

    def copy_template(self):
        """Processa o template com os valores dos campos e copia para o clipboard"""
        from main_window import placeholder_engine  # Importa aqui para evitar import circular

        logging.info("Copiando template processado para o clipboard...")

        template_name = self.template_var.get()
        if not template_name:
            self.app.show_snackbar(
                "Selecione um template!", toast_type="error", parent=self
            )
            return

        content = self.manager.get_template(template_name)

        # 1. Coleta valores dos campos
        import customtkinter as ctk
        field_values = {}
        for key, entry in self.entries.items():
            if isinstance(entry, ctk.CTkCheckBox):
                value = "Sim" if entry.get() else "Não"
            elif isinstance(entry, ctk.CTkSwitch):
                value = "Sim" if entry.get() == "Sim" else "Não"
            elif isinstance(entry, ctk.StringVar):
                value = str(entry.get())
            elif isinstance(entry, ctk.CTkTextbox):
                value = entry.get("1.0", "end-1c")
            else:
                value = str(entry.get())
            field_values[key] = value

        # 2. Processa lógica condicional no template
        def process_conditionals(template, field_values):
            import re
            def cond_repl(match):
                field = match.group(1)
                true_val = match.group(2)
                false_val = match.group(3)
                val = field_values.get(field, "")
                # Valores considerados como verdadeiro
                val_lower = str(val).lower()
                return true_val if val_lower in {"sim", "true", "1"} else false_val
            return re.sub(r"\$([^\$?]+)\?([^\|$]+)\|([^\$]+)\$", cond_repl, template)

        content = process_conditionals(content, field_values)

        # 3. Substitui placeholders simples
        for key, value in field_values.items():
            content = content.replace(f"${key}$", value or "")

        # 4. Substitui placeholders automáticos/dinâmicos
        content = placeholder_engine.process(content)

        import pyperclip
        pyperclip.copy(content)
        logging.debug("Template copiado com sucesso para o clipboard")
        self.app.show_snackbar(
            "Copiado com sucesso!", toast_type="success", parent=self
        )

    def clear_fields(self):
        """Limpa todos os campos do formulário"""
        logging.info("Limpando campos do formulário no Modo Simples...")
        # Itera pelos widgets no entries
        for field_name, widget in self.entries.items():
            # Agrupa widgets por tipo de ação
            if isinstance(widget, (ctk.CTkCheckBox, ctk.CTkSwitch)):
                widget.deselect()
            elif isinstance(widget, (ctk.StringVar)):
                widget.set("")  # Para radiobuttons
            elif isinstance(widget, (ctk.CTkEntry)):
                widget.delete(0, "end")
                widget.configure(placeholder_text=field_name)
            elif isinstance(widget, (ctk.CTkTextbox)):
                widget.delete("1.0", "end")

        # Mostra mensagem de feedback
        if hasattr(self.app, "show_snackbar"):
            self.app.show_snackbar("Campos limpos!", toast_type="info", parent=self)

    def copy_and_close(self):
        template_name = self.template_var.get()
        if not template_name:
            messagebox.showerror("Erro", "Selecione um template.")
            return

        content = self.manager.get_template(template_name)

        for key, entry in self.entries.items():
            value = entry.get()
            content = content.replace(f"${key}$", value or "")

        import pyperclip
        pyperclip.copy(content)
        self.destroy()

    def _safe_after(self, delay, callback):
        after_id = self.after(delay, callback)
        self._after_ids.add(after_id)
        return after_id

    def _cancel_all_afters(self):
        """Cancela todos os callbacks agendados de forma segura"""
        from contextlib import suppress

        for after_id in list(self._after_ids):
            with suppress(Exception):
                self.after_cancel(after_id)
            self._after_ids.discard(after_id)

    def on_close(self):
        self._cancel_all_afters()
        self.destroy()
