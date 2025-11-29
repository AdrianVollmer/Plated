"""JSON Schema generation for AI recipe extraction."""

from __future__ import annotations

from typing import Any


def get_recipe_json_schema() -> dict[str, Any]:
    """
    Generate a JSON schema for recipe extraction by AI.

    Returns a proper JSON schema (draft-07) that defines the structure,
    types, and validation rules for recipe data. This is used to guide
    AI models in extracting recipe information.
    """
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Recipe title",
                "minLength": 1,
            },
            "description": {
                "type": "string",
                "description": "Brief description of the recipe",
            },
            "servings": {
                "type": "integer",
                "description": "Number of servings",
                "minimum": 1,
                "default": 1,
            },
            "keywords": {
                "type": "string",
                "description": "Comma-separated keywords for categorization and search",
            },
            "prep_time_minutes": {
                "type": ["integer", "null"],
                "description": "Time to prepare ingredients in minutes",
                "minimum": 0,
            },
            "wait_time_minutes": {
                "type": ["integer", "null"],
                "description": "Time for cooking/baking/waiting in minutes",
                "minimum": 0,
            },
            "url": {
                "type": "string",
                "description": "Source URL if recipe is from the web",
                "format": "uri",
            },
            "notes": {
                "type": "string",
                "description": "Any additional notes about the recipe",
            },
            "special_equipment": {
                "type": "string",
                "description": "Special equipment needed for the recipe",
            },
            "ingredients": {
                "type": "array",
                "description": "List of ingredients",
                "items": {
                    "type": "object",
                    "properties": {
                        "amount": {
                            "type": "string",
                            "description": "Amount/quantity (e.g., '2', '1/2', '1-2')",
                        },
                        "unit": {
                            "type": "string",
                            "description": "Unit of measurement (e.g., 'cups', 'tbsp', 'g')",
                        },
                        "name": {
                            "type": "string",
                            "description": "Name of the ingredient",
                            "minLength": 1,
                        },
                        "note": {
                            "type": "string",
                            "description": "Additional notes (e.g., 'chopped', 'room temperature')",
                        },
                        "order": {
                            "type": "integer",
                            "description": "Display order (0-indexed)",
                            "minimum": 0,
                        },
                    },
                    "required": ["name"],
                },
            },
            "steps": {
                "type": "array",
                "description": "List of recipe steps",
                "items": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "Step instructions",
                            "minLength": 1,
                        },
                        "order": {
                            "type": "integer",
                            "description": "Display order (0-indexed)",
                            "minimum": 0,
                        },
                    },
                    "required": ["content"],
                },
            },
        },
        "required": ["title"],
    }
