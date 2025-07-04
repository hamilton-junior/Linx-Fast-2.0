import customtkinter as ctk
try:
    from version import VERSION, BUILD_DATE
except ImportError:
    VERSION, BUILD_DATE = "dev", "dev"

class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self._after_ids = set()  
        self.title("Configurações")
        # Não define geometry fixa!
        self.master = master
        self.expandable_fields = set(master.expandable_fields)
        self.check_vars = {}


        # Aparência e tema
        theme_frame = ctk.CTkFrame(self)
        theme_frame.pack(fill="x", padx=20, pady=(15, 5))
        ctk.CTkLabel(theme_frame, text="Aparência e Tema", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="center", pady=(0, 5))

        # Aparência (Switch)
        self.appearance_var = ctk.StringVar(value=master.appearance_mode if master.appearance_mode in ("dark", "light") else "dark")
        ctk.CTkLabel(theme_frame, text="Modo de Aparência:").pack(anchor="w")
        self.appearance_switch = ctk.CTkSwitch(
            theme_frame,
            text="Modo Escuro",
            variable=self.appearance_var,
            onvalue="dark",
            offvalue="light"
        )
        self.appearance_switch.pack(anchor="w", pady=(0, 5))
        # Atualiza o texto do switch conforme o valor
        def update_switch_text():
            self.appearance_switch.configure(text="Modo Escuro" if self.appearance_var.get() == "dark" else "Modo Claro")
        self.appearance_var.trace_add("write", lambda *a: self._safe_after(0, update_switch_text))
        self._safe_after(0, update_switch_text)

        # Temas disponíveis (padrão + arquivos .json em /themes)
        self.theme_var = ctk.StringVar(value=master.theme_name)
        ctk.CTkLabel(theme_frame, text="Tema de Cores:").pack(anchor="w")
        import os
        theme_dir = "themes"
        os.makedirs(theme_dir, exist_ok=True)
        themes = ["green", "blue", "dark-blue"]
        for file in os.listdir(theme_dir):
            if file.endswith(".json"):
                themes.append(file[:-5])
        themes = sorted(set(themes))
        ctk.CTkOptionMenu(
            theme_frame,
            variable=self.theme_var,
            values=themes
        ).pack(anchor="w", pady=(0, 5))

        # Expansão automática
        frame = ctk.CTkFrame(self)
        frame.pack(fill="both", expand=True, padx=20, pady=10)
        ctk.CTkLabel(frame, text="Campos com Expansão Automática", font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(5, 10))

        for field in master.fixed_fields:
            var = ctk.BooleanVar(value=field in self.expandable_fields)
            chk = ctk.CTkCheckBox(frame, text=field, variable=var)
            chk.pack(anchor="w", pady=2)
            self.check_vars[field] = var

        # --- Label de versão acima dos botões, com tooltip de data do build ---
        version_frame = ctk.CTkFrame(self, fg_color="transparent")
        version_frame.pack(fill="x", pady=(0, 2), padx=8)
        label_version = ctk.CTkLabel(
            version_frame,
            text=f"{VERSION}",
            font=ctk.CTkFont(size=10, slant="italic"),
            text_color="#888888",
            anchor="e",
            justify="right"
        )
        label_version.pack(side="right", padx=(0, 10), anchor="se")

        # Tooltip customizado para mostrar a data do build
        def show_tooltip(event=None):
            if hasattr(label_version, "_tooltip") and label_version._tooltip is not None:
                return
            tooltip = ctk.CTkToplevel(label_version)
            tooltip.overrideredirect(True)
            tooltip.attributes("-topmost", True)
            tooltip_label = ctk.CTkLabel(
                tooltip,
                text=f"Build: {BUILD_DATE}",
                font=ctk.CTkFont(size=11),
                text_color="#fff",
                fg_color="#222",
                padx=7, pady=3
            )
            tooltip_label.pack()
            label_version.update_idletasks()
            x = label_version.winfo_rootx() + label_version.winfo_width() + 7
            y = label_version.winfo_rooty() - 3
            tooltip.geometry(f"+{x}+{y}")
            label_version._tooltip = tooltip

        def hide_tooltip(event=None):
            if hasattr(label_version, "_tooltip") and label_version._tooltip is not None:
                try:
                    label_version._tooltip.destroy()
                except Exception:
                    pass
                label_version._tooltip = None

        label_version.bind("<Enter>", show_tooltip)
        label_version.bind("<Leave>", hide_tooltip)

        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(fill="x", pady=(10, 16), padx=8)  # padding extra para evitar corte

        ctk.CTkButton(btn_frame, text="Salvar", fg_color="#7E57C2", command=self.save_and_close).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Cancelar", fg_color="#A94444", command=self.destroy).pack(side="right", padx=10)

        # Ajusta o tamanho da janela para o conteúdo
        self.update_idletasks()
        # Define um tamanho mínimo confortável, mas deixa o resto automático
        self.minsize(340, 260)

    def save_and_close(self):
        self.master.expandable_fields = [field for field, var in self.check_vars.items() if var.get()]
        self.master.save_expandable_fields_config()
        # Salva e aplica tema e aparência
        theme = self.theme_var.get()
        mode = self.appearance_var.get()
        self.master.save_theme_config(theme, mode)
        ctk.set_appearance_mode(mode)
        # Ajuste: se for tema customizado, usa o caminho completo
        import os
        theme_path = os.path.join("themes", f"{theme}.json")
        if theme in ("green", "blue", "dark-blue") or not os.path.exists(theme_path):
            ctk.set_default_color_theme(theme)
        else:
            ctk.set_default_color_theme(theme_path)
        self.master.theme_manager.set_theme(theme)
        self.master.theme_manager.set_appearance_mode(mode)
        self.master.theme_name = theme
        self.master.appearance_mode = mode

        # Reconstrói toda a interface principal, preservando o estado
        self.master.reload_theme_and_interface()
        self.destroy()


    def _safe_after(self, delay, callback):
        after_id = self.after(delay, callback)
        self._after_ids.add(after_id)
        return after_id

    def _cancel_all_afters(self):
        for after_id in list(self._after_ids):
            try:
                self.after_cancel(after_id)
            except Exception:
                pass
            self._after_ids.discard(after_id)

    def on_close(self):
        self._cancel_all_afters()
        self.destroy()
