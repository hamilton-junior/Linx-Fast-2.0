import customtkinter as ctk
import pyperclip
from field_entry import FieldEntry


class QuickTemplatePopup(ctk.CTkToplevel):
    def __init__(self, master, manager):
        super().__init__(master)
        self.title("Modo Rápido")
        self.geometry("500x600")
        self.transient(master)
        self.attributes("-topmost", False)

        self.manager = manager
        self.fixed_fields = [
            "Nome", "Problema Relatado", "CNPJ",
            "Telefone", "Email", "Protocolo", "Procedimento Executado"
        ]
        self.dynamic_fields = []
        self.entries = {}
        self.has_copied = False

        self.current_template = "Template Padrão"
        self.current_template_display = ctk.StringVar(value=self.manager.meta.get_display_name(self.current_template))

        self._build_interface()
        self.load_template_placeholders()

    def _build_interface(self):
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(expand=True, fill="both", padx=10, pady=10)

        top_bar = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        top_bar.pack(fill="x", pady=(0, 10))

        self.pin_btn = ctk.CTkButton(top_bar, text="📌", width=30, command=self.toggle_pin)
        self.pin_btn.pack(side="left")

        self.theme_btn = ctk.CTkButton(top_bar, text="🌓", width=30, command=self.toggle_theme)
        self.theme_btn.pack(side="right")

        self.template_selector = ctk.CTkOptionMenu(
            top_bar,
            variable=self.current_template_display,
            values=self.manager.get_display_names(),
            command=self.on_template_change,
            width=300
        )
        self.template_selector.pack(side="left", expand=True, padx=10)

        self.form_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.form_frame.pack(fill="both", expand=True)
        self.form_frame.grid_columnconfigure(0, weight=1)

        self.clear_btn = ctk.CTkButton(self.main_frame, text="🧽 Limpar Campos", width=120, command=self.clear_fields)
        self.clear_btn.pack(pady=(5, 5), anchor="w")

        self.bottom_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.bottom_frame.pack(fill="x", pady=(10, 0))

        ctk.CTkButton(self.bottom_frame, text="Copiar", command=self.copy_template).pack(fill="x", pady=5)
        ctk.CTkLabel(self.main_frame, text="By Hamilton Junior", font=ctk.CTkFont(size=10), text_color="gray").pack(pady=(8, 0))

    def draw_all_fields(self):
        old_values = {k: v.get_value() for k, v in self.entries.items()}

        for widget in self.form_frame.winfo_children():
            if isinstance(widget, FieldEntry):
                widget.destroy()

        self.entries.clear()

        all_fields = self.fixed_fields + self.dynamic_fields
        for field in all_fields:
            field_widget = FieldEntry(
                self.form_frame,
                label_text=field,
                on_focus_out_callback=self.on_field_exit
            )
            field_widget.pack(fill="x", pady=3)

            field_widget.entry.was_invalid = False
            field_widget.entry.configure(border_color=field_widget.entry.original_border_color)

            if field in old_values and old_values[field]:
                field_widget.entry.insert(0, old_values[field])
            else:
                field_widget.show_placeholder()

            self.entries[field] = field_widget

        self.after(100, self.adjust_window_height)

    def clear_fields(self):
        for field in self.entries.values():
            field.entry.delete(0, "end")
            field.entry.was_invalid = False
            field.show_placeholder()
            field.entry.configure(border_color=field.entry.original_border_color)

    def copy_template(self):
        template = self.manager.get_template(self.current_template)
        self.has_copied = True
        for field in self.entries.values():
            value = field.get_value()
            if not value:
                field.mark_invalid()
            template = template.replace(f"${field.placeholder}$", value if value else "")
        pyperclip.copy(template)

    def on_field_exit(self, field_entry):
        if self.has_copied:
            if not field_entry.get_value():
                field_entry.mark_invalid()
            elif field_entry.entry.was_invalid:
                field_entry.mark_valid()
        else:
            if not field_entry.get_value():
                field_entry.reset_border()
                field_entry.show_placeholder()

    def toggle_pin(self):
        pinned = not self.attributes("-topmost")
        self.attributes("-topmost", pinned)
        self.pin_btn.configure(text="📌" if pinned else "📍")

    def toggle_theme(self):
        mode = ctk.get_appearance_mode()
        ctk.set_appearance_mode("light" if mode == "Dark" else "dark")

    def on_template_change(self, selected_display_name):
        real_name = self.manager.meta.get_real_name(selected_display_name)
        self.manager.load_templates()
        self.template_selector.configure(values=self.manager.get_display_names())
        self.current_template = real_name
        self.current_template_display.set(self.manager.meta.get_display_name(real_name))
        self.has_copied = False
        self.load_template_placeholders()

    def load_template_placeholders(self):
        content = self.manager.get_template(self.current_template)
        placeholders = self.manager.extract_placeholders(content)
        self.dynamic_fields = [ph for ph in placeholders if ph not in self.fixed_fields]
        self.draw_all_fields()

    def adjust_window_height(self, extra_padding=50):
        self.update_idletasks()
        content_height = self.main_frame.winfo_reqheight()
        screen_height = self.winfo_screenheight()
        max_height = int(screen_height * 0.9)

        desired_height = content_height + extra_padding
        final_height = min(desired_height, max_height)

        width = self.winfo_width()
        x, y = self.winfo_x(), self.winfo_y()
        self.geometry(f"{width}x{final_height}+{x}+{y}")
    