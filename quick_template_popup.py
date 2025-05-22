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

        # Título
        title = ctk.CTkLabel(self, text="Selecionar Template", font=("Arial", 14, "bold"))
        title.grid(row=0, column=0, columnspan=2, pady=(5, 0), padx=10, sticky="ew")

        # Botão fixo à esquerda
        self.pin_button = ctk.CTkButton(
            self,
            text="📍",
            width=36,
            command=self.toggle_always_on_top
        )
        self.pin_button.grid(row=1, column=0, padx=(10, 5), pady=5, sticky="w")

        # Dropdown expansível ocupando o espaço restante
        self.template_dropdown = ctk.CTkOptionMenu(
            self,
            values=self.manager.get_template_names(),
            variable=self.template_var,
            command=self.load_template
        )
        self.template_dropdown.grid(row=1, column=1, padx=(0, 10), pady=5, sticky="ew")

        # Frame para os campos
        self.form_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.form_frame.grid(row=2, column=0, columnspan=2, padx=20, pady=(5, 0), sticky="nsew")
        self.form_frame.grid_columnconfigure(0, weight=1)

        # Botão de ação
        self.copy_btn = ctk.CTkButton(
            self,
            text="Copiar",
            fg_color="#7E57C2",
            command=self.copy_template
        )
        self.copy_btn.grid(row=3, column=0, columnspan=2, pady=(15, 15), padx=20, sticky="ew")

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

            self.entries.clear()
            for widget in self.form_frame.winfo_children():
                widget.destroy()

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

            used_fields = sorted([ph for ph in placeholders if not is_automatic(ph)])

            for i, field in enumerate(used_fields):
                label = ctk.CTkLabel(self.form_frame, text=field)
                label.grid(row=i, column=0, sticky="w", pady=(2, 2))

                entry = ctk.CTkEntry(self.form_frame, placeholder_text=f"{field}")
                entry.grid(row=i, column=0, sticky="e", padx=(100, 0), pady=(2, 2))
                self.entries[field] = entry

            # Ajusta o tamanho da janela com base nos campos
            new_height = 105 + len(used_fields) * 35
            self.geometry(f"400x{new_height}")

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
