import customtkinter as ctk
from tkinter import messagebox
from customtkinter import CTkInputDialog
import logging
from logger_config import auto_log_functions

# Get the module logger
logger = logging.getLogger(__name__)


@auto_log_functions
class TemplateEditor(ctk.CTkToplevel):

    def __init__(
        self,
        master,
        manager,
        get_placeholders_callback,
        current_template="Template Padrão",
    ):
        logger.info(f"Iniciando Editor de Templates para: {current_template}")
        super().__init__(master)
        self.title("Editor de Templates")
        self._after_ids = set()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.geometry("860x540")
        self.transient(master)
        self.grab_set()

        # Register with theme manager
        if hasattr(master, "theme_manager"):
            self.theme_manager = master.theme_manager
            self.theme_manager.register_window(self)

        self.manager = manager
        self.get_placeholders = get_placeholders_callback
        self.template_names = self.manager.get_template_names()

        self.original_name = current_template
        self.template_var = ctk.StringVar(
            value=self.manager.meta.get_display_name(current_template)
        )

        self.last_saved_content = self.manager.get_template(current_template)

        self._build_interface()
        self.load_template(current_template)

    def _build_interface(self):
        self.grid_columnconfigure((0, 1), weight=1)
        self.grid_rowconfigure(1, weight=1)

        top_frame = ctk.CTkFrame(self)
        top_frame.grid(
            row=0, column=0, columnspan=4, sticky="ew", padx=10, pady=(10, 5)
        )
        top_frame.grid_columnconfigure(0, weight=1)

        self.dropdown = ctk.CTkOptionMenu(
            top_frame,
            values=self.manager.get_display_names(),
            variable=self.template_var,
            command=self.on_template_select,
            width=400,
        )
        self.dropdown.grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            top_frame, text="Renomear", width=80, command=self.rename_template
        ).grid(row=0, column=1, padx=5)
        ctk.CTkButton(
            top_frame, text="Novo", width=80, command=self.create_new_template
        ).grid(row=0, column=2, padx=5)
        ctk.CTkButton(
            top_frame, text="⭐", width=40, command=self.toggle_favorite
        ).grid(row=0, column=3, padx=5)
        ctk.CTkButton(
            top_frame, text="🔒", width=40, command=self.toggle_protected
        ).grid(row=0, column=4, padx=5)

        self.content_box = ctk.CTkTextbox(self, wrap="word")
        self.content_box.grid(
            row=1, column=0, columnspan=4, sticky="nsew", padx=10, pady=(5, 5)
        )
        self.content_box.bind("<Control-space>", self.show_autocomplete)
        self.content_box.bind("<KeyRelease>", self._schedule_highlight)
        
        # Configurar TAGS de destaque (estilo moderno)
        self.content_box._textbox.tag_config("variable", foreground="#a06cd5") # Roxo para variáveis
        self.content_box._textbox.tag_config("conditional", foreground="#3a86ff") # Azul para condicionais
        self.content_box._textbox.tag_config("bracket", foreground="#ff006e") # Rosa para colchetes [checkbox]


        # Botão de importar do NocoDB acima da lista de variáveis (pequeno, igual aos outros)
        ctk.CTkButton(
            self,
            text="Importar",
            width=1,
            font=ctk.CTkFont(size=12),
            command=self.master.show_nocodb_templates,
        ).grid(row=0, column=4, padx=(10, 10), pady=(10, 0), sticky="ne")

        self.placeholder_box = ctk.CTkTextbox(self, width=240)
        self.placeholder_box.grid(
            row=1, column=4, sticky="ns", padx=(5, 10), pady=(5, 5)
        )
        self.placeholder_box.configure(state="disabled")

        btn_frame = ctk.CTkFrame(self)
        btn_frame.grid(row=2, column=0, columnspan=5, pady=(10, 10))

        ctk.CTkButton(
            btn_frame, text="Salvar", fg_color="#7E57C2", command=self.save_template
        ).pack(side="left", padx=10)
        ctk.CTkButton(
            btn_frame, text="Remover", fg_color="#A94444", command=self.delete_template
        ).pack(side="left", padx=10)

    def get_real_name(self):
        return self.manager.meta.get_real_name(self.template_var.get())

    def has_unsaved_changes(self):
        return self.content_box.get("1.0", "end").strip() != self.last_saved_content

    def on_template_select(self, display_name):
        selected_name = self.manager.meta.get_real_name(display_name)

        if selected_name == self.original_name:
            return

        if self.has_unsaved_changes():
            save = messagebox.askyesno(
                "Salvar alterações?",
                f"Deseja salvar as alterações em '{self.original_name}'?",
            )
            if save:
                self.save_template()

        self.original_name = selected_name
        self.template_var.set(self.manager.meta.get_display_name(selected_name))
        self.load_template(selected_name)

    def rename_template(self):
        new_name = CTkInputDialog(
            title="Renomear Template", text="Novo nome do template:"
        ).get_input()
        if not new_name:
            return

        old_category, _ = self.manager._split_name(self.original_name)
        full_new = f"{old_category} / {new_name}" if old_category else new_name

        content = self.content_box.get("1.0", "end").strip()
        self.manager.save_template(self.original_name, full_new, content)

        self.original_name = full_new
        self.template_var.set(self.manager.meta.get_display_name(full_new))
        self.refresh_templates()
        self.last_saved_content = content
        self.refresh_placeholder_list(content)

    def create_new_template(self):
        popup = ctk.CTkToplevel(self)
        popup.title("Novo Template")
        popup.geometry("400x160")
        popup.transient(self)
        popup.grab_set()
        popup.grid_columnconfigure(0, weight=1)

        label = ctk.CTkLabel(popup, text="Nome do novo template:")
        label.grid(row=0, column=0, padx=20, pady=(20, 5))

        name_entry = ctk.CTkEntry(popup)
        name_entry.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")

        btn_frame = ctk.CTkFrame(popup)
        btn_frame.grid(row=2, column=0, pady=10)

        def criar():
            new_name = name_entry.get().strip()
            if not new_name:
                messagebox.showerror("Erro", "Nome inválido.")
                return

            category = self.manager._split_name(self.original_name)[0]
            full_name = f"{category} / {new_name}" if category else new_name

            if full_name in self.manager.get_template_names():
                messagebox.showerror("Erro", "Esse template já existe.")
                return

            manter = messagebox.askyesno(
                "Usar conteúdo atual?",
                "Deseja manter o conteúdo atual no novo template?",
            )
            content = (
                self.content_box.get("1.0", "end").strip()
                if manter
                else self.manager.get_default_template()
            )

            self.manager.add_template(full_name, content)
            self.original_name = full_name
            self.template_var.set(self.manager.meta.get_display_name(full_name))
            self.refresh_templates()
            self.load_template(full_name)
            popup.destroy()

        ctk.CTkButton(btn_frame, text="Criar", command=criar).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Cancelar", command=popup.destroy).pack(
            side="left", padx=10
        )

    def _schedule_highlight(self, event=None):
        if hasattr(self, "_highlight_timer"):
            self.after_cancel(self._highlight_timer)
        self._highlight_timer = self.after(300, self._highlight_variables)

    def _highlight_variables(self):
        """Destaque básico de sintaxe para variáveis no textbox"""
        try:
            content = self.content_box.get("1.0", "end")
            self.content_box._textbox.tag_remove("variable", "1.0", "end")
            self.content_box._textbox.tag_remove("conditional", "1.0", "end")
            self.content_box._textbox.tag_remove("bracket", "1.0", "end")

            import re
            
            # Highlight $variables$
            for match in re.finditer(r"\$[^\$\n\?]+\$", content):
                start = f"1.0 + {match.start()} chars"
                end = f"1.0 + {match.end()} chars"
                self.content_box._textbox.tag_add("variable", start, end)

            # Highlight $[conditional]?$
            for match in re.finditer(r"\$[^\$\n]+\?[^\$\n]+\$", content):
                start = f"1.0 + {match.start()} chars"
                end = f"1.0 + {match.end()} chars"
                self.content_box._textbox.tag_add("conditional", start, end)

            # Highlight [type]
            for match in re.finditer(r"\[(checkbox|switch|list:[^\]]+)\]", content):
                start = f"1.0 + {match.start()} chars"
                end = f"1.0 + {match.end()} chars"
                self.content_box._textbox.tag_add("bracket", start, end)
        except Exception:
            pass

    def load_template(self, name):
        content = self.manager.get_template(name)
        self.last_saved_content = content
        self.content_box.delete("1.0", "end")
        self.content_box.insert("1.0", content)
        self.refresh_placeholder_list(content)

    def refresh_placeholder_list(self, content):
        all_placeholders = self.manager.extract_placeholders(content)
        fixed = self.get_placeholders()["fixed"]
        dynamic = self.get_placeholders()["dynamic"]

        self.placeholder_box.configure(state="normal")
        self.placeholder_box.delete("1.0", "end")

        self.placeholder_box.insert("end", "--- Campos Padrões ---\n")
        for p in fixed:
            self.placeholder_box.insert("end", f"${p}$\n")

        self.placeholder_box.insert("end", "\n--- Campos Personalizados ---\n")
        for p in dynamic:
            self.placeholder_box.insert("end", f"${p}$\n")

        self.placeholder_box.configure(state="disabled")

    def save_template(self):
        name = self.get_real_name()
        content = self.content_box.get("1.0", "end").strip()

        if not name:
            messagebox.showerror("Erro", "O nome do template não pode ser vazio.")
            return

        self.manager.save_template(self.original_name, name, content)
        self.original_name = name
        self.template_var.set(self.manager.meta.get_display_name(name))
        self.refresh_templates()
        self.last_saved_content = content
        self.refresh_placeholder_list(content)

    def delete_template(self):
        name = self.get_real_name()
        meta = self.manager.meta

        if (
            name == "Geral / Template Padrão"
            or meta.is_protected(name)
            or meta.is_favorite(name)
        ):
            messagebox.showwarning(
                "Protegido",
                "Este template está protegido ou favoritado e não pode ser excluído.",
            )
            return

        confirm = messagebox.askyesno(
            "Confirmação", f"Deseja excluir o template '{name}'?"
        )
        if confirm:
            self.manager.delete_template(name)

            # Pegar próximo template ou padrão
            all_templates = self.manager.get_template_names()
            if all_templates:
                next_template = all_templates[0]
            else:
                next_template = "Geral / Template Padrão"

            self.original_name = next_template
            self.template_var.set(self.manager.meta.get_display_name(next_template))
            self.load_template(next_template)
            self.refresh_templates()

    def refresh_templates(self):
        self.template_names = self.manager.get_template_names()
        display_names = self.manager.get_display_names()
        self.dropdown.configure(values=display_names)

        if self.original_name in self.template_names:
            self.template_var.set(
                self.manager.meta.get_display_name(self.original_name)
            )

    def toggle_favorite(self):
        real = self.get_real_name()
        self.manager.meta.toggle_favorite(real)
        self.refresh_templates()

    def toggle_protected(self):
        real = self.get_real_name()
        if self.manager.meta.is_favorite(real):
            messagebox.showinfo(
                "Aviso", "Templates favoritos já são protegidos automaticamente."
            )
            return
        self.manager.meta.toggle_protected(real)
        self.refresh_templates()

    def show_autocomplete(self, event=None):
        placeholders = self.manager.extract_placeholders(
            self.content_box.get("1.0", "end")
        )
        all_ph = list(
            set(
                placeholders
                + self.get_placeholders()["fixed"]
                + self.get_placeholders()["dynamic"]
            )
        )
        sorted_ph = sorted(set(all_ph))

        popup = ctk.CTkToplevel(self)
        popup.transient(self)
        popup.grab_set()
        popup.geometry("+%d+%d" % (self.winfo_rootx() + 200, self.winfo_rooty() + 200))
        popup.overrideredirect(True)

        frame = ctk.CTkFrame(popup)
        frame.pack(padx=5, pady=5)

        for ph in sorted_ph:

            def insert(ph_inner=ph):
                self.content_box.insert("insert", f"${ph_inner}$")
                popup.destroy()

            btn = ctk.CTkButton(
                frame,
                text=f"${ph}$",
                width=180,
                height=26,
                font=ctk.CTkFont(size=11),
                command=insert,
            )
            btn.pack(pady=1, anchor="w")

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
        # Unregister from theme manager before destroying
        if hasattr(self, "theme_manager"):
            self.theme_manager.unregister_window(self)
        self.destroy()
