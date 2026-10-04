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

    def test_detail_view_has_quick_edit_forms_prefilled(self) -> None:
        """Ingredients and steps carry a pre-filled quick-edit form for the template to render."""
        Step.objects.create(recipe=self.recipe, content="Mix everything", order=0)
        response = self.client.get(reverse("recipe_detail", args=[self.recipe.pk]))
        self.assertEqual(response.status_code, 200)
        ingredient = response.context["recipe"].ingredients.all()[0]
        step = response.context["recipe"].steps.all()[0]
        self.assertEqual(ingredient.quick_edit_form.initial["name"], ingredient.name)
        self.assertEqual(step.quick_edit_form.initial["content"], step.content)


class RecipeCreateViewTest(TestCase):
    """Test cases for the recipe create view."""

    def test_recipe_create_view_get(self) -> None:
        """Test GET request to recipe create view."""
        response = self.client.get(reverse("recipe_create"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "title")

    def test_recipe_create_basic(self) -> None:
        """Test creating a basic recipe with required ingredient and step."""
        response = self.client.post(
            reverse("recipe_create"),
            {
                "title": "New Recipe",
                "servings": 4,
                "description": "Test description",
                # At least one ingredient is required by validation
                "ingredients-TOTAL_FORMS": "1",
                "ingredients-INITIAL_FORMS": "0",
                "ingredients-0-name": "test ingredient",
                "ingredients-0-amount": "1",
                "ingredients-0-unit": "cup",
                "ingredients-0-order": "0",
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

    def test_recipe_create_with_empty_image_shows_readable_error(self) -> None:
        """Uploading a zero-byte image should show a clear message, not a raw error dump."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        response = self.client.post(
            reverse("recipe_create"),
            {
                "title": "Recipe With Bad Image",
                "servings": 2,
                "description": "",
                "ingredients-TOTAL_FORMS": "1",
                "ingredients-INITIAL_FORMS": "0",
                "ingredients-0-name": "flour",
                "ingredients-0-amount": "1",
                "ingredients-0-unit": "cup",
                "ingredients-0-order": "0",
                "steps-TOTAL_FORMS": "1",
                "steps-INITIAL_FORMS": "0",
                "steps-0-content": "Mix",
                "steps-0-order": "0",
                "images-TOTAL_FORMS": "1",
                "images-INITIAL_FORMS": "0",
                "images-0-image": SimpleUploadedFile("empty.jpg", b"", content_type="image/jpeg"),
                "images-0-caption": "",
                "images-0-order": "0",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Recipe.objects.filter(title="Recipe With Bad Image").exists())
        self.assertContains(response, "The submitted file is empty.")
        # The raw formset error list must never be dumped onto the page.
        self.assertNotContains(response, "[{")


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
        # Get the existing ingredient to preserve it
        existing_ingredient = self.recipe.ingredients.first()

        response = self.client.post(
            reverse("recipe_update", args=[self.recipe.pk]),
            {
                "title": "Updated Title",
                "servings": 4,
                "description": "Original description",
                # Existing ingredient - must include to satisfy validation
                "ingredients-TOTAL_FORMS": "1",
                "ingredients-INITIAL_FORMS": "1",
                "ingredients-0-id": str(existing_ingredient.pk) if existing_ingredient else "",
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


class RecipeCookingViewTest(TestCase):
    """Test cases for the cooking view."""

    def setUp(self) -> None:
        """Create a test recipe with ingredients and steps."""
        self.recipe = Recipe.objects.create(
            title="Scrambled Eggs",
            description="Simple breakfast",
            servings=2,
            special_equipment="Non-stick pan",
        )
        Ingredient.objects.create(
            recipe=self.recipe,
            name="eggs",
            amount="4",
            unit="",
            order=0,
        )
        Ingredient.objects.create(
            recipe=self.recipe,
            name="butter",
            amount="1",
            unit="tbsp",
            order=1,
        )
        Step.objects.create(
            recipe=self.recipe,
            content="Beat eggs in a bowl",
            order=0,
        )
        Step.objects.create(
            recipe=self.recipe,
            content="Melt butter in pan and cook eggs",
            order=1,
        )

    def test_cooking_view_renders(self) -> None:
        """Test that cooking view renders correctly."""
        response = self.client.get(reverse("recipe_cooking", args=[self.recipe.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "recipes/recipe_cooking.html")

    def test_cooking_view_shows_recipe_data(self) -> None:
        """Test that cooking view displays recipe information."""
        response = self.client.get(reverse("recipe_cooking", args=[self.recipe.pk]))
        self.assertEqual(response.status_code, 200)

        # Check recipe title
        self.assertContains(response, "Scrambled Eggs")

        # Check ingredients
        self.assertContains(response, "eggs")
        self.assertContains(response, "butter")
        self.assertContains(response, "4")
        self.assertContains(response, "1")
        self.assertContains(response, "tbsp")

        # Check steps
        self.assertContains(response, "Beat eggs in a bowl")
        self.assertContains(response, "Melt butter in pan and cook eggs")

        # Check special equipment
        self.assertContains(response, "Non-stick pan")

    def test_cooking_view_has_checkboxes(self) -> None:
        """Test that cooking view includes checkboxes for ingredients and steps."""
        response = self.client.get(reverse("recipe_cooking", args=[self.recipe.pk]))
        self.assertEqual(response.status_code, 200)

        # Check for checkbox inputs
        self.assertContains(response, 'type="checkbox"')
        self.assertContains(response, "ingredient-checkbox")
        self.assertContains(response, "step-checkbox")

    def test_cooking_view_loads_javascript(self) -> None:
        """Test that cooking view loads necessary JavaScript."""
        response = self.client.get(reverse("recipe_cooking", args=[self.recipe.pk]))
        self.assertEqual(response.status_code, 200)
        # Check for base filename (may have hash suffix for cache-busting)
        self.assertContains(response, "cooking-view")
        self.assertContains(response, "theme-switcher")

    def test_cooking_view_404_for_nonexistent_recipe(self) -> None:
        """Test that cooking view returns 404 for non-existent recipe."""
        response = self.client.get(reverse("recipe_cooking", args=[9999]))
        self.assertEqual(response.status_code, 404)

    def test_cooking_view_scaled_amounts(self) -> None:
        """Scaled amounts from ?scale= param appear in cooking view."""
        url = reverse("recipe_cooking", args=[self.recipe.pk]) + "?scale=2"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # 4 eggs * 2 = 8, 1 tbsp butter * 2 = 2
        self.assertContains(response, "8")  # scaled egg count
        # "4" (original egg count) must not appear as a standalone token in amounts
        # The response should contain "2" from butter and step numbers, but not "4"
        self.assertNotContains(response, ">4<")

    def test_cooking_view_scale_one_is_identity(self) -> None:
        """?scale=1 (or omitted) shows original amounts."""
        url = reverse("recipe_cooking", args=[self.recipe.pk]) + "?scale=1"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "4")
        self.assertContains(response, "1")

    def test_cooking_view_invalid_scale_ignored(self) -> None:
        """Invalid ?scale= falls back to original amounts."""
        url = reverse("recipe_cooking", args=[self.recipe.pk]) + "?scale=abc"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "4")

    def test_cooking_view_step_with_timer_renders_widget(self) -> None:
        """Steps with a timer produce a data-timer-minutes attribute and widget placeholder."""
        Step.objects.create(recipe=self.recipe, content="Simmer", order=2, timer=15)
        response = self.client.get(reverse("recipe_cooking", args=[self.recipe.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-timer-minutes="15"')
        self.assertContains(response, "step-timer-widget")

    def test_cooking_view_step_without_timer_has_no_widget(self) -> None:
        """Steps without a timer do not render a timer widget or data attribute."""
        response = self.client.get(reverse("recipe_cooking", args=[self.recipe.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "data-timer-minutes")
        self.assertNotContains(response, 'class="step-timer-widget"')


class IngredientQuickEditViewTest(TestCase):
    """Test cases for the ingredient quick-edit view."""

    def setUp(self) -> None:
        """Create a recipe with one ingredient."""
        self.recipe = Recipe.objects.create(title="Soup", servings=4)
        self.ingredient = Ingredient.objects.create(recipe=self.recipe, name="salt", amount="1", unit="tsp", order=0)

    def test_get_redirects_without_saving(self) -> None:
        """GET requests redirect back to the detail page without changing anything."""
        response = self.client.get(reverse("ingredient_quick_edit", args=[self.recipe.pk, self.ingredient.pk]))
        self.assertRedirects(
            response,
            f"{reverse('recipe_detail', args=[self.recipe.pk])}#ingredient-{self.ingredient.pk}",
        )
        self.ingredient.refresh_from_db()
        self.assertEqual(self.ingredient.amount, "1")

    def test_valid_post_updates_ingredient(self) -> None:
        """A valid POST updates the ingredient and redirects to the anchored detail page."""
        response = self.client.post(
            reverse("ingredient_quick_edit", args=[self.recipe.pk, self.ingredient.pk]),
            {"amount": "2", "unit": "tbsp", "name": "salt", "note": "to taste"},
        )
        self.assertRedirects(
            response,
            f"{reverse('recipe_detail', args=[self.recipe.pk])}#ingredient-{self.ingredient.pk}",
        )
        self.ingredient.refresh_from_db()
        self.assertEqual(self.ingredient.amount, "2")
        self.assertEqual(self.ingredient.unit, "tbsp")
        self.assertEqual(self.ingredient.note, "to taste")

    def test_invalid_post_does_not_save_and_shows_message(self) -> None:
        """An invalid POST (blank name) leaves the ingredient unchanged and flashes a message."""
        response = self.client.post(
            reverse("ingredient_quick_edit", args=[self.recipe.pk, self.ingredient.pk]),
            {"amount": "2", "unit": "tbsp", "name": "", "note": ""},
            follow=True,
        )
        self.ingredient.refresh_from_db()
        self.assertEqual(self.ingredient.amount, "1")
        self.assertEqual(self.ingredient.unit, "tsp")
        self.assertEqual(self.ingredient.note, "")
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertIn("Couldn't save ingredient", str(messages[0]))

    def test_post_for_ingredient_of_different_recipe_404s(self) -> None:
        """An ingredient that doesn't belong to the given recipe 404s."""
        other_recipe = Recipe.objects.create(title="Other", servings=2)
        response = self.client.post(
            reverse("ingredient_quick_edit", args=[other_recipe.pk, self.ingredient.pk]),
            {"amount": "2", "unit": "tbsp", "name": "salt", "note": ""},
        )
        self.assertEqual(response.status_code, 404)


class StepQuickEditViewTest(TestCase):
    """Test cases for the step quick-edit view."""

    def setUp(self) -> None:
        """Create a recipe with one step."""
        self.recipe = Recipe.objects.create(title="Soup", servings=4)
        self.step = Step.objects.create(recipe=self.recipe, content="Boil water", order=0)

    def test_get_redirects_without_saving(self) -> None:
        """GET requests redirect back to the detail page without changing anything."""
        response = self.client.get(reverse("step_quick_edit", args=[self.recipe.pk, self.step.pk]))
        self.assertRedirects(
            response,
            f"{reverse('recipe_detail', args=[self.recipe.pk])}#step-{self.step.pk}",
        )
        self.step.refresh_from_db()
        self.assertEqual(self.step.content, "Boil water")

    def test_valid_post_updates_step(self) -> None:
        """A valid POST updates the step and redirects to the anchored detail page."""
        response = self.client.post(
            reverse("step_quick_edit", args=[self.recipe.pk, self.step.pk]),
            {"content": "Boil the water for 5 minutes", "timer": "5"},
        )
        self.assertRedirects(
            response,
            f"{reverse('recipe_detail', args=[self.recipe.pk])}#step-{self.step.pk}",
        )
        self.step.refresh_from_db()
        self.assertEqual(self.step.content, "Boil the water for 5 minutes")
        self.assertEqual(self.step.timer, 5)

    def test_invalid_post_does_not_save_and_shows_message(self) -> None:
        """An invalid POST (blank content) leaves the step unchanged and flashes a message."""
        response = self.client.post(
            reverse("step_quick_edit", args=[self.recipe.pk, self.step.pk]),
            {"content": "", "timer": ""},
            follow=True,
        )
        self.step.refresh_from_db()
        self.assertEqual(self.step.content, "Boil water")
        self.assertIsNone(self.step.timer)
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertIn("Couldn't save step", str(messages[0]))

    def test_post_for_step_of_different_recipe_404s(self) -> None:
        """A step that doesn't belong to the given recipe 404s."""
        other_recipe = Recipe.objects.create(title="Other", servings=2)
        response = self.client.post(
            reverse("step_quick_edit", args=[other_recipe.pk, self.step.pk]),
            {"content": "Boil water", "timer": ""},
        )
        self.assertEqual(response.status_code, 404)
