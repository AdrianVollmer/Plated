from __future__ import annotations

from django.contrib import admin

from .models import AISettings, Ingredient, Recipe, RecipeCollection, RecipeImage, Step


class IngredientInline(admin.TabularInline):
    """Inline editor for ingredients."""

    model = Ingredient
    extra = 1
    fields = ["order", "amount", "unit", "name", "note"]
    ordering = ["order"]


class StepInline(admin.StackedInline):
    """Inline editor for steps."""

    model = Step
    extra = 1
    fields = ["order", "content"]
    ordering = ["order"]


class RecipeImageInline(admin.TabularInline):
    """Inline editor for recipe images."""

    model = RecipeImage
    extra = 1
    fields = ["order", "image", "caption"]
    ordering = ["order"]
    readonly_fields = ["created_at"]


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    """Admin interface for Recipe model."""

    list_display = ["title", "servings", "prep_time", "wait_time", "created_at"]
    list_filter = ["created_at", "updated_at"]
    search_fields = ["title", "description", "keywords"]
    readonly_fields = ["created_at", "updated_at"]
    fieldsets = [
        (
            "Basic Information",
            {
                "fields": ["title", "description", "servings", "keywords"],
            },
        ),
        (
            "Timing",
            {
                "fields": ["prep_time", "wait_time"],
            },
        ),
        (
            "Additional Information",
            {
                "fields": ["url", "special_equipment", "notes"],
                "classes": ["collapse"],
            },
        ),
        (
            "Metadata",
            {
                "fields": ["created_at", "updated_at"],
                "classes": ["collapse"],
            },
        ),
    ]
    inlines = [IngredientInline, StepInline, RecipeImageInline]


@admin.register(RecipeCollection)
class RecipeCollectionAdmin(admin.ModelAdmin):
    """Admin interface for RecipeCollection model."""

    list_display = ["name", "recipe_count", "created_at"]
    search_fields = ["name", "description"]
    filter_horizontal = ["recipes"]
    readonly_fields = ["created_at", "updated_at"]
    fieldsets = [
        (
            None,
            {
                "fields": ["name", "description"],
            },
        ),
        (
            "Recipes",
            {
                "fields": ["recipes"],
            },
        ),
        (
            "Metadata",
            {
                "fields": ["created_at", "updated_at"],
                "classes": ["collapse"],
            },
        ),
    ]

    @admin.display(description="Number of Recipes")
    def recipe_count(self, obj: RecipeCollection) -> int:
        """Display the number of recipes in the collection."""
        return obj.recipes.count()


@admin.register(AISettings)
class AISettingsAdmin(admin.ModelAdmin):
    """Admin interface for AISettings model."""

    list_display = ["model", "api_url", "created_at", "updated_at"]
    readonly_fields = ["created_at", "updated_at"]
    fieldsets = [
        (
            "API Configuration",
            {
                "fields": ["api_url", "api_key", "model"],
            },
        ),
        (
            "Model Parameters",
            {
                "fields": ["max_tokens", "temperature"],
            },
        ),
        (
            "Metadata",
            {
                "fields": ["created_at", "updated_at"],
                "classes": ["collapse"],
            },
        ),
    ]
