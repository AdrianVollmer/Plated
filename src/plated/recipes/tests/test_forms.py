"""Tests for form validation."""

from __future__ import annotations

from django.test import TestCase

from ..forms import AIRecipeExtractionForm, AISettingsForm, RecipeForm, UserSettingsForm
from ..models import Recipe


class RecipeFormTest(TestCase):
    """Test cases for RecipeForm validation."""

    def test_valid_recipe_form(self) -> None:
        """Test form with valid data."""
        form = RecipeForm(
            data={
                "title": "Test Recipe",
                "description": "A test recipe",
                "servings": 4,
                "keywords": "test, recipe",
            }
        )
        self.assertTrue(form.is_valid())

    def test_recipe_form_missing_title(self) -> None:
        """Test form validation fails when title is missing."""
        form = RecipeForm(
            data={
                "description": "A test recipe",
                "servings": 4,
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)

    def test_recipe_form_missing_servings(self) -> None:
        """Test form validation fails when servings is missing."""
        form = RecipeForm(
            data={
                "title": "Test Recipe",
                "description": "A test recipe",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("servings", form.errors)

    def test_recipe_form_invalid_servings(self) -> None:
        """Test form validation fails with invalid servings."""
        form = RecipeForm(
            data={
                "title": "Test Recipe",
                "servings": -1,
            }
        )
        self.assertFalse(form.is_valid())

    def test_recipe_form_with_prep_time(self) -> None:
        """Test form with prep time."""
        form = RecipeForm(
            data={
                "title": "Test Recipe",
                "servings": 4,
                "prep_time": "00:30:00",
            }
        )
        self.assertTrue(form.is_valid())

    def test_recipe_form_with_wait_time(self) -> None:
        """Test form with wait time."""
        form = RecipeForm(
            data={
                "title": "Test Recipe",
                "servings": 4,
                "wait_time": "01:00:00",
            }
        )
        self.assertTrue(form.is_valid())

    def test_recipe_form_save(self) -> None:
        """Test that form saves correctly to database."""
        form = RecipeForm(
            data={
                "title": "Saved Recipe",
                "description": "This should be saved",
                "servings": 6,
                "keywords": "save, test",
            }
        )
        self.assertTrue(form.is_valid())
        recipe = form.save()

        self.assertEqual(recipe.title, "Saved Recipe")
        self.assertEqual(recipe.servings, 6)
        self.assertTrue(Recipe.objects.filter(title="Saved Recipe").exists())

    def test_recipe_form_update(self) -> None:
        """Test that form can update an existing recipe."""
        recipe = Recipe.objects.create(title="Original", servings=2)

        form = RecipeForm(
            data={
                "title": "Updated",
                "servings": 4,
            },
            instance=recipe,
        )
        self.assertTrue(form.is_valid())
        updated_recipe = form.save()

        self.assertEqual(updated_recipe.pk, recipe.pk)
        self.assertEqual(updated_recipe.title, "Updated")
        self.assertEqual(updated_recipe.servings, 4)


class AISettingsFormTest(TestCase):
    """Test cases for AISettingsForm validation."""

    def test_valid_ai_settings_form(self) -> None:
        """Test form with valid AI settings."""
        form = AISettingsForm(
            data={
                "api_url": "https://api.openai.com/v1/chat/completions",
                "api_key": "sk-test123",
                "model": "gpt-4",
                "max_tokens": 4000,
                "temperature": 0.7,
                "timeout": 60,
            }
        )
        self.assertTrue(form.is_valid())

    def test_ai_settings_form_invalid_url(self) -> None:
        """Test form validation fails with invalid URL."""
        form = AISettingsForm(
            data={
                "api_url": "not-a-url",
                "api_key": "sk-test123",
                "model": "gpt-4",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("api_url", form.errors)

    def test_ai_settings_form_missing_required_fields(self) -> None:
        """Test form validation fails when required fields are missing."""
        form = AISettingsForm(data={})
        self.assertFalse(form.is_valid())
        # Should have errors for required fields
        self.assertTrue(len(form.errors) > 0)


class AIRecipeExtractionFormTest(TestCase):
    """Test cases for AIRecipeExtractionForm validation."""

    def test_valid_extraction_form_text(self) -> None:
        """Test form with text input type."""
        form = AIRecipeExtractionForm(
            data={
                "input_type": "text",
                "input_content": "Recipe: Mix ingredients and bake",
            }
        )
        self.assertTrue(form.is_valid())

    def test_valid_extraction_form_html(self) -> None:
        """Test form with HTML input type."""
        form = AIRecipeExtractionForm(
            data={
                "input_type": "html",
                "input_content": "<html><body>Recipe content</body></html>",
            }
        )
        self.assertTrue(form.is_valid())

    def test_valid_extraction_form_url(self) -> None:
        """Test form with URL input type."""
        form = AIRecipeExtractionForm(
            data={
                "input_type": "url",
                "input_content": "https://example.com/recipe",
            }
        )
        self.assertTrue(form.is_valid())

    def test_extraction_form_missing_content(self) -> None:
        """Test form validation fails when content is missing."""
        form = AIRecipeExtractionForm(
            data={
                "input_type": "text",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("input_content", form.errors)

    def test_extraction_form_with_optional_prompt(self) -> None:
        """Test form with optional prompt field."""
        form = AIRecipeExtractionForm(
            data={
                "input_type": "text",
                "input_content": "Recipe content",
                "prompt": "Translate to German",
            }
        )
        self.assertTrue(form.is_valid())

    def test_extraction_form_without_optional_prompt(self) -> None:
        """Test form is valid without optional prompt."""
        form = AIRecipeExtractionForm(
            data={
                "input_type": "text",
                "input_content": "Recipe content",
            }
        )
        self.assertTrue(form.is_valid())


class UserSettingsFormTest(TestCase):
    """Test cases for UserSettingsForm validation."""

    def test_valid_user_settings_form(self) -> None:
        """Test form with valid language setting."""
        form = UserSettingsForm(
            data={
                "language": "en",
                "locale": "en-us",
            }
        )
        self.assertTrue(form.is_valid())

    def test_user_settings_form_german(self) -> None:
        """Test form with German language."""
        form = UserSettingsForm(
            data={
                "language": "de",
                "locale": "de-de",
            }
        )
        self.assertTrue(form.is_valid())
