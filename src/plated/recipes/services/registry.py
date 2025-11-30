"""Registry for recipe format handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .json_format import JSONFormatHandler
from .mock_formats import CSVLikeFormatHandler, SimpleTextFormatHandler
from .tandoor_format import TandoorFormatHandler

if TYPE_CHECKING:
    from .base import RecipeFormatHandler


class FormatRegistry:
    """Registry to manage available recipe format handlers."""

    def __init__(self) -> None:
        """Initialize the registry with available format handlers."""
        self._handlers: dict[str, RecipeFormatHandler] = {}
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        """Register the default format handlers."""
        self.register(JSONFormatHandler())
        self.register(TandoorFormatHandler())
        # Register mock formats for demonstration
        self.register(SimpleTextFormatHandler())
        self.register(CSVLikeFormatHandler())

    def register(self, handler: RecipeFormatHandler) -> None:
        """
        Register a format handler.

        Args:
            handler: The format handler instance to register
        """
        self._handlers[handler.format_id] = handler

    def get_handler(self, format_id: str) -> RecipeFormatHandler | None:
        """
        Get a format handler by its ID.

        Args:
            format_id: The unique identifier of the format

        Returns:
            The format handler instance, or None if not found
        """
        return self._handlers.get(format_id)

    def get_all_handlers(self) -> dict[str, RecipeFormatHandler]:
        """
        Get all registered format handlers.

        Returns:
            Dictionary mapping format IDs to handler instances
        """
        return self._handlers.copy()

    def get_import_formats(self) -> list[tuple[str, str]]:
        """
        Get list of available import formats for use in forms.

        Returns:
            List of tuples (format_id, format_name) for use in form choices
        """
        return [(handler.format_id, handler.format_name) for handler in self._handlers.values()]

    def get_export_formats(self) -> list[tuple[str, str]]:
        """
        Get list of available export formats for use in forms.

        Returns:
            List of tuples (format_id, format_name) for use in form choices
        """
        return [(handler.format_id, handler.format_name) for handler in self._handlers.values()]

    def detect_format(self, content: str) -> RecipeFormatHandler | None:
        """
        Try to detect the format of the given content.

        Args:
            content: The file content as a string

        Returns:
            The detected format handler, or None if no handler can import the content
        """
        for handler in self._handlers.values():
            if handler.can_import(content):
                return handler
        return None


# Global registry instance
format_registry = FormatRegistry()
