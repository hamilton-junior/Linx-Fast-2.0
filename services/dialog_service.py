import ctk_dialogs
from typing import Optional


class DialogService:
    """Small adapter providing a neutral dialog API for the app.

    This lets UI classes depend on an interface instead of a concrete module
    and makes the code easier to test/mock.
    """

    def __init__(self, parent):
        self.parent = parent

    def message(self, title: str, message: str, kind: str = "info") -> None:
        # Delegate to existing helpers (keeps behavior exactly the same)
        return ctk_dialogs.ctk_message(self.parent, title, message, kind=kind)

    def ask_yes_no(self, title: str, message: str) -> bool:
        return ctk_dialogs.ctk_ask_yes_no(self.parent, title, message)

    def ask_string(self, title: str, prompt: str, initial: Optional[str] = None) -> Optional[str]:
        return ctk_dialogs.ctk_ask_string(self.parent, title, prompt, initial=initial)
