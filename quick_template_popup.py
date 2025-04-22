import customtkinter as ctk
from tkinter import StringVar
from tkinter import messagebox


class QuickTemplatePopup(ctk.CTkToplevel):
    def __init__(self, master, manager):
        super().__init__(master)
        self.title("Modo Rápido – Linx Fast")
        self.manager = manager
        self.geometry("325x250")
        self.entries = {}

        self.template_var = StringVar(value="")
        self._build_interface()

    def _build_interface(self):
        self.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(self, text="Selecionar Template", font=("Arial", 14, "bold"))
        title.grid(row=0, column=0, pady=(5, 5))

        self.template_dropdown = ctk.CTkOptionMenu(self, values=self.manager.get_template_names(),
                                                    variable=self.template_var,
                                                    command=self.load_template)
        self.template_dropdown.grid(row=1, column=0, padx=20, pady=(0, 5), sticky="ew")

        self.form_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.form_frame.grid(row=2, column=0, padx=20, pady=(5, 0), sticky="nsew")
        self.form_frame.grid_columnconfigure(0, weight=1)

        self.copy_btn = ctk.CTkButton(self, text="Copiar e Fechar", fg_color="#7E57C2",
                                        command=self.copy_and_close)
        self.copy_btn.grid(row=3, column=0, pady=(15, 0))

    def load_template(self, template_name):
        self.entries.clear()
        for widget in self.form_frame.winfo_children():
            widget.destroy()

        content = self.manager.get_template(template_name)
        placeholders = self.manager.extract_placeholders(content)
        used_fields = sorted(placeholders)

        for i, field in enumerate(used_fields):
            label = ctk.CTkLabel(self.form_frame, text=field)
            label.grid(row=i, column=0, sticky="w", pady=(2, 2))

            entry = ctk.CTkEntry(self.form_frame, placeholder_text=f"{field}")
            entry.grid(row=i, column=0, sticky="e", padx=(100, 0), pady=(2, 2))
            self.entries[field] = entry

        # Ajusta o tamanho da janela com base nos campos
        new_height = 105 + len(used_fields) * 35
        self.geometry(f"400x{new_height}")

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
