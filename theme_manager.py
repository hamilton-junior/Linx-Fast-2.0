import customtkinter as ctk
import tkinter as tk
import os

class ThemeManager:
    def __init__(self, theme_name="green", mode="dark"):
        self.theme_name = theme_name
        self.mode = mode

        self.themes_dir = "themes"
        os.makedirs(self.themes_dir, exist_ok=True)

        # Apenas define o tema de cor ao iniciar, não altera o modo de aparência global!
        self.set_theme(self.theme_name)
        # NÃO chama set_appearance_mode aqui!

    def set_theme(self, theme_name):
        theme_path = os.path.join(self.themes_dir, f"{theme_name}.json")
        if os.path.exists(theme_path):
            ctk.set_default_color_theme(theme_path)
        else:
            ctk.set_default_color_theme(theme_name)
        self.theme_name = theme_name

    def set_appearance_mode(self, mode):
        # Só altera o modo global se explicitamente chamado
        ctk.set_appearance_mode(mode)
        self.mode = mode

    def toggle_appearance(self):
        self.mode = "dark" if self.mode == "light" else "light"
        self.set_appearance_mode(self.mode)

    def get_current_appearance(self):
        return self.mode

    def get_theme_default_color(self, widget_class, property_name):
        """Retorna a cor padrão do tema para a propriedade informada de um widget."""
        root = tk.Tk()
        root.withdraw()

        temp = widget_class(root)
        try:
            color = temp.cget(property_name)
        except AttributeError:
            # Se a propriedade não existir, retorna uma cor padrão
            color = "red"
        finally:
            temp.destroy()
            root.destroy()

        if isinstance(color, (list, tuple)):
            return color[0]
        return color