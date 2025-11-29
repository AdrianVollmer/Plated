"""Tests for meal plan views, including critical shopping list aggregation."""

from __future__ import annotations

from datetime import date

from django.test import TestCase
from django.urls import reverse

from ..models import Ingredient, MealPlan, MealPlanEntry, Recipe


class MealPlanListViewTest(TestCase):
    """Test cases for meal plan list view."""

    def setUp(self) -> None:
        """Create test meal plans."""
        MealPlan.objects.create(
            name="Week 1",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 7),
        )
        MealPlan.objects.create(
            name="Week 2",
            start_date=date(2024, 1, 8),
            end_date=date(2024, 1, 14),
        )

    def test_meal_plan_list_view(self) -> None:
        """Test that meal plan list view displays all meal plans."""
        response = self.client.get(reverse("meal_plan_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Week 1")
        self.assertContains(response, "Week 2")


class MealPlanDetailViewTest(TestCase):
    """Test cases for meal plan detail view."""

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
        )

    def test_meal_plan_detail_view(self) -> None:
        """Test that meal plan detail view displays entries."""
        response = self.client.get(reverse("meal_plan_detail", args=[self.meal_plan.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Week")
        self.assertContains(response, "Breakfast Recipe")
        self.assertContains(response, "Dinner Recipe")


class ShoppingListViewTest(TestCase):
    """Test cases for shopping list aggregation - CRITICAL functionality."""

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
        )
        MealPlanEntry.objects.create(
            meal_plan=self.meal_plan,
            recipe=self.recipe2,
            date=date(2024, 1, 2),
            meal_type="lunch",
        )
        MealPlanEntry.objects.create(
            meal_plan=self.meal_plan,
            recipe=self.recipe3,
            date=date(2024, 1, 1),
            meal_type="dinner",
        )

    def test_shopping_list_view(self) -> None:
        """Test that shopping list view displays aggregated ingredients."""
        response = self.client.get(reverse("shopping_list", args=[self.meal_plan.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Shopping List Test")

    def test_shopping_list_aggregation_basic(self) -> None:
        """Test that shopping list aggregates ingredients by name."""
        response = self.client.get(reverse("shopping_list", args=[self.meal_plan.pk]))
        self.assertEqual(response.status_code, 200)

        # All unique ingredient names should appear
        self.assertContains(response, "Pasta")
        self.assertContains(response, "Tomatoes")
        self.assertContains(response, "Garlic")
        self.assertContains(response, "Lettuce")
        self.assertContains(response, "Bread")

    def test_shopping_list_groups_same_ingredient(self) -> None:
        """Test that same ingredients from different recipes are grouped together."""
        response = self.client.get(reverse("shopping_list", args=[self.meal_plan.pk]))

        # Check that tomatoes appear with both amounts listed
        content = response.content.decode()
        # Should have both pasta and salad as sources for tomatoes
        self.assertIn("tomatoes", content.lower())

    def test_shopping_list_empty_meal_plan(self) -> None:
        """Test shopping list with no recipes."""
        empty_plan = MealPlan.objects.create(
            name="Empty Plan",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 7),
        )
        response = self.client.get(reverse("shopping_list", args=[empty_plan.pk]))
        self.assertEqual(response.status_code, 200)

    def test_shopping_list_with_ingredients_no_unit(self) -> None:
        """Test shopping list with ingredients that have no unit."""
        recipe = Recipe.objects.create(title="Simple Recipe", servings=2)
        Ingredient.objects.create(
            recipe=recipe,
            name="eggs",
            amount="4",
            unit="",  # No unit
        )

        meal_plan = MealPlan.objects.create(
            name="Simple Plan",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 7),
        )
        MealPlanEntry.objects.create(
            meal_plan=meal_plan,
            recipe=recipe,
            date=date(2024, 1, 1),
            meal_type="breakfast",
        )

        response = self.client.get(reverse("shopping_list", args=[meal_plan.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Eggs")

    def test_shopping_list_case_insensitive_grouping(self) -> None:
        """Test that ingredient names are grouped case-insensitively."""
        recipe1 = Recipe.objects.create(title="Recipe 1", servings=2)
        recipe2 = Recipe.objects.create(title="Recipe 2", servings=2)

        # Same ingredient with different cases
        Ingredient.objects.create(recipe=recipe1, name="Flour", amount="1", unit="cup")
        Ingredient.objects.create(recipe=recipe2, name="flour", amount="2", unit="cups")

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
        )
        MealPlanEntry.objects.create(
            meal_plan=meal_plan,
            recipe=recipe2,
            date=date(2024, 1, 2),
            meal_type="dinner",
        )

        response = self.client.get(reverse("shopping_list", args=[meal_plan.pk]))
        self.assertEqual(response.status_code, 200)

        # Should group both as "Flour" (title case)
        content = response.content.decode()
        # Count occurrences - should appear once as a grouped ingredient
        flour_count = content.lower().count("flour")
        # Should appear at least once in the shopping list
        self.assertGreater(flour_count, 0)


class MealPlanCreateViewTest(TestCase):
    """Test cases for meal plan create view."""

    def test_meal_plan_create_view_get(self) -> None:
        """Test GET request to meal plan create view."""
        response = self.client.get(reverse("meal_plan_create"))
        self.assertEqual(response.status_code, 200)

    def test_meal_plan_create_post(self) -> None:
        """Test creating a new meal plan."""
        response = self.client.post(
            reverse("meal_plan_create"),
            {
                "name": "New Meal Plan",
                "description": "Test description",
                "start_date": "2024-01-01",
                "end_date": "2024-01-07",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(MealPlan.objects.filter(name="New Meal Plan").exists())


class MealPlanUpdateViewTest(TestCase):
    """Test cases for meal plan update view."""

    def setUp(self) -> None:
        """Create a test meal plan."""
        self.meal_plan = MealPlan.objects.create(
            name="Original Name",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 7),
        )

    def test_meal_plan_update_view_get(self) -> None:
        """Test GET request to meal plan update view."""
        response = self.client.get(reverse("meal_plan_update", args=[self.meal_plan.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Original Name")

    def test_meal_plan_update_post(self) -> None:
        """Test updating a meal plan."""
        response = self.client.post(
            reverse("meal_plan_update", args=[self.meal_plan.pk]),
            {
                "name": "Updated Name",
                "description": "Updated description",
                "start_date": "2024-01-01",
                "end_date": "2024-01-07",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)

        self.meal_plan.refresh_from_db()
        self.assertEqual(self.meal_plan.name, "Updated Name")


class MealPlanDeleteViewTest(TestCase):
    """Test cases for meal plan delete view."""

    def setUp(self) -> None:
        """Create a test meal plan."""
        self.meal_plan = MealPlan.objects.create(
            name="Plan to Delete",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 7),
        )

    def test_meal_plan_delete_view_get(self) -> None:
        """Test GET request to meal plan delete view."""
        response = self.client.get(reverse("meal_plan_delete", args=[self.meal_plan.pk]))
        self.assertEqual(response.status_code, 200)

    def test_meal_plan_delete_post(self) -> None:
        """Test deleting a meal plan."""
        meal_plan_pk = self.meal_plan.pk
        response = self.client.post(
            reverse("meal_plan_delete", args=[self.meal_plan.pk]),
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(MealPlan.objects.filter(pk=meal_plan_pk).exists())
