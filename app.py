# app.py
import customtkinter as ctk
import pyperclip
import json

from template_manager import TemplateManager
from template_editor import TemplateEditor
from quick_template_popup import QuickTemplatePopup
from theme_manager import ThemeManager
from field_entry import FieldEntry


class TemplateApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.theme = ThemeManager()
        self.title("Linx Fast 2.0")
        self.geometry("500x600")
        self.attributes("-topmost", False)

        self.manager = TemplateManager()
        self.has_copied = False
        self.entries = {}
        self.fixed_fields = [
            "Nome", "Problema Relatado", "CNPJ",
            "Telefone", "Email", "Protocolo", "Procedimento Executado"
        ]
        self.dynamic_fields = []

        self.current_template = "Template Padrão"
        self.current_template_display = ctk.StringVar(
            value=self.manager.meta.get_display_name(self.current_template)
        )

        self._build_interface()
        self.load_template_placeholders()

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(0, self.apply_saved_geometry)

    def _build_interface(self):
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(expand=True, fill="both", padx=10, pady=10)

        top_bar = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        top_bar.pack(fill="x", pady=(0, 8))

        self.pin_btn = ctk.CTkButton(top_bar, text="📌", width=30, command=self.toggle_pin)
        self.pin_btn.pack(side="left", padx=(0, 6))

        self.theme_btn = ctk.CTkButton(top_bar, text="🌓", width=30, command=self.theme.toggle_appearance)
        self.theme_btn.pack(side="right")

        self.template_selector = ctk.CTkOptionMenu(
            top_bar,
            variable=self.current_template_display,
            values=self.manager.get_display_names(),
            command=self.on_template_change,
            width=300
        )
        self.template_selector.pack(side="left", expand=True, padx=(10, 0))

        self.form_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.form_frame.pack(fill="both", expand=True)

        # Dentro de _build_interface(), depois de draw_all_fields()
        self.draw_all_fields()

        self.clear_btn = ctk.CTkButton(self.main_frame, text="🧽 Limpar Campos", width=120, command=self.clear_fields)
        self.clear_btn.pack(pady=(5, 5), anchor="w")

        bottom_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        bottom_frame.pack(fill="x", pady=(1, 0))

        ctk.CTkButton(bottom_frame, text="Copiar para Área de Transferência", command=self.copy_template).pack(fill="x", pady=5)
        ctk.CTkButton(bottom_frame, text="Visualizar Resultado", command=self.preview_template).pack(fill="x", pady=5)
        ctk.CTkButton(bottom_frame, text="Editar Templates", command=self.open_template_editor).pack(fill="x", pady=5)
        ctk.CTkButton(bottom_frame, text="Modo Rápido", command=self.open_quick_mode).pack(fill="x", pady=5)

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

            # 🧼 Reset de estado para evitar erro após trocar de template
            field_widget.entry.was_invalid = False
            field_widget.entry.configure(border_color=field_widget.entry.original_border_color)

            if field in old_values and old_values[field]:
                field_widget.entry.insert(0, old_values[field])
            else:
                field_widget.show_placeholder()  # ← Garantir placeholder se vazio


            self.entries[field] = field_widget

        self.after(100, self.adjust_window_height)

    def on_field_exit(self, field_entry):
        value = field_entry.get_value()

        if self.has_copied:
            if not value:
                if not field_entry.entry.was_invalid:
                    field_entry.mark_invalid()
            elif field_entry.entry.was_invalid:
                field_entry.mark_valid()
        else:
            if not value:
                field_entry.reset_border()



    def clear_fields(self):
        for field in self.entries.values():
            field.clear()

    def toggle_pin(self):
        pinned = not self.attributes("-topmost")
        self.attributes("-topmost", pinned)
        self.pin_btn.configure(text="📌" if pinned else "📍")

    def on_template_change(self, selected_display_name):
        real_name = self.manager.meta.get_real_name(selected_display_name)
        self.manager.load_templates()
        self.template_selector.configure(values=self.manager.get_display_names())
        self.current_template = real_name
        self.current_template_display.set(self.manager.meta.get_display_name(real_name))
        self.has_copied = False
        self.load_template_placeholders()
        self.draw_all_fields()  # ← agora sim!



    def load_template_placeholders(self):
        content = self.manager.get_template(self.current_template)
        placeholders = self.manager.extract_placeholders(content)
        self.dynamic_fields = [ph for ph in placeholders if ph not in self.fixed_fields]


    def copy_template(self):
        self.has_copied = True
        template = self.manager.get_template(self.current_template)
        for key, entry in self.entries.items():
            value = entry.get_value()
            if not value:
                entry.mark_invalid()
            template = template.replace(f"${key}$", value if value else "")
        pyperclip.copy(template)

    def preview_template(self):
        content = self.manager.get_template(self.current_template)
        for key, entry in self.entries.items():
            content = content.replace(f"${key}$", entry.get_value())

        popup = ctk.CTkToplevel(self)
        popup.title("Visualização")
        popup.geometry("600x400")
        popup.transient(self)
        popup.grab_set()

        text = ctk.CTkTextbox(popup)
        text.insert("1.0", content)
        text.configure(state="disabled")
        text.pack(expand=True, fill="both", padx=20, pady=20)

    def open_template_editor(self):
        def get_fields():
            return {"fixed": self.fixed_fields, "dynamic": self.dynamic_fields}
        TemplateEditor(self, self.manager, get_fields, current_template=self.current_template)

    def open_quick_mode(self):
        QuickTemplatePopup(self, self.manager)

    def adjust_window_height(self, extra_padding=60):
        self.update_idletasks()
        height = self.main_frame.winfo_reqheight()
        screen_h = self.winfo_screenheight()
        max_h = int(screen_h * 0.9)
        target_h = min(height + extra_padding, max_h)
        self.geometry(f"{self.winfo_width()}x{target_h}+{self.winfo_x()}+{self.winfo_y()}")

    def save_window_config(self):
        try:
            with open("config.json", "w", encoding="utf-8") as f:
                json.dump({"geometry": self.geometry()}, f)
        except:
            pass

    def apply_saved_geometry(self):
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                geometry = json.load(f).get("geometry")
                if geometry:
                    self.geometry(geometry)
        except:
            pass

    def on_close(self):
        self.save_window_config()
        self.destroy()


if __name__ == "__main__":
    app = TemplateApp()
    app.mainloop()
