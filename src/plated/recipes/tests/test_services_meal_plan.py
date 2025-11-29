"""Tests for the meal plan service layer - critical business logic."""

from __future__ import annotations

from datetime import date

from django.test import TestCase

from ..models import Ingredient, MealPlan, MealPlanEntry, Recipe
from ..services import meal_plan_service


class AggregateShoppingListTest(TestCase):
    """Test cases for shopping list aggregation logic."""

    def setUp(self) -> None:
        """Create meal plan with multiple recipes containing various ingredients."""
        self.meal_plan = MealPlan.objects.create(
            name="Shopping List Test",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 7),
        )

        # Recipe 1: Pasta
        self.recipe1 = Recipe.objects.create(title="Pasta", servings=4)
        Ingredient.objects.create(
            recipe=self.recipe1,
            name="pasta",
            amount="1",
            unit="lb",
            order=0,
        )
        Ingredient.objects.create(
            recipe=self.recipe1,
            name="tomatoes",
            amount="2",
            unit="cups",
            order=1,
        )
        Ingredient.objects.create(
            recipe=self.recipe1,
            name="garlic",
            amount="3",
            unit="cloves",
            order=2,
        )

        # Recipe 2: Salad (shares tomatoes with recipe 1)
        self.recipe2 = Recipe.objects.create(title="Salad", servings=2)
        Ingredient.objects.create(
            recipe=self.recipe2,
            name="lettuce",
            amount="1",
            unit="head",
            order=0,
        )
        Ingredient.objects.create(
            recipe=self.recipe2,
            name="tomatoes",
            amount="1",
            unit="cup",
            order=1,
        )

        # Recipe 3: Garlic Bread (shares garlic)
        self.recipe3 = Recipe.objects.create(title="Garlic Bread", servings=4)
        Ingredient.objects.create(
            recipe=self.recipe3,
            name="bread",
            amount="1",
            unit="loaf",
            order=0,
        )
        Ingredient.objects.create(
            recipe=self.recipe3,
            name="garlic",
            amount="4",
            unit="cloves",
            order=1,
        )

        # Add recipes to meal plan
        MealPlanEntry.objects.create(
            meal_plan=self.meal_plan,
            recipe=self.recipe1,
            date=date(2024, 1, 1),
            meal_type="dinner",
            servings=4,  # Match recipe servings
        )
        MealPlanEntry.objects.create(
            meal_plan=self.meal_plan,
            recipe=self.recipe2,
            date=date(2024, 1, 2),
            meal_type="lunch",
            servings=2,  # Match recipe servings
        )
        MealPlanEntry.objects.create(
            meal_plan=self.meal_plan,
            recipe=self.recipe3,
            date=date(2024, 1, 1),
            meal_type="dinner",
            servings=4,  # Match recipe servings
        )

    def test_aggregate_shopping_list_basic(self) -> None:
        """Test basic shopping list aggregation."""
        # Prefetch data as the view does
        meal_plan = MealPlan.objects.prefetch_related("entries__recipe__ingredients").get(pk=self.meal_plan.pk)

        ingredients_list = meal_plan_service.aggregate_shopping_list(meal_plan)

        # Should return a list of tuples (name, display_amount)
        self.assertIsInstance(ingredients_list, list)
        self.assertGreater(len(ingredients_list), 0)

        # Check that all ingredients are tuples
        for item in ingredients_list:
            self.assertIsInstance(item, tuple)
            self.assertEqual(len(item), 2)

    def test_aggregate_shopping_list_groups_same_ingredient(self) -> None:
        """Test that ingredients with same name and unit are aggregated."""
        meal_plan = MealPlan.objects.prefetch_related("entries__recipe__ingredients").get(pk=self.meal_plan.pk)

        ingredients_list = meal_plan_service.aggregate_shopping_list(meal_plan)
        ingredients_dict = dict(ingredients_list)

        # Garlic should be aggregated: 3 + 4 = 7 cloves
        self.assertIn("garlic", ingredients_dict)
        self.assertIn("7 cloves", ingredients_dict["garlic"])

        # Tomatoes have different units ("cups" vs "cup"), so they appear separately
        # This is correct behavior - units must match exactly for aggregation
        self.assertIn("tomatoes", ingredients_dict)
        tomatoes_display = ingredients_dict["tomatoes"]
        # Should have both "1 cup" and "2 cups" (the original amounts from recipes)
        self.assertIn("cup", tomatoes_display)
        self.assertIn("cups", tomatoes_display)

    def test_aggregate_shopping_list_same_unit_aggregation(self) -> None:
        """Test that ingredients with exact same unit are properly aggregated."""
        # Create two recipes with butter using the same unit
        recipe4 = Recipe.objects.create(title="Recipe 4", servings=2)
        Ingredient.objects.create(
            recipe=recipe4,
            name="butter",
            amount="2",
            unit="tbsp",
            order=0,
        )
        recipe5 = Recipe.objects.create(title="Recipe 5", servings=2)
        Ingredient.objects.create(
            recipe=recipe5,
            name="butter",
            amount="3",
            unit="tbsp",
            order=0,
        )

        MealPlanEntry.objects.create(
            meal_plan=self.meal_plan,
            recipe=recipe4,
            date=date(2024, 1, 3),
            meal_type="breakfast",
            servings=2,
        )
        MealPlanEntry.objects.create(
            meal_plan=self.meal_plan,
            recipe=recipe5,
            date=date(2024, 1, 4),
            meal_type="lunch",
            servings=2,
        )

        meal_plan = MealPlan.objects.prefetch_related("entries__recipe__ingredients").get(pk=self.meal_plan.pk)

        ingredients_list = meal_plan_service.aggregate_shopping_list(meal_plan)
        ingredients_dict = dict(ingredients_list)

        # Butter should be aggregated: 2 + 3 = 5 tbsp
        self.assertIn("butter", ingredients_dict)
        self.assertEqual("5 tbsp", ingredients_dict["butter"])

    def test_aggregate_shopping_list_different_units(self) -> None:
        """Test that ingredients with same name but different units are separate."""
        # Add a recipe with tomatoes in a different unit
        recipe4 = Recipe.objects.create(title="Recipe 4", servings=2)
        Ingredient.objects.create(
            recipe=recipe4,
            name="tomatoes",
            amount="2",
            unit="whole",
            order=0,
        )
        MealPlanEntry.objects.create(
            meal_plan=self.meal_plan,
            recipe=recipe4,
            date=date(2024, 1, 3),
            meal_type="breakfast",
            servings=2,
        )

        meal_plan = MealPlan.objects.prefetch_related("entries__recipe__ingredients").get(pk=self.meal_plan.pk)

        ingredients_list = meal_plan_service.aggregate_shopping_list(meal_plan)
        ingredients_dict = dict(ingredients_list)

        # Tomatoes should have multiple units listed
        self.assertIn("tomatoes", ingredients_dict)
        tomatoes_display = ingredients_dict["tomatoes"]
        self.assertIn("cup", tomatoes_display)
        self.assertIn("whole", tomatoes_display)

    def test_aggregate_shopping_list_fractional_amounts(self) -> None:
        """Test aggregation of fractional ingredient amounts."""
        recipe = Recipe.objects.create(title="Fractional Recipe", servings=2)
        Ingredient.objects.create(
            recipe=recipe,
            name="flour",
            amount="1/2",
            unit="cup",
            order=0,
        )

        meal_plan = MealPlan.objects.create(
            name="Fraction Test",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 7),
        )
        # Add same recipe twice
        MealPlanEntry.objects.create(
            meal_plan=meal_plan,
            recipe=recipe,
            date=date(2024, 1, 1),
            meal_type="breakfast",
            servings=2,
        )
        MealPlanEntry.objects.create(
            meal_plan=meal_plan,
            recipe=recipe,
            date=date(2024, 1, 2),
            meal_type="breakfast",
            servings=2,
        )

        meal_plan = MealPlan.objects.prefetch_related("entries__recipe__ingredients").get(pk=meal_plan.pk)

        ingredients_list = meal_plan_service.aggregate_shopping_list(meal_plan)
        ingredients_dict = dict(ingredients_list)

        # Should aggregate: 1/2 + 1/2 = 1
        self.assertIn("flour", ingredients_dict)
        self.assertIn("1 cup", ingredients_dict["flour"])

    def test_aggregate_shopping_list_servings_multiplier(self) -> None:
        """Test that servings multiplier is applied correctly."""
        recipe = Recipe.objects.create(title="Test Recipe", servings=2)
        Ingredient.objects.create(
            recipe=recipe,
            name="sugar",
            amount="1",
            unit="cup",
            order=0,
        )

        meal_plan = MealPlan.objects.create(
            name="Servings Test",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 7),
        )
        # Double the servings (2 -> 4)
        MealPlanEntry.objects.create(
            meal_plan=meal_plan,
            recipe=recipe,
            date=date(2024, 1, 1),
            meal_type="breakfast",
            servings=4,
        )

        meal_plan = MealPlan.objects.prefetch_related("entries__recipe__ingredients").get(pk=meal_plan.pk)

        ingredients_list = meal_plan_service.aggregate_shopping_list(meal_plan)
        ingredients_dict = dict(ingredients_list)

        # Should double the amount: 1 * (4/2) = 2
        self.assertIn("sugar", ingredients_dict)
        self.assertIn("2 cup", ingredients_dict["sugar"])

    def test_aggregate_shopping_list_non_numeric_amounts(self) -> None:
        """Test handling of non-numeric ingredient amounts."""
        recipe = Recipe.objects.create(title="Non-numeric Recipe", servings=2)
        Ingredient.objects.create(
            recipe=recipe,
            name="salt",
            amount="to taste",
            unit="",
            order=0,
        )

        meal_plan = MealPlan.objects.create(
            name="Non-numeric Test",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 7),
        )
        MealPlanEntry.objects.create(
            meal_plan=meal_plan,
            recipe=recipe,
            date=date(2024, 1, 1),
            meal_type="dinner",
            servings=2,
        )

        meal_plan = MealPlan.objects.prefetch_related("entries__recipe__ingredients").get(pk=meal_plan.pk)

        ingredients_list = meal_plan_service.aggregate_shopping_list(meal_plan)
        ingredients_dict = dict(ingredients_list)

        # Should preserve non-numeric amounts
        self.assertIn("salt", ingredients_dict)
        self.assertIn("to taste", ingredients_dict["salt"])

    def test_aggregate_shopping_list_empty_meal_plan(self) -> None:
        """Test shopping list with no entries."""
        empty_plan = MealPlan.objects.create(
            name="Empty Plan",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 7),
        )

        ingredients_list = meal_plan_service.aggregate_shopping_list(empty_plan)

        # Should return empty list
        self.assertEqual(ingredients_list, [])

    def test_aggregate_shopping_list_case_insensitive(self) -> None:
        """Test that ingredient names are grouped case-insensitively."""
        recipe1 = Recipe.objects.create(title="Recipe 1", servings=2)
        recipe2 = Recipe.objects.create(title="Recipe 2", servings=2)

        # Same ingredient with different cases
        Ingredient.objects.create(recipe=recipe1, name="Flour", amount="1", unit="cup")
        Ingredient.objects.create(recipe=recipe2, name="flour", amount="2", unit="cup")

        meal_plan = MealPlan.objects.create(
            name="Case Test",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 7),
        )
        MealPlanEntry.objects.create(
            meal_plan=meal_plan,
            recipe=recipe1,
            date=date(2024, 1, 1),
            meal_type="dinner",
            servings=2,
        )
        MealPlanEntry.objects.create(
            meal_plan=meal_plan,
            recipe=recipe2,
            date=date(2024, 1, 2),
            meal_type="dinner",
            servings=2,
        )

        meal_plan = MealPlan.objects.prefetch_related("entries__recipe__ingredients").get(pk=meal_plan.pk)

        ingredients_list = meal_plan_service.aggregate_shopping_list(meal_plan)
        ingredients_dict = dict(ingredients_list)

        # Should group both as "flour" and aggregate amounts: 1 + 2 = 3
        self.assertIn("flour", ingredients_dict)
        self.assertIn("3 cup", ingredients_dict["flour"])

        # Should only appear once in the list
        flour_items = [name for name, _ in ingredients_list if name.lower() == "flour"]
        self.assertEqual(len(flour_items), 1)

    def test_aggregate_shopping_list_sorted_alphabetically(self) -> None:
        """Test that shopping list is sorted alphabetically by ingredient name."""
        meal_plan = MealPlan.objects.prefetch_related("entries__recipe__ingredients").get(pk=self.meal_plan.pk)

        ingredients_list = meal_plan_service.aggregate_shopping_list(meal_plan)
        names = [name for name, _ in ingredients_list]

        # Should be sorted alphabetically
        self.assertEqual(names, sorted(names))


