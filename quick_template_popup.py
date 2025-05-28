import customtkinter as ctk
from tkinter import StringVar
from tkinter import messagebox
from app import TemplateApp
from template_editor import TemplateEditor
from template_manager import TemplateManager
from theme_manager import ThemeManager

class QuickTemplatePopup(ctk.CTkToplevel):
    def __init__(self, master, manager):
        super().__init__(master)
        self.title("Modo Simples – Linx Fast")
        self.manager = manager
        self.theme_manager = ThemeManager()
        self.geometry("325x250")
        self.entries = {}

        self.template_var = StringVar(value="")
        self._build_interface()

    def _build_interface(self):
        self.grid_columnconfigure(0, weight=0)  # coluna do botão pin
        self.grid_columnconfigure(1, weight=1)  # coluna do dropdown expansível
        self.grid_columnconfigure(2, weight=0)  # coluna do toggle

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
        self.clear_on_switch = ctk.BooleanVar(value=True)
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
        self.clear_toggle.bind("<Leave>", hide_tooltip)
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
        self.form_frame.grid(row=2, column=0, columnspan=3, padx=20, pady=(5, 0), sticky="nsew")
        self.form_frame.grid_columnconfigure(0, weight=1)

        # Botão de ação
        self.copy_btn = ctk.CTkButton(
            self,
            text="Copiar",
            fg_color="#7E57C2",
            command=self.copy_template
        )
        self.copy_btn.grid(row=3, column=0, columnspan=3, pady=(15, 15), padx=20, sticky="ew")

    def toggle_always_on_top(self):
        current = self.attributes("-topmost")
        new_state = not current
        self.attributes("-topmost", new_state)
        self.pin_button.configure(fg_color="green" if new_state else self.theme_manager.get_theme_default_color(ctk.CTkButton, "fg_color"))
        self.pin_button.configure(text="📌" if new_state else "📍")
        if new_state:
            TemplateApp.show_snackbar("PIN ativado!", toast_type="info")
        else:
            TemplateApp.show_snackbar("PIN desativado!", toast_type="info")


    def load_template(self, template_name):
        from app import placeholder_engine  # Importa aqui para evitar import circular
        import json
        import os

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


        for i, field in enumerate(used_fields):
            label = ctk.CTkLabel(self.form_frame, text=field)
            label.grid(row=i, column=0, sticky="w", pady=(2, 2))

            # --- Procedimento Executado e Problema Relatado: alterna Entry/Textbox conforme foco ---
            if field in ("Procedimento Executado", "Problema Relatado"):
                entry = ctk.CTkEntry(self.form_frame, placeholder_text=f"{field}")
                # Se o toggle "Limpar?" estiver desmarcado, restaura valor antigo se existir
                if hasattr(self, "clear_on_switch") and not self.clear_on_switch.get():
                    valor_antigo = old_values.get(field, None)
                    if valor_antigo not in (None, ""):
                        entry.insert(0, valor_antigo)
                entry.grid(row=i, column=0, sticky="e", padx=(100, 0), pady=(2, 2))
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
                    textbox.grid(row=row_idx, column=0, sticky="e", padx=(100, 0), pady=(2, 2))
                    self.entries[field_name] = textbox
                    textbox.after(1, lambda: textbox.configure(border_color=current_border_color))
                    textbox.border_color = current_border_color
                    textbox.focus()
                    textbox.bind("<FocusOut>", lambda e, fn=field_name, r=row_idx: to_entry(e, fn, r))

                def to_entry(event, field_name=field, row_idx=i):
                    current_widget = self.entries[field_name]
                    if not isinstance(current_widget, ctk.CTkTextbox):
                        return
                    val = current_widget.get("1.0", "end-1c")
                    current_widget.grid_forget()
                    entry = ctk.CTkEntry(self.form_frame, placeholder_text=f"{field_name}")
                    if val:
                        entry.insert(0, val)
                    entry.grid(row=row_idx, column=0, sticky="e", padx=(100, 0), pady=(2, 2))
                    self.entries[field_name] = entry
                    entry.bind("<FocusIn>", lambda e, fn=field_name, r=row_idx: to_textbox(e, fn, r))

                entry.bind("<FocusIn>", lambda e, fn=field, r=i: to_textbox(e, fn, r))
            # --- Demais campos: Entry padrão ---
            else:
                entry = ctk.CTkEntry(self.form_frame, placeholder_text=f"{field}")
                if hasattr(self, "clear_on_switch") and not self.clear_on_switch.get():
                    valor_antigo = old_values.get(field, None)
                    if valor_antigo not in (None, ""):
                        entry.insert(0, valor_antigo)
                entry.grid(row=i, column=0, sticky="e", padx=(100, 0), pady=(2, 2))
                self.entries[field] = entry

        # Ajusta o tamanho da janela com base nos campos
        self.update_idletasks()
        form_height = self.form_frame.winfo_reqheight()

        if len(self.entries) == 0:
            # Reposiciona o botão Copiar logo abaixo do dropdown
            self.copy_btn.grid_configure(row=2, pady=(10, 10))
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
            padding = 30  # espaço para margens/paddings
            min_height = title_height + dropdown_height + copy_btn_height + padding
            if min_height < 170:
                min_height = 170
            self.geometry(f"400x{min_height}")
        else:
            # Mantém o botão Copiar abaixo dos campos
            self.copy_btn.grid_configure(row=3, pady=(15, 15))
            # Altura base para botões e margens
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
            from app import placeholder_engine  # Importa aqui para evitar import circular

            template_name = self.template_var.get()
            if not template_name:
                messagebox.showerror("Erro", "Selecione um template.")
                return

            content = self.manager.get_template(template_name)

            for key, entry in self.entries.items():
                value = entry.get()
                content = content.replace(f"${key}$", value if value else "")

            # Substitui placeholders automáticos/dinâmicos
            content = placeholder_engine.process(content)

            import pyperclip
            pyperclip.copy(content)

    def copy_and_close(self):
        template_name = self.template_var.get()
        if not template_name:
            messagebox.showerror("Erro", "Selecione um template.")
            return

        content = self.manager.get_template(template_name)

        for key, entry in self.entries.items():
            value = entry.get()
            content = content.replace(f"${key}$", value if value else "")

        import pyperclip
        pyperclip.copy(content)
        self.destroy()
