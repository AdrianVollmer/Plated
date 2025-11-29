"""Tests for Recipe models."""

from __future__ import annotations

from datetime import timedelta

from django.test import TestCase

from ..models import Ingredient, MealPlan, MealPlanEntry, Recipe, RecipeCollection, Step


class RecipeModelTest(TestCase):
    """Test cases for the Recipe model."""

    def test_create_recipe(self) -> None:
        """Test creating a basic recipe."""
        recipe = Recipe.objects.create(
            title="Chocolate Cake",
            description="A delicious chocolate cake",
            servings=8,
            prep_time=timedelta(minutes=30),
            wait_time=timedelta(minutes=45),
            keywords="dessert, chocolate, cake",
        )
        self.assertEqual(recipe.title, "Chocolate Cake")
        self.assertEqual(recipe.servings, 8)
        self.assertEqual(recipe.prep_time, timedelta(minutes=30))

    def test_recipe_str(self) -> None:
        """Test the string representation of a recipe."""
        recipe = Recipe.objects.create(title="Test Recipe", servings=4)
        self.assertEqual(str(recipe), "Test Recipe")

    def test_recipe_with_ingredients(self) -> None:
        """Test creating a recipe with ingredients."""
        recipe = Recipe.objects.create(title="Pancakes", servings=4)
        Ingredient.objects.create(
            recipe=recipe,
            name="flour",
            amount="2",
            unit="cups",
            order=0,
        )
        Ingredient.objects.create(
            recipe=recipe,
            name="milk",
            amount="1",
            unit="cup",
            order=1,
        )

        self.assertEqual(recipe.ingredients.count(), 2)
        first_ingredient = recipe.ingredients.first()
        assert first_ingredient is not None  # Type narrowing for mypy
        self.assertEqual(first_ingredient.name, "flour")

    def test_recipe_with_steps(self) -> None:
        """Test creating a recipe with steps."""
        recipe = Recipe.objects.create(title="Simple Soup", servings=2)
        Step.objects.create(
            recipe=recipe,
            content="Boil water",
            order=0,
        )
        Step.objects.create(
            recipe=recipe,
            content="Add ingredients",
            order=1,
        )

        self.assertEqual(recipe.steps.count(), 2)
        first_step = recipe.steps.first()
        assert first_step is not None  # Type narrowing for mypy
        self.assertEqual(first_step.content, "Boil water")

    def test_recipe_deletion_cascades(self) -> None:
        """Test that deleting a recipe deletes its ingredients and steps."""
        recipe = Recipe.objects.create(title="Test Recipe", servings=4)
        Ingredient.objects.create(recipe=recipe, name="sugar", amount="1", unit="cup")
        Step.objects.create(recipe=recipe, content="Mix well", order=0)

        ingredient_count = Ingredient.objects.filter(recipe=recipe).count()
        step_count = Step.objects.filter(recipe=recipe).count()

        self.assertEqual(ingredient_count, 1)
        self.assertEqual(step_count, 1)

        recipe.delete()

        # Check that ingredients and steps are deleted
        self.assertEqual(Ingredient.objects.filter(recipe_id=recipe.pk).count(), 0)
        self.assertEqual(Step.objects.filter(recipe_id=recipe.pk).count(), 0)


class IngredientModelTest(TestCase):
    """Test cases for the Ingredient model."""

    def setUp(self) -> None:
        """Create a test recipe."""
        self.recipe = Recipe.objects.create(title="Test Recipe", servings=4)

    def test_create_ingredient(self) -> None:
        """Test creating an ingredient."""
        ingredient = Ingredient.objects.create(
            recipe=self.recipe,
            name="flour",
            amount="2",
            unit="cups",
            order=0,
        )
        self.assertEqual(ingredient.name, "flour")
        self.assertEqual(ingredient.amount, "2")
        self.assertEqual(ingredient.unit, "cups")

    def test_ingredient_str(self) -> None:
        """Test the string representation of an ingredient."""
        ingredient = Ingredient.objects.create(
            recipe=self.recipe,
            name="sugar",
            amount="1",
            unit="tbsp",
        )
        self.assertEqual(str(ingredient), "1 tbsp sugar")

    def test_ingredient_without_unit(self) -> None:
        """Test creating an ingredient without a unit."""
        ingredient = Ingredient.objects.create(
            recipe=self.recipe,
            name="eggs",
            amount="2",
            unit="",
        )
        self.assertEqual(str(ingredient), "2 eggs")

    def test_ingredient_ordering(self) -> None:
        """Test that ingredients are ordered correctly."""
        Ingredient.objects.create(recipe=self.recipe, name="c", amount="1", order=2)
        Ingredient.objects.create(recipe=self.recipe, name="a", amount="1", order=0)
        Ingredient.objects.create(recipe=self.recipe, name="b", amount="1", order=1)

        ingredients = list(self.recipe.ingredients.all())
        self.assertEqual(ingredients[0].name, "a")
        self.assertEqual(ingredients[1].name, "b")
        self.assertEqual(ingredients[2].name, "c")


