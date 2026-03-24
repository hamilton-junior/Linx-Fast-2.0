from abc import ABC, abstractmethod
from typing import Any, List, Optional


class TemplateServiceInterface(ABC):
    """Abstract interface describing the template-related operations used by UI."""

    @abstractmethod
    def get_template_names(self) -> List[str]:
        raise NotImplementedError()

    @abstractmethod
    def get_display_names(self) -> List[str]:
        raise NotImplementedError()

    @abstractmethod
    def get_template(self, name: str) -> str:
        raise NotImplementedError()

    @abstractmethod
    def save_template(
        self, old_name: Optional[str], new_name: str, content: str
    ) -> None:
        raise NotImplementedError()

    @abstractmethod
    def delete_template(self, name: str) -> None:
        raise NotImplementedError()

    @abstractmethod
    def extract_placeholders(self, content: str) -> List[str]:
        raise NotImplementedError()

    @abstractmethod
    def rename_placeholder(self, old_inner: str, new_inner: str) -> None:
        raise NotImplementedError()

    @abstractmethod
    def rename_field(self, old_inner: str, new_inner: str) -> None:
        raise NotImplementedError()


class TemplateServiceAdapter(TemplateServiceInterface):
    """Adapter that wraps an existing manager object to the TemplateServiceInterface.

    This allows UI code to depend on an abstraction while reusing the
    existing manager implementation.
    """

    def __init__(self, manager: Any):
        self._mgr = manager

    def get_template_names(self) -> List[str]:
        return self._mgr.get_template_names()

    def get_display_names(self) -> List[str]:
        return self._mgr.get_display_names()

    def get_template(self, name: str) -> str:
        return self._mgr.get_template(name)

    def save_template(
        self, old_name: Optional[str], new_name: str, content: str
    ) -> None:
        return self._mgr.save_template(old_name, new_name, content)

    def delete_template(self, name: str) -> None:
        return self._mgr.delete_template(name)

    def extract_placeholders(self, content: str) -> List[str]:
        return self._mgr.extract_placeholders(content)

    def rename_placeholder(self, old_inner: str, new_inner: str) -> None:
        if hasattr(self._mgr, "rename_placeholder"):
            return self._mgr.rename_placeholder(old_inner, new_inner)
        # best effort: try to call a similarly named API
        if hasattr(self._mgr, "rename_field"):
            return self._mgr.rename_field(old_inner, new_inner)
        # otherwise do nothing
        return None

    def rename_field(self, old_inner: str, new_inner: str) -> None:
        if hasattr(self._mgr, "rename_field"):
            return self._mgr.rename_field(old_inner, new_inner)
        if hasattr(self._mgr, "rename_placeholder"):
            return self._mgr.rename_placeholder(old_inner, new_inner)
        return None
