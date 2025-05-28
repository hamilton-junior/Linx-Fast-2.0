import customtkinter as ctk

class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
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
        self.appearance_var.trace_add("write", lambda *a: update_switch_text())
        update_switch_text()

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
