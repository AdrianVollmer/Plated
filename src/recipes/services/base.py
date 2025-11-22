"""Base class for recipe import/export format handlers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import Recipe


class RecipeFormatHandler(ABC):
    """Abstract base class for recipe format import/export handlers."""

    @property
    @abstractmethod
    def format_name(self) -> str:
        """Human-readable name of the format (e.g., 'JSON', 'YAML')."""
        pass

    @property
    @abstractmethod
    def format_id(self) -> str:
        """Unique identifier for the format (e.g., 'json', 'yaml')."""
        pass

    @property
    @abstractmethod
    def file_extension(self) -> str:
        """File extension for this format (e.g., '.json', '.yaml')."""
        pass

    @property
    @abstractmethod
    def mime_type(self) -> str:
        """MIME type for this format (e.g., 'application/json')."""
        pass

    @abstractmethod
    def can_import(self, content: str) -> bool:
        """
        Check if the content can be imported by this handler.

        Args:
            content: The file content as a string

        Returns:
            True if this handler can import the content, False otherwise
        """
        pass

    @abstractmethod
    def import_recipe(self, content: str) -> Recipe:
        """
        Import a recipe from the given content.

        Args:
            content: The file content as a string

        Returns:
            A Recipe model instance (not yet saved to database)

        Raises:
            ValueError: If the content is invalid or cannot be parsed
        """
        pass

    @abstractmethod
    def export_recipe(self, recipe: Recipe) -> str:
        """
        Export a recipe to a string in this format.

        Args:
            recipe: The Recipe model instance to export

        Returns:
            The recipe data as a formatted string

        Raises:
            ValueError: If the recipe cannot be exported
        """
        pass
