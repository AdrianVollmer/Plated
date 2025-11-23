from __future__ import annotations

from django.conf import settings as django_settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Recipe(models.Model):
    """A recipe with title, description, and other metadata."""

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    servings = models.PositiveIntegerField(default=1)
    keywords = models.CharField(max_length=500, blank=True, help_text="Comma-separated keywords")
    prep_time = models.DurationField(null=True, blank=True, help_text="Time to prepare ingredients")
    wait_time = models.DurationField(null=True, blank=True, help_text="Time for cooking/baking/waiting")
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

    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="ingredients")
    amount = models.CharField(max_length=50, blank=True, help_text="e.g., '2', '1/2', '1-2'")
    unit = models.CharField(max_length=50, blank=True, help_text="e.g., 'cups', 'tbsp', 'g'")
    name = models.CharField(max_length=200)
    note = models.CharField(max_length=200, blank=True, help_text="e.g., 'chopped', 'room temperature'")
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


class AISettings(models.Model):
    """Settings for AI/LLM integration."""

    api_url = models.URLField(
        help_text="URL of the LLM API endpoint (e.g., https://api.openai.com/v1/chat/completions)"
    )
    api_key = models.CharField(max_length=500, help_text="API key for authentication", blank=True, null=True)
    model = models.CharField(
        max_length=200,
        help_text="Model name (e.g., gpt-4, claude-3-sonnet-20240229)",
    )
    max_tokens = models.PositiveIntegerField(default=4096, help_text="Maximum tokens for the response")
    temperature = models.FloatField(
        default=0.7,
        help_text="Temperature for response randomness (0.0 to 2.0)",
    )
    timeout = models.PositiveIntegerField(
        default=60,
        validators=[MinValueValidator(10), MaxValueValidator(600)],
        help_text="Timeout in seconds (10-600). Jobs with timeout > 10s run in background.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "AI Settings"
        verbose_name_plural = "AI Settings"

    def __str__(self) -> str:
        return f"AI Settings (Model: {self.model})"


class MealPlan(models.Model):
    """A meal plan for a specific time period."""

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self) -> str:
        return self.name


class MealPlanEntry(models.Model):
    """A specific recipe scheduled for a date and meal type in a meal plan."""

    MEAL_TYPE_CHOICES = [
        ("breakfast", "Breakfast"),
        ("lunch", "Lunch"),
        ("dinner", "Dinner"),
        ("snack", "Snack"),
    ]

    meal_plan = models.ForeignKey(MealPlan, on_delete=models.CASCADE, related_name="entries")
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="meal_plan_entries")
    date = models.DateField()
    meal_type = models.CharField(max_length=20, choices=MEAL_TYPE_CHOICES)
    servings = models.PositiveIntegerField(default=1, help_text="Number of servings for this meal")
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["date", "meal_type"]
        verbose_name_plural = "Meal plan entries"

    def __str__(self) -> str:
        return f"{self.recipe.title} - {self.get_meal_type_display()} on {self.date}"


class AIJob(models.Model):
    """A background job for AI recipe extraction."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]

    INPUT_TYPE_CHOICES = [
        ("text", "Text"),
        ("html", "HTML"),
        ("url", "URL"),
    ]

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    input_type = models.CharField(max_length=10, choices=INPUT_TYPE_CHOICES)
    input_content = models.TextField(help_text="The text, HTML, or URL to extract recipe from")
    instructions = models.TextField(blank=True, help_text="Optional additional instructions for the AI")
    result_data = models.JSONField(null=True, blank=True, help_text="Extracted recipe data as JSON")
    error_message = models.TextField(blank=True, help_text="Error message if job failed")
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    seen = models.BooleanField(default=False, help_text="Whether user has seen this completed/failed job")
    timeout = models.PositiveIntegerField(help_text="Timeout in seconds for this job")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "AI Job"
        verbose_name_plural = "AI Jobs"

    def __str__(self) -> str:
        return f"AI Job {self.pk} - {self.get_status_display()} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"


class UserSettings(models.Model):
    """User-specific settings including language preference."""

    # Use session_key as a unique identifier for users (works without authentication)
    session_key = models.CharField(max_length=40, unique=True, db_index=True)
    language = models.CharField(
        max_length=10,
        choices=[(lang[0], lang[1]) for lang in django_settings.LANGUAGES],
        default=django_settings.LANGUAGE_CODE,
        help_text="Preferred language for the interface",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User Settings"
        verbose_name_plural = "User Settings"

    def __str__(self) -> str:
        return f"Settings for {self.session_key} (Language: {self.get_language_display()})"