class PrepareMealPlanPdfDataTest(TestCase):
    """Test cases for meal plan PDF data preparation."""

    def setUp(self) -> None:
        """Create a test meal plan with entries."""
        self.meal_plan = MealPlan.objects.create(
            name="Test Week",
            description="Test meal plan",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 7),
        )
        self.recipe1 = Recipe.objects.create(title="Breakfast Recipe", servings=2)
        self.recipe2 = Recipe.objects.create(title="Dinner Recipe", servings=4)

        MealPlanEntry.objects.create(
            meal_plan=self.meal_plan,
            recipe=self.recipe1,
            date=date(2024, 1, 1),
            meal_type="breakfast",
            servings=2,
        )
        MealPlanEntry.objects.create(
            meal_plan=self.meal_plan,
            recipe=self.recipe2,
            date=date(2024, 1, 1),
            meal_type="dinner",
            servings=4,
            notes="Extra spicy",
        )

    def test_prepare_meal_plan_pdf_data_structure(self) -> None:
        """Test that PDF data has correct structure."""
        meal_plan = MealPlan.objects.prefetch_related("entries__recipe").get(pk=self.meal_plan.pk)

        data = meal_plan_service.prepare_meal_plan_pdf_data(meal_plan)

        # Check top-level keys
        self.assertIn("name", data)
        self.assertIn("description", data)
        self.assertIn("start_date", data)
        self.assertIn("end_date", data)
        self.assertIn("entries", data)

        # Check values
        self.assertEqual(data["name"], "Test Week")
        self.assertEqual(data["description"], "Test meal plan")
        self.assertEqual(data["start_date"], "2024-01-01")
        self.assertEqual(data["end_date"], "2024-01-07")

        # Check entries
        self.assertEqual(len(data["entries"]), 2)

    def test_prepare_meal_plan_pdf_data_entries(self) -> None:
        """Test that entry data is correctly formatted."""
        meal_plan = MealPlan.objects.prefetch_related("entries__recipe").get(pk=self.meal_plan.pk)

        data = meal_plan_service.prepare_meal_plan_pdf_data(meal_plan)

        # Check first entry
        entry1 = data["entries"][0]
        self.assertEqual(entry1["date"], "2024-01-01")
        self.assertEqual(entry1["meal_type"], "breakfast")
        self.assertEqual(entry1["recipe_title"], "Breakfast Recipe")
        self.assertEqual(entry1["servings"], 2)

        # Check second entry with notes
        entry2 = data["entries"][1]
        self.assertEqual(entry2["notes"], "Extra spicy")


