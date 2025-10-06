import customtkinter as ctk
import logging

logger = logging.getLogger(__name__)


def init_textbox_methods(cls):

    def _apply_field_color(self, widget, field_name, animate=True, value=None):
        """Aplica a cor correta ao campo com animação opcional"""
        default_border = self.theme_manager.get_theme_default_color(
            ctk.CTkEntry, "border_color"
        )

        # Obtém o valor se não foi fornecido
        if value is None:
            if isinstance(widget, ctk.CTkTextbox):
                value = widget.get("1.0", "end-1c").strip()
            elif isinstance(widget, ctk.CTkEntry):
                value = widget.get().strip()
            else:
                value = ""

        # Decide a cor baseado no status do campo e seu valor
        if self._get_field_template_status(field_name):
            if not value:  # Campo vazio
                widget.configure(border_color=default_border)
            else:  # Campo com conteúdo
                highlight_color = self.theme_manager.get_lighter_color(
                    default_border, factor=0.3
                )
                if animate:

                    def _animate():
                        widget.configure(border_color=highlight_color)
                        widget.after(
                            100, lambda: widget.configure(border_color=default_border)
                        )
                        widget.after(
                            200, lambda: widget.configure(border_color=highlight_color)
                        )

                    widget.after(1, _animate)
                else:
                    widget.configure(border_color=highlight_color)
        else:  # Campo que não faz parte do template
            widget.configure(border_color=default_border)

    def _validate_field_and_update_color(
        self, widget, field_name, animate=False, value=None
    ):
        """Valida o campo e atualiza a cor de acordo com o conteúdo"""
        logger.debug(f"\nValidando campo: {field_name}")
        logger.debug(f"  Tipo de widget: {type(widget).__name__}")

        try:
            is_template_field = self._get_field_template_status(field_name)
            logger.debug(f"  Campo é parte do template: {is_template_field}")

            # Obtém o valor se não foi fornecido
            if value is None:
                if isinstance(widget, ctk.CTkTextbox):
                    value = widget.get("1.0", "end-1c").strip()
                    logger.debug("  - TextBox:")
                elif isinstance(widget, ctk.CTkEntry):
                    value = widget.get().strip()
                    logger.debug("  - Entry:")
                elif isinstance(widget, ctk.StringVar):  # Para radio buttons
                    value = widget.get()
                    logger.debug("  - Radio:")
                    # Radio buttons não têm validação visual
                    return
                elif hasattr(widget, "get"):
                    value = widget.get().strip()
                else:
                    logger.warning(f"Widget '{field_name}' não suporta validação")
                    return

            logger.debug(f"    - Valor: '{value}'")
            current_color = (
                widget.cget("border_color") if hasattr(widget, "cget") else None
            )
            logger.debug(f"    - Cor atual: {current_color}")

            # Aplica a cor apenas se o widget suportar configuração visual
            if hasattr(widget, "configure"):
                self._apply_field_color(
                    widget, field_name, animate=animate, value=value
                )

        except Exception as e:
            logger.error(f"Erro ao validar campo {field_name}: {e}")

    def _handle_textbox_focusout(self, event, field_name, textbox, to_entry_fn):
        """Gerencia a perda de foco de um campo textbox"""
        # Valida o campo e atualiza cores apenas se houver conteúdo
        current_value = textbox.get("1.0", "end-1c").strip()
        if current_value:
            self._validate_field_and_update_color(
                textbox, field_name, value=current_value
            )
        else:
            # Se não tem conteúdo, volta para a cor padrão
            default_border = self.theme_manager.get_theme_default_color(
                ctk.CTkEntry, "border_color"
            )
            textbox.configure(border_color=default_border)

        # Captura o novo widget que está recebendo o foco (pode ser None)
        new_focus = self.focus_get()
        logger.debug(f"FocusOut em {field_name} (TextBox). Novo foco: {new_focus}")

        # Se o novo foco não é o próprio textbox e tem conteúdo, anima a cor
        if current_value and new_focus != textbox:
            if self._get_field_template_status(field_name):
                self._apply_field_color(
                    textbox, field_name, animate=True, value=current_value
                )

        # Registra perda de foco
        logger.debug(f"FocusOut em {field_name} (TextBox):")
        logger.debug(f"  - Valor atual: '{current_value}'")
        logger.debug(f"  - Novo foco: {new_focus}")

        # Se clicou fora do textbox ou mudou para outro widget
        if not new_focus or new_focus != textbox:
            logger.debug(
                f"  - Convertendo TextBox para Entry (perdeu foco para: {new_focus})"
            )
            if to_entry_fn:
                entry = to_entry_fn(current_value)
                if current_value and entry:
                    self._validate_field_and_update_color(
                        entry, field_name, value=current_value
                    )
                return "break"

    # Adiciona os métodos à classe
    cls._apply_field_color = _apply_field_color
    cls._validate_field_and_update_color = _validate_field_and_update_color
    cls._handle_textbox_focusout = _handle_textbox_focusout

    return cls
