"""Tests for recipe import functionality."""

from __future__ import annotations

import json
import zipfile
from io import BytesIO

from django.test import Client, TestCase
from django.urls import reverse

from ..models import Recipe
from ..services.tandoor_format import TandoorFormatHandler


class TandoorFormatHandlerTest(TestCase):
    """Test the Tandoor format handler."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.handler = TandoorFormatHandler()

    def test_format_properties(self) -> None:
        """Test format handler properties."""
        self.assertEqual(self.handler.format_name, "Tandoor")
        self.assertEqual(self.handler.format_id, "tandoor")
        self.assertEqual(self.handler.file_extension, ".json")
        self.assertEqual(self.handler.mime_type, "application/json")

    def test_can_import_valid_tandoor_json(self) -> None:
        """Test that valid Tandoor JSON is recognized."""
        tandoor_data = {
            "name": "Test Recipe",
            "description": "Test description",
            "steps": [{"instruction": "Do something"}],
            "servings": 4,
        }
        content = json.dumps(tandoor_data)
        self.assertTrue(self.handler.can_import(content))

    def test_can_import_invalid_json(self) -> None:
        """Test that invalid JSON is rejected."""
        self.assertFalse(self.handler.can_import("not valid json"))

    def test_can_import_missing_required_fields(self) -> None:
        """Test that JSON without required fields is rejected."""
        invalid_data = {"description": "Missing name field"}
        content = json.dumps(invalid_data)
        self.assertFalse(self.handler.can_import(content))

    def test_import_basic_recipe(self) -> None:
        """Test importing a basic Tandoor recipe."""
        tandoor_data = {
            "name": "Bolognese",
            "description": "Traditional Italian sauce",
            "servings": 6,
            "working_time": 45,
            "waiting_time": 240,
            "keywords": [{"name": "Italian"}, {"name": "Pasta"}],
            "steps": [
                {
                    "instruction": "Cook the meat",
                    "ingredients": [
                        {
                            "food": {"name": "Ground beef"},
                            "unit": {"name": "g"},
                            "amount": 500.0,
                            "note": "lean",
                        }
                    ],
                },
                {
                    "instruction": "Add tomatoes",
                    "ingredients": [
                        {
                            "food": {"name": "Tomatoes"},
                            "unit": {"name": "can"},
                            "amount": 1.0,
                            "note": None,
                        }
                    ],
                },
            ],
            "source_url": "https://example.com/recipe",
        }

        content = json.dumps(tandoor_data)
        recipe = self.handler.import_recipe(content)

        # Verify recipe was created
        self.assertIsNotNone(recipe.pk)
        self.assertEqual(recipe.title, "Bolognese")
        self.assertEqual(recipe.description, "Traditional Italian sauce")
        self.assertEqual(recipe.servings, 6)
        self.assertEqual(recipe.keywords, "Italian, Pasta")
        self.assertEqual(recipe.url, "https://example.com/recipe")

        # Verify times
        self.assertIsNotNone(recipe.prep_time)
        self.assertIsNotNone(recipe.wait_time)
        assert recipe.prep_time is not None  # for mypy
        assert recipe.wait_time is not None  # for mypy
        self.assertEqual(recipe.prep_time.total_seconds(), 45 * 60)
        self.assertEqual(recipe.wait_time.total_seconds(), 240 * 60)

        # Verify ingredients
        ingredients = list(recipe.ingredients.all().order_by("order"))
        self.assertEqual(len(ingredients), 2)
        self.assertEqual(ingredients[0].name, "Ground beef")
        self.assertEqual(ingredients[0].amount, "500.0")  # amount is CharField
        self.assertEqual(ingredients[0].unit, "g")
        self.assertEqual(ingredients[0].note, "lean")

        # Verify steps
        steps = list(recipe.steps.all().order_by("order"))
        self.assertEqual(len(steps), 2)
        self.assertEqual(steps[0].content, "Cook the meat")
        self.assertEqual(steps[1].content, "Add tomatoes")

    def test_import_recipe_without_times(self) -> None:
        """Test importing a recipe without time information."""
        tandoor_data = {
            "name": "Simple Recipe",
            "description": "",
            "servings": 2,
            "steps": [{"instruction": "Mix ingredients", "ingredients": []}],
        }

        content = json.dumps(tandoor_data)
        recipe = self.handler.import_recipe(content)

        self.assertIsNone(recipe.prep_time)
        self.assertIsNone(recipe.wait_time)

    def test_export_not_implemented(self) -> None:
        """Test that export raises NotImplementedError."""
        recipe = Recipe.objects.create(title="Test", servings=1)
        with self.assertRaises(NotImplementedError):
            self.handler.export_recipe(recipe)


class ImportViewsTest(TestCase):
    """Test import views."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.client = Client()
        # Create a session
        session = self.client.session
        session.save()

    def test_settings_page_has_import_form(self) -> None:
        """Test that settings page includes import form."""
        response = self.client.get(reverse("settings"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Database Import")
        self.assertContains(response, "import_file")

    def test_import_upload_tandoor_format(self) -> None:
        """Test uploading a Tandoor format file."""
        # Create a mock Tandoor export
        recipe_data = {
            "name": "Test Recipe",
            "description": "Test",
            "servings": 4,
            "steps": [{"instruction": "Test step", "ingredients": []}],
        }

        # Create inner zip with recipe.json
        recipe_zip_buffer = BytesIO()
        with zipfile.ZipFile(recipe_zip_buffer, "w") as recipe_zip:
            recipe_zip.writestr("recipe.json", json.dumps(recipe_data))

        # Create outer zip with the recipe zip
        main_zip_buffer = BytesIO()
        with zipfile.ZipFile(main_zip_buffer, "w") as main_zip:
            main_zip.writestr("1.zip", recipe_zip_buffer.getvalue())

        main_zip_buffer.seek(0)

        response = self.client.post(
            reverse("import_database_upload"),
            {
                "format": "tandoor",
                "import_file": main_zip_buffer,
            },
        )

        # Should redirect to preview
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith(reverse("import_database_preview")))  # type: ignore[attr-defined]

        # Check session data
        self.assertIn("import_recipes", self.client.session)
        recipes_data = self.client.session["import_recipes"]
        self.assertEqual(len(recipes_data), 1)
        self.assertEqual(recipes_data[0]["name"], "Test Recipe")

    def test_import_upload_plated_json(self) -> None:
        """Test uploading a Plated JSON file."""
        recipe_data = {
            "title": "Test Recipe",
            "description": "Test",
            "servings": 4,
            "ingredients": [{"name": "Flour", "amount": "500", "unit": "g", "order": 0}],
            "steps": [{"content": "Test step", "order": 0}],
            "prep_time_minutes": 30,
            "wait_time_minutes": None,
            "keywords": "",
            "url": "",
            "notes": "",
            "special_equipment": "",
            "images": [],
        }

        json_content = json.dumps(recipe_data).encode("utf-8")
        json_file = BytesIO(json_content)
        json_file.name = "recipe.json"

        response = self.client.post(
            reverse("import_database_upload"),
            {
                "format": "plated",
                "import_file": json_file,
            },
        )

        # Should redirect to preview
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith(reverse("import_database_preview")))  # type: ignore[attr-defined]

    def test_import_preview_page(self) -> None:
        """Test the import preview page."""
        # Set up session data
        session = self.client.session
        session["import_recipes"] = [
            {
                "json": json.dumps(
                    {
                        "title": "Recipe 1",
                        "description": "Test",
                        "servings": 2,
                        "ingredients": [],
                        "steps": [{"content": "Step 1", "order": 0}],
                    }
                ),
                "image": None,
                "name": "Recipe 1",
            }
        ]
        session["import_format"] = "plated"
        session.save()

        response = self.client.get(reverse("import_database_preview"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Import Preview")
        self.assertContains(response, "Recipe 1")
        self.assertContains(response, "Confirm Import")

    def test_import_preview_no_data(self) -> None:
        """Test preview page redirects if no import data."""
        response = self.client.get(reverse("import_database_preview"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith(reverse("settings")))  # type: ignore[attr-defined]

    def test_import_confirm_creates_recipes(self) -> None:
        """Test that confirm view creates recipes in database."""
        # Set up session data with a complete Plated recipe
        recipe_json = json.dumps(
            {
                "title": "Imported Recipe",
                "description": "Test import",
                "servings": 4,
                "ingredients": [{"name": "Salt", "amount": "1", "unit": "tsp", "order": 0}],
                "steps": [{"content": "Add salt", "order": 0}],
                "prep_time_minutes": 10,
                "wait_time_minutes": None,
                "keywords": "test",
                "url": "",
                "notes": "",
                "special_equipment": "",
                "images": [],
            }
        )

        # Need to modify session before POST
        session = self.client.session
        session["import_recipes"] = [{"json": recipe_json, "image": None, "name": "Imported Recipe"}]
        session["import_format"] = "plated"
        session.save()

        # Confirm there are no recipes yet
        self.assertEqual(Recipe.objects.count(), 0)

        # Post to confirm
        response = self.client.post(reverse("import_database_confirm"))

        # Should redirect to recipe list (which is at "/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("recipe_list"))  # type: ignore[attr-defined]

        # Check recipe was created
        self.assertEqual(Recipe.objects.count(), 1)
        recipe = Recipe.objects.first()
        self.assertIsNotNone(recipe)
        assert recipe is not None  # for mypy
        self.assertEqual(recipe.title, "Imported Recipe")
        self.assertEqual(recipe.servings, 4)
        self.assertEqual(recipe.ingredients.count(), 1)
        self.assertEqual(recipe.steps.count(), 1)

    def test_import_invalid_file(self) -> None:
        """Test uploading an invalid file."""
        invalid_file = BytesIO(b"not a valid file")
        invalid_file.name = "invalid.txt"

        response = self.client.post(
            reverse("import_database_upload"),
            {
                "format": "tandoor",
                "import_file": invalid_file,
            },
        )

        # Should redirect back to settings with error
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith(reverse("settings")))  # type: ignore[attr-defined]
