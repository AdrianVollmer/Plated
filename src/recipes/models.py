from __future__ import annotations

from django.db import models


class Recipe(models.Model):
    """A recipe with title, description, and other metadata."""

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    servings = models.PositiveIntegerField(default=1)
    keywords = models.CharField(
        max_length=500, blank=True, help_text="Comma-separated keywords"
    )
    prep_time = models.DurationField(
        null=True, blank=True, help_text="Time to prepare ingredients"
    )
    wait_time = models.DurationField(
        null=True, blank=True, help_text="Time for cooking/baking/waiting"
    )
    url = models.URLField(blank=True, help_text="Source URL if recipe is from the web")
    notes = models.TextField(blank=True)
    special_equipment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title


class Ingredient(models.Model):
    """An ingredient in a recipe."""

    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name="ingredients"
    )
    amount = models.CharField(
        max_length=50, blank=True, help_text="e.g., '2', '1/2', '1-2'"
    )
    unit = models.CharField(
        max_length=50, blank=True, help_text="e.g., 'cups', 'tbsp', 'g'"
    )
    name = models.CharField(max_length=200)
    note = models.CharField(
        max_length=200, blank=True, help_text="e.g., 'chopped', 'room temperature'"
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self) -> str:
        parts = []
        if self.amount:
            parts.append(self.amount)
        if self.unit:
            parts.append(self.unit)
        parts.append(self.name)
        if self.note:
            parts.append(f"({self.note})")
        return " ".join(parts)


class Step(models.Model):
    """A step in a recipe, supporting markdown."""

    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="steps")
    order = models.PositiveIntegerField(default=0)
    content = models.TextField(help_text="Markdown supported")

    class Meta:
        ordering = ["order"]

    def __str__(self) -> str:
        return f"Step {self.order + 1}: {self.content[:50]}"


class RecipeImage(models.Model):
    """An image associated with a recipe."""

    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="recipes/%Y/%m/%d/")
    order = models.PositiveIntegerField(default=0)
    caption = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order"]

    def __str__(self) -> str:
        return f"Image for {self.recipe.title}"


class RecipeCollection(models.Model):
    """A collection of related recipes."""

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    recipes = models.ManyToManyField(Recipe, related_name="collections", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