class StepModelTest(TestCase):
    """Test cases for the Step model."""

    def setUp(self) -> None:
        """Create a test recipe."""
        self.recipe = Recipe.objects.create(title="Test Recipe", servings=4)

    def test_create_step(self) -> None:
        """Test creating a step."""
        step = Step.objects.create(
            recipe=self.recipe,
            content="Mix ingredients",
            order=0,
        )
        self.assertEqual(step.content, "Mix ingredients")
        self.assertEqual(step.order, 0)

    def test_step_str(self) -> None:
        """Test the string representation of a step."""
        step = Step.objects.create(
            recipe=self.recipe,
            content="Bake at 350°F",
            order=0,
        )
        self.assertIn("Step", str(step))
        self.assertIn("Bake at 350°F", str(step))

    def test_step_ordering(self) -> None:
        """Test that steps are ordered correctly."""
        Step.objects.create(recipe=self.recipe, content="Third", order=2)
        Step.objects.create(recipe=self.recipe, content="First", order=0)
        Step.objects.create(recipe=self.recipe, content="Second", order=1)

        steps = list(self.recipe.steps.all())
        self.assertEqual(steps[0].content, "First")
        self.assertEqual(steps[1].content, "Second")
        self.assertEqual(steps[2].content, "Third")


class RecipeCollectionModelTest(TestCase):
    """Test cases for the RecipeCollection model."""

    def test_create_collection(self) -> None:
        """Test creating a recipe collection."""
        collection = RecipeCollection.objects.create(
            name="Desserts",
            description="Sweet treats",
        )
        self.assertEqual(collection.name, "Desserts")
        self.assertEqual(collection.description, "Sweet treats")

    def test_collection_str(self) -> None:
        """Test the string representation of a collection."""
        collection = RecipeCollection.objects.create(name="Breakfast")
        self.assertEqual(str(collection), "Breakfast")

    def test_collection_with_recipes(self) -> None:
        """Test adding recipes to a collection."""
        collection = RecipeCollection.objects.create(name="Quick Meals")
        recipe1 = Recipe.objects.create(title="Omelette", servings=2)
        recipe2 = Recipe.objects.create(title="Salad", servings=2)

        collection.recipes.add(recipe1, recipe2)

        self.assertEqual(collection.recipes.count(), 2)
        self.assertIn(recipe1, collection.recipes.all())
        self.assertIn(recipe2, collection.recipes.all())


class MealPlanModelTest(TestCase):
    """Test cases for the MealPlan model."""

    def test_create_meal_plan(self) -> None:
        """Test creating a meal plan."""
        from datetime import date

        meal_plan = MealPlan.objects.create(
            name="Week 1",
            description="First week of January",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 7),
        )
        self.assertEqual(meal_plan.name, "Week 1")
        self.assertEqual(meal_plan.start_date, date(2024, 1, 1))

    def test_meal_plan_str(self) -> None:
        """Test the string representation of a meal plan."""
        from datetime import date

        meal_plan = MealPlan.objects.create(
            name="Weekly Plan",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 7),
        )
        self.assertEqual(str(meal_plan), "Weekly Plan")

    def test_meal_plan_with_entries(self) -> None:
        """Test adding entries to a meal plan."""
        from datetime import date

        meal_plan = MealPlan.objects.create(
            name="Test Plan",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 7),
        )
        recipe = Recipe.objects.create(title="Pasta", servings=4)

        MealPlanEntry.objects.create(
            meal_plan=meal_plan,
            recipe=recipe,
            date=date(2024, 1, 1),
            meal_type="dinner",
            servings=4,
        )

        self.assertEqual(meal_plan.entries.count(), 1)
        first_entry = meal_plan.entries.first()
        assert first_entry is not None  # Type narrowing for mypy
        self.assertEqual(first_entry.recipe, recipe)


class MealPlanEntryModelTest(TestCase):
    """Test cases for the MealPlanEntry model."""

    def setUp(self) -> None:
        """Create test meal plan and recipe."""
        from datetime import date

        self.meal_plan = MealPlan.objects.create(
            name="Test Plan",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 7),
        )
        self.recipe = Recipe.objects.create(title="Test Recipe", servings=4)

    def test_create_meal_plan_entry(self) -> None:
        """Test creating a meal plan entry."""
        from datetime import date

        entry = MealPlanEntry.objects.create(
            meal_plan=self.meal_plan,
            recipe=self.recipe,
            date=date(2024, 1, 1),
            meal_type="lunch",
            servings=2,
            notes="Half recipe",
        )
        self.assertEqual(entry.meal_type, "lunch")
        self.assertEqual(entry.servings, 2)
        self.assertEqual(entry.notes, "Half recipe")

    def test_meal_plan_entry_str(self) -> None:
        """Test the string representation of a meal plan entry."""
        from datetime import date

        entry = MealPlanEntry.objects.create(
            meal_plan=self.meal_plan,
            recipe=self.recipe,
            date=date(2024, 1, 1),
            meal_type="breakfast",
        )
        self.assertIn("Test Recipe", str(entry))
        self.assertIn("breakfast", str(entry))
