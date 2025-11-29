"""Type definitions for recipe data structures."""

from __future__ import annotations

from typing import TypedDict


class IngredientSchema(TypedDict, total=False):
    """Schema for an ingredient."""

    amount: str
    unit: str
    name: str
    note: str
    order: int


class StepSchema(TypedDict):
    """Schema for a recipe step."""

    content: str
    order: int


class ImageSchema(TypedDict, total=False):
    """Schema for a recipe image metadata (not the actual image file)."""

    caption: str
    order: int


class RecipeSchema(TypedDict, total=False):
    """Schema for a complete recipe."""

    title: str
    description: str
    servings: int
    keywords: str
    prep_time_minutes: int | None
    wait_time_minutes: int | None
    url: str
    notes: str
    special_equipment: str
    ingredients: list[IngredientSchema]
    steps: list[StepSchema]
    images: list[ImageSchema]
