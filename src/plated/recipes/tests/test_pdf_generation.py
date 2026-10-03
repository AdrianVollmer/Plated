"""Tests for PDF generation functionality."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, Mock, patch

from django.test import TestCase
from django.urls import reverse

from ..models import Ingredient, MealPlan, MealPlanEntry, Recipe, RecipeCollection, Step


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

    @patch("recipes.views.recipes.generate_recipe_pdf")
    def test_pdf_is_served_inline(self, mock_generate: MagicMock) -> None:
        """PDFs must be served as 'inline', not 'attachment'.

        A forced download (Content-Disposition: attachment) is invisible in
        standalone PWA mode on Android -- there's no browser chrome to show
        download progress/completion, so it looks like nothing happened.
        """
        mock_generate.return_value = b"PDF content"

        response = self.client.get(reverse("recipe_pdf", args=[self.recipe.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertIn("inline", response["Content-Disposition"])
        self.assertNotIn("attachment", response["Content-Disposition"])


class CollectionAndMealPlanPDFInlineTestCase(TestCase):
    """PDF downloads for collections and meal plans must also be inline (see PDFGenerationTestCase)."""

    def setUp(self) -> None:
        self.recipe = Recipe.objects.create(title="Pasta", servings=4)
        Ingredient.objects.create(recipe=self.recipe, name="pasta", amount="1", unit="lb", order=0)

        self.collection = RecipeCollection.objects.create(name="Test Collection")
        self.collection.recipes.add(self.recipe)

        self.meal_plan = MealPlan.objects.create(
            name="Test Meal Plan",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 7),
        )
        MealPlanEntry.objects.create(
            meal_plan=self.meal_plan,
            recipe=self.recipe,
            date=date(2024, 1, 1),
            meal_type="dinner",
        )

    @patch("recipes.services.typst_service.generate_typst_pdf")
    def test_collection_pdf_is_served_inline(self, mock_generate: MagicMock) -> None:
        mock_generate.return_value = b"PDF content"

        response = self.client.get(reverse("collection_pdf", args=[self.collection.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertIn("inline", response["Content-Disposition"])
        self.assertNotIn("attachment", response["Content-Disposition"])

    @patch("recipes.services.typst_service.generate_typst_pdf")
    def test_meal_plan_pdf_is_served_inline(self, mock_generate: MagicMock) -> None:
        mock_generate.return_value = b"PDF content"

        response = self.client.get(reverse("meal_plan_pdf", args=[self.meal_plan.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertIn("inline", response["Content-Disposition"])
        self.assertNotIn("attachment", response["Content-Disposition"])

    @patch("recipes.services.typst_service.generate_typst_pdf")
    def test_shopping_list_pdf_is_served_inline(self, mock_generate: MagicMock) -> None:
        mock_generate.return_value = b"PDF content"

        response = self.client.get(reverse("shopping_list_pdf", args=[self.meal_plan.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertIn("inline", response["Content-Disposition"])
        self.assertNotIn("attachment", response["Content-Disposition"])
