"""Tests for recipe CRUD views."""

from __future__ import annotations

from django.test import TestCase
from django.urls import reverse

from ..models import Ingredient, Recipe, Step


class RecipeListViewTest(TestCase):
    """Test cases for the recipe list view."""

    def setUp(self) -> None:
        """Create test recipes."""
        Recipe.objects.create(title="Pasta", servings=4, keywords="italian, dinner")
        Recipe.objects.create(title="Salad", servings=2, keywords="healthy, lunch")
        Recipe.objects.create(title="Cake", servings=8, keywords="dessert, sweet")

    def test_recipe_list_view(self) -> None:
        """Test that recipe list view displays all recipes."""
        response = self.client.get(reverse("recipe_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pasta")
        self.assertContains(response, "Salad")
        self.assertContains(response, "Cake")

    def test_recipe_list_search(self) -> None:
        """Test searching recipes."""
        response = self.client.get(reverse("recipe_list"), {"q": "pasta"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pasta")
        self.assertNotContains(response, "Salad")


class RecipeDetailViewTest(TestCase):
    """Test cases for the recipe detail view."""

    def setUp(self) -> None:
        """Create a test recipe with ingredients and steps."""
        self.recipe = Recipe.objects.create(
            title="Chocolate Chip Cookies",
            description="Classic cookies",
            servings=24,
            keywords="dessert, cookies",
        )
        Ingredient.objects.create(
            recipe=self.recipe,
            name="flour",
            amount="2",
            unit="cups",
            order=0,
        )
        Ingredient.objects.create(
            recipe=self.recipe,
            name="chocolate chips",
            amount="1",
            unit="cup",
            order=1,
        )
        Step.objects.create(
            recipe=self.recipe,
            content="Mix dry ingredients",
            order=0,
        )
        Step.objects.create(
            recipe=self.recipe,
            content="Bake at 350°F for 12 minutes",
            order=1,
        )

    def test_recipe_detail_view(self) -> None:
        """Test that recipe detail view displays recipe information."""
        response = self.client.get(reverse("recipe_detail", args=[self.recipe.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Chocolate Chip Cookies")
        self.assertContains(response, "Classic cookies")
        self.assertContains(response, "flour")
        self.assertContains(response, "Mix dry ingredients")

    def test_recipe_detail_nonexistent(self) -> None:
        """Test detail view for a recipe that doesn't exist."""
        response = self.client.get(reverse("recipe_detail", args=[9999]))
        self.assertEqual(response.status_code, 404)


class RecipeCreateViewTest(TestCase):
    """Test cases for the recipe create view."""

    def test_recipe_create_view_get(self) -> None:
        """Test GET request to recipe create view."""
        response = self.client.get(reverse("recipe_create"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "title")

    def test_recipe_create_basic(self) -> None:
        """Test creating a basic recipe with one step (required by validation)."""
        response = self.client.post(
            reverse("recipe_create"),
            {
                "title": "New Recipe",
                "servings": 4,
                "description": "Test description",
                # Formsets require management form data
                "ingredients-TOTAL_FORMS": "0",
                "ingredients-INITIAL_FORMS": "0",
                # At least one step is required by validation
                "steps-TOTAL_FORMS": "1",
                "steps-INITIAL_FORMS": "0",
                "steps-0-content": "Prepare the recipe",
                "steps-0-order": "0",
                "images-TOTAL_FORMS": "0",
                "images-INITIAL_FORMS": "0",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Recipe.objects.filter(title="New Recipe").exists())

    def test_recipe_create_with_ingredients_and_steps(self) -> None:
        """Test creating a recipe with ingredients and steps."""
        response = self.client.post(
            reverse("recipe_create"),
            {
                "title": "Scrambled Eggs",
                "servings": 2,
                "description": "Quick breakfast",
                # Ingredients formset
                "ingredients-TOTAL_FORMS": "2",
                "ingredients-INITIAL_FORMS": "0",
                "ingredients-0-name": "eggs",
                "ingredients-0-amount": "4",
                "ingredients-0-unit": "",
                "ingredients-0-order": "0",
                "ingredients-1-name": "butter",
                "ingredients-1-amount": "1",
                "ingredients-1-unit": "tbsp",
                "ingredients-1-order": "1",
                # Steps formset
                "steps-TOTAL_FORMS": "2",
                "steps-INITIAL_FORMS": "0",
                "steps-0-content": "Beat eggs",
                "steps-0-order": "0",
                "steps-1-content": "Cook in pan with butter",
                "steps-1-order": "1",
                # Images formset
                "images-TOTAL_FORMS": "0",
                "images-INITIAL_FORMS": "0",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)

        recipe = Recipe.objects.filter(title="Scrambled Eggs").first()
        self.assertIsNotNone(recipe)
        assert recipe is not None  # Type narrowing for mypy
        self.assertEqual(recipe.ingredients.count(), 2)
        self.assertEqual(recipe.steps.count(), 2)


class RecipeUpdateViewTest(TestCase):
    """Test cases for the recipe update view."""

    def setUp(self) -> None:
        """Create a test recipe."""
        self.recipe = Recipe.objects.create(
            title="Original Title",
            servings=4,
            description="Original description",
        )
        Ingredient.objects.create(
            recipe=self.recipe,
            name="sugar",
            amount="1",
            unit="cup",
            order=0,
        )

    def test_recipe_update_view_get(self) -> None:
        """Test GET request to recipe update view."""
        response = self.client.get(reverse("recipe_update", args=[self.recipe.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Original Title")

    def test_recipe_update_title(self) -> None:
        """Test updating a recipe's title."""
        response = self.client.post(
            reverse("recipe_update", args=[self.recipe.pk]),
            {
                "title": "Updated Title",
                "servings": 4,
                "description": "Original description",
                # Existing ingredient
                "ingredients-TOTAL_FORMS": "1",
                "ingredients-INITIAL_FORMS": "1",
                "ingredients-0-id": (str(ing.pk) if (ing := self.recipe.ingredients.first()) is not None else "0"),
                "ingredients-0-name": "sugar",
                "ingredients-0-amount": "1",
                "ingredients-0-unit": "cup",
                "ingredients-0-order": "0",
                # At least one step is required by validation
                "steps-TOTAL_FORMS": "1",
                "steps-INITIAL_FORMS": "0",
                "steps-0-content": "Mix and bake",
                "steps-0-order": "0",
                # Images formset
                "images-TOTAL_FORMS": "0",
                "images-INITIAL_FORMS": "0",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)

        self.recipe.refresh_from_db()
        self.assertEqual(self.recipe.title, "Updated Title")


class RecipeDeleteViewTest(TestCase):
    """Test cases for the recipe delete view."""

    def setUp(self) -> None:
        """Create a test recipe."""
        self.recipe = Recipe.objects.create(
            title="Recipe to Delete",
            servings=4,
        )

    def test_recipe_delete_view_get(self) -> None:
        """Test GET request to recipe delete view (confirmation page)."""
        response = self.client.get(reverse("recipe_delete", args=[self.recipe.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Recipe to Delete")

    def test_recipe_delete_post(self) -> None:
        """Test POST request to delete a recipe."""
        recipe_pk = self.recipe.pk
        response = self.client.post(
            reverse("recipe_delete", args=[self.recipe.pk]),
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Recipe.objects.filter(pk=recipe_pk).exists())
