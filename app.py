from main_window import TemplateApp
from main_window import placeholder_engine


if __name__ == "__main__":
    app = TemplateApp()
    app.mainloop()




    def draw_all_fields(self):
        # Salva valores antigos, tanto de Entry quanto de Textbox
        old_values = {}
        for k, v in self.entries.items():
            try:
                old_values[k] = v.get()
            except Exception:
                try:
                    old_values[k] = v.get("1.0", "end-1c")
                except Exception:
                    old_values[k] = ""

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

        self._safe_after(100, self.adjust_window_height)

    def save_field_order(self):
        """Salva a ordem dos campos dinâmicos do template atual no arquivo config.json."""
        try:
            if os.path.exists("config.json"):
                with open("config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
            else:
                config = {}

            if "field_orders" not in config:
                config["field_orders"] = {}

            config["field_orders"][self.current_template] = self.dynamic_fields

            with open("config.json", "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            print(f"[ERRO ao salvar ordem dos campos]: {e}")

    def load_field_order(self):
        """Carrega a ordem dos campos dinâmicos do template atual, se existir."""
        try:
            if os.path.exists("config.json"):
                with open("config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
                field_orders = config.get("field_orders", {})
                order = field_orders.get(self.current_template)
                if order:
                    # Garante que só mantenha campos realmente presentes no template
                    self.dynamic_fields = [f for f in order if f in self.dynamic_fields] + [f for f in self.dynamic_fields if f not in order]
        except Exception as e:
            print(f"[ERRO ao carregar ordem dos campos]: {e}")



    def move_field(self, field, direction):
            idx = self.dynamic_fields.index(field)
            new_idx = idx + direction
            if 0 <= new_idx < len(self.dynamic_fields):
                self.dynamic_fields[idx], self.dynamic_fields[new_idx] = self.dynamic_fields[new_idx], self.dynamic_fields[idx]
                self.draw_all_fields()
                self.save_field_order()

    def remove_field(self, field):
        if field in self.dynamic_fields:
            self.dynamic_fields.remove(field)
            self.draw_all_fields()
            self.save_field_order()

    def prompt_new_field(self):
        popup = CTkInputDialog(text="Nome do novo campo (placeholder):", title="Adicionar Campo")
        field_name = popup.get_input()
        if field_name and field_name not in self.entries:
            self.dynamic_fields.append(field_name)
            self.draw_all_fields()
            self.save_field_order()

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
        # Validate if a template is selected
        if not self.current_template or self.current_template == "Selecione o template...":
            self.show_snackbar("Selecione um template antes de copiar!", toast_type="error")
            return

        template = self.template_manager.get_template(self.current_template)
        tem_vazios = False

        # Descobre quais campos realmente estão no template atual
        placeholders = set(self.template_manager.extract_placeholders(template))

        # Também inclui campos usados em condicionais ($Campo?Texto|Alternativa$)
        import re
        cond_fields = set()
        for match in re.findall(r"\$([a-zA-Z0-9 _\-çÇáéíóúãõâêîôûÀ-ÿ\[\]%:/]+)\?", template):
            cond_fields.add(match.strip())

        all_fields = placeholders | cond_fields

        # Filtra apenas os campos presentes no template e que estão na interface
        fields_to_validate = [k for k in self.entries if k in all_fields]

        # 1. Coleta valores dos campos
        field_values = {}
        for key in fields_to_validate:
            entry = self.entries[key]
            if not entry.winfo_exists():
                continue
            # Campos inteligentes
            if isinstance(entry, ctk.CTkCheckBox):
                value = "Sim" if entry.get() else "Não"
            elif isinstance(entry, ctk.CTkSwitch):
                value = str(entry.get())
            elif isinstance(entry, ctk.StringVar):
                value = str(entry.get())
            elif isinstance(entry, ctk.CTkTextbox):
                value = entry.get("1.0", "end-1c")
            else:
                value = str(entry.get())
            field_values[key] = value
            if not value or value == "Não":
                if hasattr(entry, "configure"):
                    entry.configure(border_color="red")
                    entry.border_color = "red"
                    entry.bind("<FocusIn>", lambda e, ent=entry: ent.configure(border_color=ent.original_border_color))
                    entry.bind(
                        "<FocusOut>",
                        lambda e, ent=entry: self.animate_field_success(ent)
                        if (ent.get("1.0", "end-1c") if isinstance(ent, ctk.CTkTextbox) else ent.get())
                        else None
                    )
                tem_vazios = True

        # 2. Processa lógica condicional no template
        template = self.process_conditionals(template, field_values)

        # 3. Substitui placeholders simples
        for key, value in field_values.items():
            template = template.replace(f"${key}$", value if value else "")

        # 4. Substitui placeholders dinâmicos
        template = placeholder_engine.process(template)

        pyperclip.copy(template)
        self.pulse_window()
        if not tem_vazios:
            self.show_snackbar("Copiado com sucesso!", toast_type="success")
        else:
            self.show_snackbar("Existem campos em branco!", toast_type="warning")



    def preview_template(self):
        template = self.template_manager.get_template(self.current_template)
        # Coleta valores dos campos
        field_values = {}
        for key, entry in self.entries.items():
            if isinstance(entry, ctk.CTkCheckBox):
                value = "Sim" if entry.get() else "Não"
            elif isinstance(entry, ctk.CTkSwitch):
                value = str(entry.get())
            elif isinstance(entry, ctk.StringVar):
                value = str(entry.get())
            elif isinstance(entry, ctk.CTkTextbox):
                value = entry.get("1.0", "end-1c")
            else:
                value = str(entry.get())
            field_values[key] = value
        # Processa lógica condicional
        template = self.process_conditionals(template, field_values)
        # Substitui placeholders simples
        for key, value in field_values.items():
            template = template.replace(f"${key}$", value if value else "")
        # Substitui placeholders dinâmicos
        template = placeholder_engine.process(template)

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

        # SALVAR VALORES EXISTENTES (Entry ou Textbox)
        old_values = {}
        for k, v in self.entries.items():
            if isinstance(v, ctk.CTkTextbox):
                old_values[k] = v.get("1.0", "end-1c")
            else:
                old_values[k] = v.get()

        # Filtra placeholders automáticos (handlers do PlaceholderEngine)
        automatic_placeholders = set(placeholder_engine.handlers.keys())
        # Também filtra placeholders do tipo $Agora[...]$
        def is_automatic(ph):
            if ph in automatic_placeholders:
                return True
            if ph == "Agora":
                return True
            if ph.startswith("Agora[") and ph.endswith("]"):
                return True
            return False
        # REDEFINIR CAMPOS DINÂMICOS com base no novo template
        # Também inclui campos usados em condicionais
        import re
        cond_fields = set()
        for match in re.findall(r"\$([a-zA-Z0-9 _\-çÇáéíóúãõâêîôûÀ-ÿ\[\]%:/]+)\?", template_content):
            cond_fields.add(match.strip())

        all_fields = set(placeholders) | cond_fields

        self.dynamic_fields = [
            ph for ph in all_fields
            if ph not in self.fixed_fields and not is_automatic(ph)
        ]

        # Carrega ordem persistida, se houver
        if hasattr(self, "load_field_order") and callable(self.load_field_order):
            self.load_field_order()

        # RECONSTRUIR OS CAMPOS
        self.draw_all_fields()
        # RESTAURAR APENAS VALORES NÃO NULOS/NÃO VAZIOS
        for k in self.entries:
            valor_antigo = old_values.get(k, None)
            entry = self.entries[k]
            if valor_antigo not in (None, ""):
                if isinstance(entry, ctk.CTkTextbox):
                    entry.delete("1.0", "end")
                    entry.insert("1.0", valor_antigo)
                else:
                    entry.delete(0, "end")
                    entry.insert(0, valor_antigo)
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
        # Calcula altura do label de crédito
        author_label_height = 0
        for widget in self.main_frame.grid_slaves(row=100, column=0):
            author_label_height = widget.winfo_reqheight()
            break
        extra_height = 250 + author_label_height

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


    def animate_resize_to(self, target_height, step=25, delay=10, on_complete=None):
        self.update_idletasks()

        current_width = self._get_current_width()
        current_height = self.winfo_height()
        x, y = self.winfo_x(), self.winfo_y()

        geometry_str = self._get_geometry_str(current_width, target_height, x, y)
        abs_diff = abs(target_height - current_height)
        direction = self._get_direction(target_height, current_height)
        new_height = self._get_new_height(current_height, step, direction)
        new_geometry_str = self._get_geometry_str(current_width, new_height, x, y)

        if self._should_set_final_height(current_height):
            self._set_final_geometry(geometry_str, on_complete)
            return

        if self._should_snap_to_target(abs_diff, step):
            self._set_final_geometry(geometry_str, on_complete)
            return

        self.geometry(new_geometry_str)
        self._safe_after(delay, lambda: self.animate_resize_to(target_height, step, delay, on_complete))

    def limpar_campos(self):
        for name, entry in self.entries.items():
            if isinstance(entry, ctk.CTkTextbox):
                entry.delete("1.0", "end")
                entry.insert("1.0", "")
                entry.configure(border_color=entry.original_border_color)
            else:
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
            self._safe_after(delay, lambda: animate(count - 1))
        animate(times)

    def show_snackbar(self, message="Copiado com sucesso!", duration=1500, toast_type="success"):
        styles = {
            "success": {"fg": "#388E3C", "icon": "✔"},
            "error": {"fg": "#D32F2F", "icon": "✖"},
            "warning": {"fg": "#D4A326", "icon": "⚠"},
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
                self._safe_after(20, lambda: fade_in(opacity + 0.1))

        fade_in()

        # Desaparecer com fade out
        def fade_out(opacity=1.0):
            if opacity <= 0:
                snackbar.destroy()
            else:
                snackbar.attributes("-alpha", opacity)
                self._safe_after(30, lambda: fade_out(opacity - 0.1))

        self._safe_after(duration, lambda: fade_out())

    def process_conditionals(self, template, field_values):
        """
        Substitui todos os padrões $Campo?Texto|Alternativa$ no template.
        Se o campo estiver preenchido, usa Texto (pode conter outros placeholders).
        Se não, usa Alternativa (pode conter outros placeholders).
        """
        import re

        def cond_replacer(match):
            field = match.group(1)
            if "?" in field and "|" in field:
                # Suporte a aninhamento acidental, pega só o primeiro ?
                field_name, rest = field.split("?", 1)
                if "|" in rest:
                    text_true, text_false = rest.split("|", 1)
                else:
                    text_true, text_false = rest, ""
                value = field_values.get(field_name, "")
                # Se for checkbox, só considera "Sim" como verdadeiro
                if field_name.startswith("[checkbox]"):
                    is_true = value == "Sim"
                else:
                    is_true = bool(value)
                # Recursivo: processa condicional dentro de Texto/Alternativa
                if is_true:
                    return self.process_conditionals(text_true, field_values)
                else:
                    return self.process_conditionals(text_false, field_values)
            return match.group(0)

        # Regex: $Campo?Texto|Alternativa$
        return re.sub(r"\$([a-zA-Z0-9 _\-çÇáéíóúãõâêîôûÀ-ÿ\[\]%:/\?\|]+)\$", cond_replacer, template)


    def create_tooltip(self, widget, text, fg_color="#222", text_color="#fff"):
        """
        Attach a custom tooltip to a widget. The tooltip appears on hover and disappears on leave.

        Args:
            widget: The widget to attach the tooltip to.
            text (str): The text to display in the tooltip.
            fg_color (str, optional): Background color of the tooltip. Defaults to "#222".
            text_color (str, optional): Text color of the tooltip. Defaults to "#fff".
        """
        tooltip = {"window": None}

        def show_tooltip(event=None):
            # Always destroy any previous tooltip before showing a new one
            hide_tooltip()
            if tooltip["window"] is not None:
                return
            tooltip["window"] = tw = ctk.CTkToplevel(widget)
            tw.overrideredirect(True)
            tw.attributes("-topmost", True)
            label = ctk.CTkLabel(
                tw,
                text=text,
                font=ctk.CTkFont(size=11),
                text_color=text_color,
                fg_color=fg_color,
                padx=7, pady=3
            )
            label.pack()
            widget.update_idletasks()
            x = widget.winfo_rootx() + widget.winfo_width() + 7
            y = widget.winfo_rooty() - 3
            tw.geometry(f"+{x}+{y}")

        def hide_tooltip(event=None):
            if tooltip["window"] is not None:
                try:
                    tooltip["window"].destroy()
                except Exception:
                    pass
                tooltip["window"] = None

        def force_hide_tooltip(event=None):
            # Força o fechamento do tooltip em qualquer situação
            hide_tooltip()
            widget.after(1, hide_tooltip)

        widget.bind("<Enter>", show_tooltip)
        widget.bind("<Leave>", force_hide_tooltip)
        widget.bind("<ButtonPress>", force_hide_tooltip)
        widget.bind("<FocusOut>", force_hide_tooltip)
        widget.bind("<Destroy>", force_hide_tooltip)


    def animate_field_success(self, entry):
        if self.visual_feedback_enabled:    
            entry.configure(border_color="#00C853")  # verde sucesso

            # Pulse: aumentar e voltar o tamanho da fonte levemente
            def pulse(step=0):
                size = 12 + (1 if step % 2 == 0 else 0)
                entry.configure(font=ctk.CTkFont(size=size))
                if step < 4:
                    self._safe_after(100, lambda: pulse(step + 1))
                else:
                    entry.configure(font=ctk.CTkFont(size=12))
                    entry.configure(border_color=entry.original_border_color)

            pulse()

    def pulse_button_success(self, button, original_color="#7E57C2", success_color="#00C853"):
        # Salva a cor original
        button.configure(fg_color=success_color)

        def restore():
            button.configure(fg_color=original_color)

        self._safe_after(500, restore)


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
        self._cancel_all_afters()
        self.update_idletasks()  # Garante que a geometria seja a real
        self.save_window_config()
        self.destroy()

    # --- Configuração de campos expansíveis ---
    def load_expandable_fields_config(self):
        import json
        if os.path.exists("config.json"):
            try:
                with open("config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
                return config.get("expandable_fields", ["Procedimento Executado", "Problema Relatado"])
            except Exception:
                return ["Procedimento Executado", "Problema Relatado"]
        return ["Procedimento Executado", "Problema Relatado"]

    def save_expandable_fields_config(self):
        import json
        config = {}
        if os.path.exists("config.json"):
            try:
                with open("config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
            except Exception:
                config = {}
        config["expandable_fields"] = self.expandable_fields
        with open("config.json", "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)

    def open_settings(self):
        # Permite apenas uma janela de configurações por vez
        if hasattr(self, "_settings_window") and self._settings_window is not None:
            try:
                self._settings_window.focus()
                self._settings_window.lift()
                return
            except Exception:
                self._settings_window = None  # Se a janela foi fechada manualmente

        self._settings_window = SettingsWindow(self)
        # Quando a janela for fechada, remove a referência
        def on_close_settings():
            win = self._settings_window
            self._settings_window = None
            if win is not None:
                win.destroy()
        self._settings_window.protocol("WM_DELETE_WINDOW", on_close_settings)

    def reload_theme_and_interface(self):
        # 1. Salva o estado atual
        state = {
            "current_template": self.current_template,
            "current_template_display": self.current_template_display.get(),
            "dynamic_fields": list(self.dynamic_fields),
            "fixed_field_modes": dict(self.fixed_field_modes),
            "expandable_fields": list(self.expandable_fields),
            "field_values": {},
        }
        for k, v in self.entries.items():
            try:
                state["field_values"][k] = v.get()
            except Exception:
                try:
                    state["field_values"][k] = v.get("1.0", "end-1c")
                except Exception:
                    state["field_values"][k] = ""

        # 2. Destroi widgets principais
        for widget in self.winfo_children():
            widget.destroy()

        # 3. Recria interface
        self._build_main_interface()
        # 4. Restaura estado
        self.current_template = state["current_template"]
        self.current_template_display.set(state["current_template_display"])
        self.dynamic_fields = state["dynamic_fields"]
        self.fixed_field_modes = state["fixed_field_modes"]
        self.expandable_fields = state["expandable_fields"]
        self.load_template_placeholders()
        # 5. Restaura valores dos campos
        for k in self.entries:
            valor_antigo = state["field_values"].get(k, None)
            entry = self.entries[k]
            if valor_antigo not in (None, ""):
                if isinstance(entry, ctk.CTkTextbox):
                    entry.delete("1.0", "end")
                    entry.insert("1.0", valor_antigo)
                else:
                    entry.delete(0, "end")
                    entry.insert(0, valor_antigo)
    def load_theme_config(self):
        import json
        if os.path.exists("config.json"):
            try:
                with open("config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
                theme = config.get("theme_name", "green")
                mode = config.get("appearance_mode", "dark")
                return theme, mode
            except Exception:
                return "green", "dark"
        return "green", "dark"

    def save_theme_config(self, theme_name, appearance_mode):
        import json
        config = {}
        if os.path.exists("config.json"):
            try:
                with open("config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
            except Exception:
                config = {}
        config["theme_name"] = theme_name
        config["appearance_mode"] = appearance_mode
        with open("config.json", "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)