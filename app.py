import customtkinter as ctk
import pyperclip
import json
import sys
import os
from template_editor import TemplateEditor
from template_manager import TemplateManager
from theme_manager import ThemeManager
from dpm import DailyPasswordManager
from customtkinter import CTkInputDialog

if sys.platform == "win32":
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # SYSTEM_AWARE
    except Exception as e:
        print(f"[DPI WARNING] Could not set DPI awareness: {e}")


class TemplateApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Linx Fast 2.0")
        self.geometry("360x535")
        self.visual_feedback_enabled = True


        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")

        #Inicialização das classes
        self.template_manager = TemplateManager()
        self.theme_manager = ThemeManager()
        self.password_manager = DailyPasswordManager()
        self.fixed_fields = [
            "Nome", "Problema Relatado", "CNPJ",
            "Telefone", "Email", "Protocolo", "Procedimento Executado"
        ]
        self.dynamic_fields = []
        self.entries = {}
        self.field_widgets = {}

        self.current_template = "Selecione o template..."
        self.current_template_display = ctk.StringVar(value=self.template_manager.meta.get_display_name(self.current_template))


        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_main_interface()
        self.load_template_placeholders()

        # Somente após layout real ser montado
        self.after(0, self.apply_saved_geometry)
        self.protocol("WM_DELETE_WINDOW", self.on_close)




    def _build_main_interface(self):
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.main_frame.grid_columnconfigure(0, weight=1)

        
        selector_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        selector_frame.grid(row=0, column=0, sticky="w", padx=5, pady=(5, 5))

        self.pin_button = ctk.CTkButton(
            selector_frame,
            text="📍",
            command=self.toggle_always_on_top,
            width=30
            )
        self.pin_button.pack(side="left", padx=(0, 5))
        
        self.template_selector = ctk.CTkOptionMenu(
            selector_frame,
            variable=self.current_template_display,
            values=self.template_manager.get_display_names(),
            command=self.on_template_change,
            width=300
        )
        self.template_selector.pack(side="left")

        self.form_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.form_frame.grid(row=1, column=0, sticky="nsew")
        self.form_frame.grid_columnconfigure(0, weight=1)

        self.draw_all_fields()
        
        # Botão de Senha Diária
        self.btn_daily_password = ctk.CTkButton(self.main_frame, text="PW", command=self.handle_daily_password, width=1, height=30,anchor="center")
        self.btn_daily_password.grid(sticky="w",row=2, column=0, padx=(5,0),pady=(5, 0))
        self.btn_daily_password.bind("<Button-3>", lambda e: (self.password_manager.set_today_password(None), self.show_snackbar("Senha diária resetada!", toast_type="info")))

        # Botão de Limpar Campos
        self.btn_limpar_campos = ctk.CTkButton(
            self.main_frame,
            text="❌",
            fg_color="#A94444",
            hover_color="#912F2F",
            anchor="right",
            width=1,
            height=30,
            command=self.limpar_campos
        )
        self.btn_limpar_campos.grid(row=2, column=0, pady=(5, 0), sticky="e")

        #Botão de Copiar Template
        ctk.CTkButton(self.main_frame, text="Copiar para área de transferência",
                        fg_color="#7E57C2", hover_color="#6A4BB3",
                        command=self.copy_template).grid(row=2, column=0, pady=(5, 5))
        #Botão de Visualizar Template
        ctk.CTkButton(self.main_frame, text="Visualizar Resultado",
                        fg_color="#5E35B1", hover_color="#512DA8",
                        command=self.preview_template).grid(row=3, column=0, pady=(5, 5))
        #Botão de Editar Template
        ctk.CTkButton(self.main_frame, text="Editar Templates",
                        fg_color="#7E57C2", hover_color="#6A4BB3",
                        command=self.open_template_editor).grid(row=4, column=0, pady=(5, 5))
        #Botão de Adicionar Campo
        self.add_btn = ctk.CTkButton(self.main_frame, text="+ Adicionar Campo", width=150, height=30,
                        command=self.prompt_new_field,
                        fg_color="#333", hover_color="#444", font=ctk.CTkFont(size=12))
        self.add_btn.grid(row=5, column=0, pady=(5, 2))
        #Botão de Modo Simples
        ctk.CTkButton(self.main_frame, text="Modo Simples",
                        fg_color="#5E35B1", hover_color="#4527A0",
                        command=self.open_quick_mode).grid(row=6, column=0, pady=(5, 5))


    def draw_all_fields(self):
        old_values = {k: v.get() for k, v in self.entries.items()}

        for widget in self.form_frame.winfo_children():
            widget.destroy()
        self.entries.clear()
        self.field_widgets.clear()

        row = 0
        for field in self.fixed_fields:
            self._draw_field(field, row, old_values.get(field, ""), is_dynamic=False)
            row += 1
        for field in self.dynamic_fields:
            self._draw_field(field, row, old_values.get(field, ""), is_dynamic=True)
            row += 1
            
        self.after(100, self.adjust_window_height)


    def _should_wrap_label(self, text):
        return len(text) > 15 and " " in text

    def _draw_field(self, name, row, value="", is_dynamic=True):
            row_frame = ctk.CTkFrame(self.form_frame, fg_color="transparent")
            row_frame.grid(row=row, column=0, sticky="ew", padx=10, pady=4)
            row_frame.grid_columnconfigure(1, weight=1)  # Apenas a entrada expande

            label = ctk.CTkLabel(
                row_frame,
                text=name,
                anchor="w",
                justify="left",
                width=160  # largura fixa para alinhamento
            )
            label.grid(row=0, column=0, sticky="w", padx=(0, 5))

            entry = ctk.CTkEntry(row_frame, placeholder_text=f"{name}")
            if value not in (None, ""):
                entry.insert(0, value)
            entry.grid(row=0, column=1, sticky="ew")
            self.entries[name] = entry
            entry.original_border_color = entry.cget("border_color")  # salvar cor original

            if is_dynamic:
                btn_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
                btn_frame.grid(row=0, column=2, sticky="e", padx=(5, 0))

                up_btn = ctk.CTkButton(btn_frame, text="↑", width=30, command=lambda: self.move_field(name, -1))
                down_btn = ctk.CTkButton(btn_frame, text="↓", width=30, command=lambda: self.move_field(name, 1))
                del_btn = ctk.CTkButton(btn_frame, text="✕", width=30, fg_color="#A94444",
                                        command=lambda: self.remove_field(name))

                up_btn.pack(side="left", padx=2)
                down_btn.pack(side="left", padx=2)
                del_btn.pack(side="left", padx=2)

    def move_field(self, field, direction):
        idx = self.dynamic_fields.index(field)
        new_idx = idx + direction
        if 0 <= new_idx < len(self.dynamic_fields):
            self.dynamic_fields[idx], self.dynamic_fields[new_idx] = self.dynamic_fields[new_idx], self.dynamic_fields[idx]
            self.draw_all_fields()

    def remove_field(self, field):
        if field in self.dynamic_fields:
            self.dynamic_fields.remove(field)
            self.draw_all_fields()

    def prompt_new_field(self):
        popup = CTkInputDialog(text="Nome do novo campo (placeholder):", title="Adicionar Campo")
        field_name = popup.get_input()
        if field_name and field_name not in self.entries:
            self.dynamic_fields.append(field_name)
            self.draw_all_fields()

    def focus_next_field(self, current_name):
        keys = list(self.entries.keys())
        try:
            idx = keys.index(current_name)
            next_key = keys[idx + 1]
            self.entries[next_key].focus()
        except (ValueError, IndexError):
            pass

    def toggle_always_on_top(self):
        current = self.attributes("-topmost")
        new_state = not current
        self.attributes("-topmost", new_state)
        self.pin_button.configure(fg_color="green" if new_state else self.theme_manager.get_theme_default_color(ctk.CTkButton, "fg_color"))
        self.pin_button.configure(text="📌" if new_state else "📍")
        if new_state:
            self.show_snackbar("PIN ativado!", toast_type="info")
        else:
            self.show_snackbar("PIN desativado!", toast_type="info")

    def copy_template(self):
        template = self.template_manager.get_template(self.current_template)
        tem_vazios = False

        for key, entry in self.entries.items():
            value = entry.get()
            if not value:
                entry.configure(border_color="red")
                entry.bind("<FocusIn>", lambda e, ent=entry: ent.configure(border_color=ent.original_border_color))
                entry.bind("<FocusOut>", lambda e, ent=entry: self.animate_field_success(ent) if ent.get() else None)

                tem_vazios = True
            template = template.replace(f"${key}$", value if value else "")

        pyperclip.copy(template)
        self.pulse_window()
        self.show_snackbar("Copiado com sucesso!", toast_type="success")

        if tem_vazios:
            self.show_snackbar("Existem campos em branco!", toast_type="warning")


    def preview_template(self):
        template = self.template_manager.get_template(self.current_template)
        for key, entry in self.entries.items():
            value = entry.get()
            template = template.replace(f"${key}$", value if value else "")

        preview = ctk.CTkToplevel(self)
        preview.title("Visualização do Template")
        preview.geometry("600x400")
        preview.transient(self)
        preview.grab_set()

        box = ctk.CTkTextbox(preview, wrap="word")
        box.insert("1.0", template)
        box.configure(state="disabled")
        box.pack(expand=True, fill="both", padx=20, pady=20)

    def load_template_placeholders(self):
            template_content = self.template_manager.get_template(self.current_template)
            placeholders = self.template_manager.extract_placeholders(template_content)

            # SALVAR VALORES EXISTENTES
            old_values = {k: v.get() for k, v in self.entries.items()}

            # REDEFINIR CAMPOS DINÂMICOS com base no novo template
            self.dynamic_fields = [ph for ph in placeholders if ph not in self.fixed_fields]

            # RECONSTRUIR OS CAMPOS
            self.draw_all_fields()
            # RESTAURAR APENAS VALORES NÃO NULOS/NÃO VAZIOS
            for k in self.entries:
                valor_antigo = old_values.get(k, None)
                if valor_antigo not in (None, ""):
                    self.entries[k].delete(0, "end")
                    self.entries[k].insert(0, valor_antigo)
            # Se não houver valor antigo, deixa vazio para mostrar o placeholder

    def open_template_editor(self):
        def get_fields():
            return {
                "fixed": self.fixed_fields,
                "dynamic": sorted(self.dynamic_fields)
            }

        TemplateEditor(self, self.template_manager, get_fields, current_template=self.current_template)
        
    def open_quick_mode(self):
        from quick_template_popup import QuickTemplatePopup
        QuickTemplatePopup(self, self.template_manager)

    def handle_daily_password(self):
        if senha := self.password_manager.get_today_password():
            try:
                pyperclip.copy(senha)
                self.show_snackbar("Senha diária copiada!")
            except Exception:
                self.show_snackbar("Falha ao copiar senha para a área de transferência!", toast_type="error")
        else:
            dialog = CTkInputDialog(title="Senha Diária", text="Informe a senha de hoje:")
            if senha_input := dialog.get_input():
                self.password_manager.set_today_password(senha_input)
                pyperclip.copy(senha_input)
                self.show_snackbar("Senha diária salva e copiada!")

    def on_template_change(self, selected_display_name):
        real_name = self.template_manager.meta.get_real_name(selected_display_name)

        # Sempre recarrega lista atualizada
        self.template_manager.load_templates()
        self.template_selector.configure(values=self.template_manager.get_display_names())

        self.current_template = real_name
        self.current_template_display.set(self.template_manager.meta.get_display_name(real_name))
        self.load_template_placeholders()

    def adjust_window_height(self):
        self.update_idletasks()

        # Altura real do conteúdo do formulário
        form_height = self.form_frame.winfo_reqheight()  # ← usa o tamanho *requisitado*
        extra_height = 250

        screen_height = self.winfo_screenheight()
        max_height = int(screen_height * 0.9)

        desired_height = form_height + extra_height
        new_height = min(desired_height, max_height)

        # Largura atual (fallback se necessário)
        width = self.winfo_width()
        if width <= 10:
            width = 500  # valor padrão inicial

        # Mantém a posição atual
        x = self.winfo_x()
        y = self.winfo_y()

        # Garante altura mínima para evitar efeitos indesejados
        min_height = 415
        final_height = max(new_height, min_height)

        self.animate_resize_to(final_height, on_complete=self.save_window_config)


    def animate_resize_to(self, target_height, step=10, delay=10, on_complete=None):
        self.update_idletasks()

        current_width = self.winfo_width()
        if current_width < 350:
            current_width = 350  # largura mínima

        current_height = self.winfo_height()
        x, y = self.winfo_x(), self.winfo_y()

        if current_height <= 1:
            self.geometry(f"{current_width}x{target_height}+{x}+{y}")
            if on_complete:
                self.after(10, on_complete)
            return

        if abs(target_height - current_height) <= step:
            self.geometry(f"{current_width}x{target_height}+{x}+{y}")
            if on_complete:
                self.after(10, on_complete)
            return

        direction = 1 if target_height > current_height else -1
        new_height = current_height + (step * direction)
        self.geometry(f"{current_width}x{new_height}+{x}+{y}")

        self.after(delay, lambda: self.animate_resize_to(target_height, step, delay, on_complete))

    def limpar_campos(self):
        for name, entry in self.entries.items():
            entry.delete(0, "end")
            entry.insert(0, "")
            entry.configure(placeholder_text=name)
            entry.configure(border_color=entry.original_border_color)

        self.show_snackbar("Campos limpos!", toast_type="info")


    def pulse_window(self, times=5, offset=3, delay=5):
        x, y = self.winfo_x(), self.winfo_y()
        def animate(count):
            if count == 0:
                self.geometry(f"+{x}+{y}")
                return
            dx = offset if count % 2 == 0 else -offset
            self.geometry(f"+{x + dx}+{y}")
            self.after(delay, lambda: animate(count - 1))
        animate(times)

    def show_snackbar(self, message="Copiado com sucesso!", duration=1500, toast_type="success"):
        styles = {
            "success": {"fg": "#388E3C", "icon": "✔"},
            "error": {"fg": "#D32F2F", "icon": "✖"},
            "warning": {"fg": "#FBC02D", "icon": "⚠"},
            "info": {"fg": "#1976D2", "icon": "ℹ"},
            "default": {"fg": "#AE00FF", "icon": "•"},
        }

        style = styles.get(toast_type, styles["default"])
        text = f"{style['icon']} {message}"

        # Cria a janela flutuante
        snackbar = ctk.CTkToplevel(self)
        snackbar.overrideredirect(True)
        snackbar.attributes("-topmost", True)
        snackbar.configure(fg_color=style["fg"])

        label = ctk.CTkLabel(snackbar, text=text, text_color="white", font=ctk.CTkFont(size=12), padx=15, pady=8)
        label.pack()

        self.update_idletasks()
        width = snackbar.winfo_reqwidth()
        height = snackbar.winfo_reqheight()
        x = self.winfo_x() + int((self.winfo_width() - width) / 2)
        y = self.winfo_y() + self.winfo_height() - height - 20

        snackbar.geometry(f"{width}x{height}+{x}+{y}")
        snackbar.attributes("-alpha", 0)

        # Fade in
        def fade_in(opacity=0.0):
            if opacity >= 1.0:
                snackbar.attributes("-alpha", 1.0)
            else:
                snackbar.attributes("-alpha", opacity)
                self.after(20, lambda: fade_in(opacity + 0.1))

        fade_in()

        # Desaparecer com fade out
        def fade_out(opacity=1.0):
            if opacity <= 0:
                snackbar.destroy()
            else:
                snackbar.attributes("-alpha", opacity)
                self.after(30, lambda: fade_out(opacity - 0.1))

        self.after(duration, lambda: fade_out())

    def animate_field_success(self, entry):
        if self.visual_feedback_enabled:    
            entry.configure(border_color="#00C853")  # verde sucesso

            # Pulse: aumentar e voltar o tamanho da fonte levemente
            def pulse(step=0):
                size = 12 + (1 if step % 2 == 0 else 0)
                entry.configure(font=ctk.CTkFont(size=size))
                if step < 4:
                    self.after(100, lambda: pulse(step + 1))
                else:
                    entry.configure(font=ctk.CTkFont(size=12))
                    entry.configure(border_color=entry.original_border_color)

            pulse()

    def pulse_button_success(self, button, original_color="#7E57C2", success_color="#00C853"):
        # Salva a cor original
        button.configure(fg_color=success_color)

        def restore():
            button.configure(fg_color=original_color)

        self.after(500, restore)


    def save_window_config(self):
        self.update_idletasks()
        width, height = self.winfo_width(), self.winfo_height()

        if height >= 300:
            geometry_str = self.geometry()

            try:
                # Carrega o config existente, se houver
                if os.path.exists("config.json"):
                    with open("config.json", "r", encoding="utf-8") as f:
                        config = json.load(f)
                else:
                    config = {}

                # Atualiza a geometria
                config["geometry"] = geometry_str

                # Salva o arquivo atualizado
                with open("config.json", "w", encoding="utf-8") as f:
                    json.dump(config, f)

            except Exception as e:
                print(f"[ERRO ao salvar config]: {e}")


    def load_window_config(self):
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
                geometry = config.get("geometry")
                if geometry and "x" in geometry:
                    self.geometry(geometry)
        except Exception:
            pass

    def apply_saved_geometry(self):
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
                geometry = config.get("geometry")
                if geometry and "x" in geometry:
                    self.geometry(geometry)
        except Exception:
            pass



    def on_close(self):
        self.update_idletasks()  # Garante que a geometria seja a real
        self.save_window_config()
        self.destroy()

if __name__ == "__main__":
    app = TemplateApp()
    app.mainloop()
