# template_editor.py
import customtkinter as ctk
from customtkinter import CTkTextbox, CTkButton, CTkOptionMenu, CTkFrame, CTkLabel, CTkFont, CTkInputDialog
import tkinter.messagebox as mbox


class TemplateEditor(ctk.CTkToplevel):
    def __init__(self, master, manager, get_fields_callback, current_template=None):
        super().__init__(master)
        self.title("Editor de Templates")
        self.geometry("800x600")
        self.transient(master)
        self.grab_set()

        self.manager = manager
        self.get_fields_callback = get_fields_callback

        self.current_template = current_template or self.manager.get_template_names()[0]
        self.template_display_name = ctk.StringVar(value=self.manager.meta.get_display_name(self.current_template))

        self._build_interface()
        self.load_template()

    def _build_interface(self):
        self.main_frame = CTkFrame(self)
        self.main_frame.pack(expand=True, fill="both", padx=10, pady=10)

        # Top Bar
        top_bar = CTkFrame(self.main_frame, fg_color="transparent")
        top_bar.pack(fill="x")

        CTkLabel(top_bar, text="Template:").pack(side="left", padx=(0, 6))

        self.template_selector = CTkOptionMenu(
            top_bar,
            variable=self.template_display_name,
            values=self.manager.get_display_names(),
            command=self.on_template_change,
            width=300
        )
        self.template_selector.pack(side="left", padx=(0, 10))

        CTkButton(top_bar, text="Novo", width=80, command=self.create_new_template).pack(side="left")
        CTkButton(top_bar, text="Salvar", width=80, command=self.save_template).pack(side="left", padx=(6, 0))
        CTkButton(top_bar, text="Excluir", width=80, command=self.delete_template).pack(side="left", padx=(6, 0))
        CTkButton(top_bar, text="Fechar", width=80, command=self.destroy).pack(side="right")

        # Editor e campos
        self.editor_frame = CTkFrame(self.main_frame)
        self.editor_frame.pack(expand=True, fill="both", pady=10)

        self.textbox = CTkTextbox(self.editor_frame, wrap="word")
        self.textbox.pack(side="left", expand=True, fill="both", padx=(0, 10))

        self.side_frame = CTkFrame(self.editor_frame, width=200)
        self.side_frame.pack(side="left", fill="y")

        CTkLabel(self.side_frame, text="Placeholders Disponíveis:").pack(pady=(0, 5))

        self.fields_listbox = CTkTextbox(self.side_frame, height=25, wrap="none")
        self.fields_listbox.configure(state="disabled")
        self.fields_listbox.pack(fill="both", expand=True)

    def load_template(self):
        template_text = self.manager.get_template(self.current_template)
        self.textbox.delete("1.0", "end")
        self.textbox.insert("1.0", template_text)
        self.update_fields_list()

    def save_template(self):
        new_content = self.textbox.get("1.0", "end").strip()
        if not new_content:
            mbox.showwarning("Aviso", "O conteúdo do template não pode estar vazio.")
            return

        self.manager.update_template(self.current_template, new_content)
        mbox.showinfo("Salvo", "Template salvo com sucesso!")

    def delete_template(self):
        if self.current_template.startswith("Geral"):
            mbox.showwarning("Protegido", "Templates gerais não podem ser removidos.")
            return

        confirm = mbox.askyesno("Confirmação", f"Remover template '{self.template_display_name.get()}'?")
        if confirm:
            self.manager.delete_template(self.current_template)
            self._refresh_templates()
            self.on_template_change(self.manager.meta.get_display_name(self.current_template))

    def create_new_template(self):
        dialog = CTkInputDialog(text="Nome do novo template:", title="Novo Template")
        name = dialog.get_input()
        if not name:
            return

        real_name = f"Custom / {name}"
        if real_name in self.manager.get_template_names():
            mbox.showerror("Erro", "Já existe um template com esse nome.")
            return

        self.manager.add_template(real_name, "")
        self._refresh_templates()
        self.current_template = real_name
        self.template_display_name.set(self.manager.meta.get_display_name(real_name))
        self.load_template()

    def on_template_change(self, display_name):
        real_name = self.manager.meta.get_real_name(display_name)
        self.current_template = real_name
        self.template_display_name.set(display_name)
        self.load_template()

    def update_fields_list(self):
        self.fields_listbox.configure(state="normal")
        self.fields_listbox.delete("1.0", "end")
        fields = self.get_fields_callback()
        for f in fields["fixed"] + fields["dynamic"]:
            self.fields_listbox.insert("end", f"${f}$\n")
        self.fields_listbox.configure(state="disabled")

    def _refresh_templates(self):
        self.manager.load_templates()
        self.template_selector.configure(values=self.manager.get_display_names())
        all_templates = self.manager.get_template_names()
        self.current_template = all_templates[-1] if all_templates else None
