class StringRef:
    """Uma classe simples para encapsular uma string mutável."""

    def __init__(self, initial_value: str = "") -> None:
        self.value = str(initial_value)

    def get(self) -> str:
        return self.value

    def set(self, new_value: str) -> None:
        self.value = str(new_value)

    def __getitem__(self, index: int) -> str:
        """Suporte para acesso como lista para compatibilidade."""
        return self.value if index == 0 else ""

    def __setitem__(self, index: int, value: str) -> None:
        """Suporte para acesso como lista para compatibilidade."""
        if index == 0:
            self.value = str(value)

    def __str__(self) -> str:
        return self.value
