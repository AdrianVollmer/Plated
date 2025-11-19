from __future__ import annotations

from django.test import TestCase
from django.urls import reverse

from .models import Ingredient, Recipe


class IngredientAPITestCase(TestCase):
    """Test cases for ingredient autocomplete API endpoints."""

    def setUp(self) -> None:
        """Create test recipes with ingredients."""
        recipe1 = Recipe.objects.create(title="Test Recipe 1", servings=4)
        recipe2 = Recipe.objects.create(title="Test Recipe 2", servings=2)

        Ingredient.objects.create(recipe=recipe1, name="flour", unit="cups", amount="2")
        Ingredient.objects.create(recipe=recipe1, name="sugar", unit="tbsp", amount="1")
        Ingredient.objects.create(recipe=recipe2, name="flour", unit="cups", amount="1")
        Ingredient.objects.create(recipe=recipe2, name="eggs", unit="", amount="2")

    def test_get_ingredient_names(self) -> None:
        """Test API endpoint returns distinct ingredient names."""
        response = self.client.get(reverse("api_ingredient_names"))
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("names", data)
        self.assertEqual(set(data["names"]), {"eggs", "flour", "sugar"})

    def test_get_ingredient_units(self) -> None:
        """Test API endpoint returns distinct ingredient units."""
        response = self.client.get(reverse("api_ingredient_units"))
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("units", data)
        self.assertEqual(set(data["units"]), {"cups", "tbsp"})

    def test_units_exclude_empty(self) -> None:
        """Test that empty units are excluded from the response."""
        response = self.client.get(reverse("api_ingredient_units"))
        data = response.json()
        self.assertNotIn("", data["units"])
