import customtkinter as ctk
import tkinter as tk
import os
import logging
from logger_config import auto_log_functions

# Get the module logger
logger = logging.getLogger(__name__)


@auto_log_functions
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
        try:
            widget_name = widget_class.__name__
            color = ctk.ThemeManager.theme[widget_name][property_name]

            current_mode = self.get_current_appearance()
            if isinstance(color, (list, tuple)):
                return color[0] if current_mode.lower() == "dark" else color[1]
            return color
        except (KeyError, IndexError):
            return "#FF0000"  # Cor de fallback (vermelho)

    def get_lighter_color(self, color_hex, factor=0.2):
        """Retorna uma versão mais clara da cor hexadecimal fornecida."""
        # Remove o # se existir
        color_hex = color_hex.lstrip("#")

        # Converte para RGB
        r = int(color_hex[:2], 16)
        g = int(color_hex[2:4], 16)
        b = int(color_hex[4:], 16)

        # Torna mais claro
        r = min(255, int(r + (255 - r) * factor))
        g = min(255, int(g + (255 - g) * factor))
        b = min(255, int(b + (255 - b) * factor))

        # Converte de volta para hex
        return f"#{r:02x}{g:02x}{b:02x}"

    def get_darker_color(self, color_hex, factor=0.2):
        """Retorna uma versão mais escura da cor hexadecimal fornecida."""
        # Remove o # se existir
        color_hex = color_hex.lstrip("#")

        # Converte para RGB
        r = int(color_hex[:2], 16)
        g = int(color_hex[2:4], 16)
        b = int(color_hex[4:], 16)

        # Torna mais escuro
        r = int(r * (1 - factor))
        g = int(g * (1 - factor))
        b = int(b * (1 - factor))

        # Converte de volta para hex
        return f"#{r:02x}{g:02x}{b:02x}"
