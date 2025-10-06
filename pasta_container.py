from typing import Union


class PastaContainer:
    """Classe que gerencia uma pasta escolhida de forma segura."""

    def __init__(self, inicial: Union[str, None] = "") -> None:
        self._pasta: str = str(inicial) if inicial is not None else ""

    def get(self) -> str:
        """Retorna o valor atual da pasta."""
        return self._pasta

    def set(self, valor: str) -> None:
        """Define um novo valor para a pasta."""
        self._pasta = str(valor)  # Garante que é uma string

    def __getitem__(self, _: int) -> str:
        """Permite acesso como lista para compatibilidade."""
        return self._pasta

    def __setitem__(self, _: int, valor: str) -> None:
        """Permite acesso como lista para compatibilidade."""
        self._pasta = str(valor)  # Garante que é uma string