class PrepareShoppingListPdfDataTest(TestCase):
    """Test cases for shopping list PDF data preparation."""

    def setUp(self) -> None:
        """Create meal plan with recipes and ingredients."""
        self.meal_plan = MealPlan.objects.create(
            name="Shopping Test",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 7),
        )

        self.recipe1 = Recipe.objects.create(title="Recipe 1", servings=2)
        Ingredient.objects.create(
            recipe=self.recipe1,
            name="flour",
            amount="1",
            unit="cup",
            order=0,
        )

        self.recipe2 = Recipe.objects.create(title="Recipe 2", servings=2)
        Ingredient.objects.create(
            recipe=self.recipe2,
            name="sugar",
            amount="2",
            unit="cups",
            order=0,
        )

        MealPlanEntry.objects.create(
            meal_plan=self.meal_plan,
            recipe=self.recipe1,
            date=date(2024, 1, 1),
            meal_type="breakfast",
            servings=2,
        )
        MealPlanEntry.objects.create(
            meal_plan=self.meal_plan,
            recipe=self.recipe2,
            date=date(2024, 1, 2),
            meal_type="lunch",
            servings=2,
        )

    def test_prepare_shopping_list_pdf_data_structure(self) -> None:
        """Test that PDF data has correct structure."""
        meal_plan = MealPlan.objects.prefetch_related("entries__recipe__ingredients").get(pk=self.meal_plan.pk)

        data = meal_plan_service.prepare_shopping_list_pdf_data(meal_plan)

        # Check top-level keys
        self.assertIn("meal_plan_name", data)
        self.assertIn("start_date", data)
        self.assertIn("end_date", data)
        self.assertIn("ingredients", data)
        self.assertIn("recipe_count", data)

        # Check values
        self.assertEqual(data["meal_plan_name"], "Shopping Test")
        self.assertEqual(data["start_date"], "2024-01-01")
        self.assertEqual(data["end_date"], "2024-01-07")
        self.assertEqual(data["recipe_count"], 2)

    def test_prepare_shopping_list_pdf_data_ingredients(self) -> None:
        """Test that ingredients are correctly formatted."""
        meal_plan = MealPlan.objects.prefetch_related("entries__recipe__ingredients").get(pk=self.meal_plan.pk)

        data = meal_plan_service.prepare_shopping_list_pdf_data(meal_plan)

        # Should have 2 ingredients
        self.assertEqual(len(data["ingredients"]), 2)

        # Check ingredient structure
        ingredient = data["ingredients"][0]
        self.assertIn("name", ingredient)
        self.assertIn("items", ingredient)
        self.assertIn("total_amount", ingredient)

    def test_prepare_shopping_list_pdf_data_sorted(self) -> None:
        """Test that ingredients are sorted alphabetically."""
        meal_plan = MealPlan.objects.prefetch_related("entries__recipe__ingredients").get(pk=self.meal_plan.pk)

        data = meal_plan_service.prepare_shopping_list_pdf_data(meal_plan)

        # Get ingredient names
        names = [ing["name"] for ing in data["ingredients"]]

        # Should be sorted: "Flour" before "Sugar"
        self.assertEqual(names, sorted(names))
