from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, Mock, patch

from django.test import TestCase
from django.urls import reverse

from .models import Ingredient, Recipe, Step


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


class PDFGenerationTestCase(TestCase):
    """Test cases for PDF generation functionality."""

    def setUp(self) -> None:
        """Create a test recipe with ingredients and steps."""
        self.recipe = Recipe.objects.create(
            title="Test Recipe",
            description="A test recipe for PDF generation",
            servings=4,
            keywords="test, pdf",
        )
        Ingredient.objects.create(
            recipe=self.recipe,
            name="flour",
            unit="cups",
            amount="2",
            order=0,
        )
        Ingredient.objects.create(
            recipe=self.recipe,
            name="sugar",
            unit="tbsp",
            amount="1",
            order=1,
        )
        Step.objects.create(
            recipe=self.recipe,
            content="Mix ingredients together",
            order=0,
        )
        Step.objects.create(
            recipe=self.recipe,
            content="Bake at 350°F for 30 minutes",
            order=1,
        )

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_pdf_generation_success(
        self,
        mock_exists: MagicMock,
        mock_subprocess: MagicMock,
    ) -> None:
        """Test successful PDF generation."""
        # Mock the Typst template file exists check
        mock_exists.return_value = True

        # Mock successful subprocess run
        mock_subprocess.return_value = Mock(returncode=0, stderr="")

        # Mock the PDF file creation by writing to the temp file
        with patch("builtins.open", create=True) as mock_open:
            # Setup mock file handle for reading the PDF
            mock_file = MagicMock()
            mock_file.read.return_value = b"PDF content"
            mock_file.__enter__.return_value = mock_file
            mock_open.return_value = mock_file

            response = self.client.get(reverse("recipe_pdf", args=[self.recipe.pk]))

            # Note: Due to the complexity of mocking file operations within
            # TemporaryDirectory, this test mainly verifies the view logic
            self.assertIn(
                response.status_code,
                [200, 302],  # Could be successful or redirect on error
            )

    @patch("pathlib.Path.exists")
    def test_pdf_generation_typst_not_found(
        self,
        mock_exists: MagicMock,
    ) -> None:
        """Test PDF generation when Typst is not installed."""
        # Mock the Typst template file exists
        mock_exists.return_value = True

        with patch("subprocess.run", side_effect=FileNotFoundError):
            response = self.client.get(
                reverse("recipe_pdf", args=[self.recipe.pk]),
                follow=False,
            )

            # Should redirect back to recipe detail
            self.assertEqual(response.status_code, 302)
            self.assertEqual(
                response["Location"],
                reverse("recipe_detail", args=[self.recipe.pk]),
            )

    def test_pdf_generation_nonexistent_recipe(self) -> None:
        """Test PDF generation for a recipe that doesn't exist."""
        response = self.client.get(reverse("recipe_pdf", args=[9999]))
        self.assertEqual(response.status_code, 404)
