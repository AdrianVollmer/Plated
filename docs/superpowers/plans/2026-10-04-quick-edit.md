# Quick-Edit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users fix a single ingredient's amount/unit/name/note, or a single step's
content/timer, from a small modal on the recipe detail page, without opening the full
`recipe_update` edit form.

**Architecture:** Two small `ModelForm`s (`IngredientQuickEditForm`, `StepQuickEditForm`) and two
plain function-based views (mirroring the existing `add_recipe_to_collections` view), each scoped
to one `Ingredient`/`Step` row and reached via its own URL
(`/recipe/<recipe_pk>/ingredient/<pk>/quick-edit/`, `/recipe/<recipe_pk>/step/<pk>/quick-edit/`).
`RecipeDetailView` prefetches ingredients/steps and attaches a pre-filled form instance to each
object so the template can render one Bootstrap modal per item with no JS needed to populate
fields. A pencil-icon button on each row opens its modal via Bootstrap's own
`data-bs-toggle`/`data-bs-target` attributes.

**Tech Stack:** Django 5 (forms, class-based + function-based views), Bootstrap 5 modals,
vanilla JS only for the existing theme/scaling scripts (none added by this feature).

**Spec:** `docs/superpowers/specs/2026-10-04-quick-edit-design.md`

---

## File Structure

- Modify `src/plated/recipes/forms.py` — add `IngredientQuickEditForm`, `StepQuickEditForm`.
- Modify `src/plated/recipes/views/recipes.py` — add `get_queryset` to `RecipeDetailView` (prefetch
  + attach forms), add `ingredient_quick_edit` and `step_quick_edit` view functions.
- Modify `src/plated/recipes/urls.py` — add the two quick-edit URL patterns.
- Create `src/plated/templates/recipes/_ingredient_quick_edit_modal.html` — one ingredient's modal.
- Create `src/plated/templates/recipes/_step_quick_edit_modal.html` — one step's modal.
- Modify `src/plated/templates/recipes/recipe_detail.html` — add edit buttons + `id` attributes to
  ingredient/step rows, include the two new modal partials.
- Modify `src/plated/static/styles.css` — minor layout rules for the new edit button and the step
  content wrapper.
- Modify `src/plated/recipes/tests/test_forms.py` — form validation tests.
- Modify `src/plated/recipes/tests/test_views_recipes.py` — view tests.
- Modify `docs/features.md` — document the feature.

---

### Task 1: `IngredientQuickEditForm`

**Files:**
- Modify: `src/plated/recipes/forms.py`
- Test: `src/plated/recipes/tests/test_forms.py`

- [ ] **Step 1: Write the failing tests**

Add to `src/plated/recipes/tests/test_forms.py`. First update the imports at the top of the file:

```python
from ..forms import (
    AIRecipeExtractionForm,
    AISettingsForm,
    IngredientQuickEditForm,
    RecipeForm,
    StepQuickEditForm,
    UserSettingsForm,
)
from ..models import Ingredient, Recipe, Step
```

Then append this class at the end of the file:

```python
class IngredientQuickEditFormTest(TestCase):
    """Test cases for IngredientQuickEditForm validation."""

    def setUp(self) -> None:
        """Create a recipe with one ingredient."""
        self.recipe = Recipe.objects.create(title="Soup", servings=4)
        self.ingredient = Ingredient.objects.create(
            recipe=self.recipe, name="salt", amount="1", unit="tsp", order=0
        )

    def test_valid_data_updates_ingredient(self) -> None:
        """Valid data saves onto the existing ingredient instance."""
        form = IngredientQuickEditForm(
            data={"amount": "2", "unit": "tbsp", "name": "salt", "note": "to taste"},
            instance=self.ingredient,
        )
        self.assertTrue(form.is_valid())
        ingredient = form.save()
        self.assertEqual(ingredient.pk, self.ingredient.pk)
        self.assertEqual(ingredient.amount, "2")
        self.assertEqual(ingredient.unit, "tbsp")
        self.assertEqual(ingredient.note, "to taste")

    def test_blank_name_is_invalid(self) -> None:
        """Name is required, so a blank value fails validation."""
        form = IngredientQuickEditForm(
            data={"amount": "2", "unit": "tbsp", "name": "", "note": ""},
            instance=self.ingredient,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_blank_amount_unit_note_are_valid(self) -> None:
        """Amount, unit, and note are optional."""
        form = IngredientQuickEditForm(
            data={"amount": "", "unit": "", "name": "salt", "note": ""},
            instance=self.ingredient,
        )
        self.assertTrue(form.is_valid())
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python src/plated/manage.py test recipes.tests.test_forms.IngredientQuickEditFormTest -v 2`
Expected: FAIL/ERROR — `ImportError: cannot import name 'IngredientQuickEditForm'`

- [ ] **Step 3: Implement the form**

In `src/plated/recipes/forms.py`, change the models import at the top from:

```python
from .models import AISettings, Recipe, UserSettings
```

to:

```python
from .models import AISettings, Ingredient, Recipe, Step, UserSettings
```

Then add this class directly after `RecipeForm` (i.e. right before `class AISettingsForm`):

```python
class IngredientQuickEditForm(forms.ModelForm):
    """Quick-edit form for a single ingredient's amount/unit/name/note."""

    class Meta:
        model = Ingredient
        fields = ["amount", "unit", "name", "note"]
        widgets = {
            "amount": forms.TextInput(attrs={"class": "form-control"}),
            "unit": forms.TextInput(attrs={"class": "form-control"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "note": forms.TextInput(attrs={"class": "form-control"}),
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python src/plated/manage.py test recipes.tests.test_forms.IngredientQuickEditFormTest -v 2`
Expected: `OK` (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/plated/recipes/forms.py src/plated/recipes/tests/test_forms.py
git commit -m "feat(recipes): add IngredientQuickEditForm"
```

---

### Task 2: `StepQuickEditForm`

**Files:**
- Modify: `src/plated/recipes/forms.py`
- Test: `src/plated/recipes/tests/test_forms.py`

- [ ] **Step 1: Write the failing tests**

Append to `src/plated/recipes/tests/test_forms.py` (the `StepQuickEditForm` and `Step` imports were
already added in Task 1):

```python
class StepQuickEditFormTest(TestCase):
    """Test cases for StepQuickEditForm validation."""

    def setUp(self) -> None:
        """Create a recipe with one step."""
        self.recipe = Recipe.objects.create(title="Soup", servings=4)
        self.step = Step.objects.create(recipe=self.recipe, content="Boil water", order=0)

    def test_valid_data_updates_step(self) -> None:
        """Valid data saves onto the existing step instance."""
        form = StepQuickEditForm(
            data={"content": "Boil the water for 5 minutes", "timer": "5"},
            instance=self.step,
        )
        self.assertTrue(form.is_valid())
        step = form.save()
        self.assertEqual(step.pk, self.step.pk)
        self.assertEqual(step.content, "Boil the water for 5 minutes")
        self.assertEqual(step.timer, 5)

    def test_blank_content_is_invalid(self) -> None:
        """Content is required, so a blank value fails validation."""
        form = StepQuickEditForm(data={"content": "", "timer": ""}, instance=self.step)
        self.assertFalse(form.is_valid())
        self.assertIn("content", form.errors)

    def test_blank_timer_is_valid(self) -> None:
        """Timer is optional."""
        form = StepQuickEditForm(data={"content": "Boil water", "timer": ""}, instance=self.step)
        self.assertTrue(form.is_valid())
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python src/plated/manage.py test recipes.tests.test_forms.StepQuickEditFormTest -v 2`
Expected: FAIL/ERROR — `ImportError: cannot import name 'StepQuickEditForm'`

- [ ] **Step 3: Implement the form**

Add this class in `src/plated/recipes/forms.py` directly after `IngredientQuickEditForm`:

```python
class StepQuickEditForm(forms.ModelForm):
    """Quick-edit form for a single step's content/timer."""

    class Meta:
        model = Step
        fields = ["content", "timer"]
        widgets = {
            "content": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "timer": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python src/plated/manage.py test recipes.tests.test_forms.StepQuickEditFormTest -v 2`
Expected: `OK` (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/plated/recipes/forms.py src/plated/recipes/tests/test_forms.py
git commit -m "feat(recipes): add StepQuickEditForm"
```

---

### Task 3: `ingredient_quick_edit` view + URL

**Files:**
- Modify: `src/plated/recipes/views/recipes.py`
- Modify: `src/plated/recipes/urls.py`
- Test: `src/plated/recipes/tests/test_views_recipes.py`

- [ ] **Step 1: Write the failing tests**

Append to `src/plated/recipes/tests/test_views_recipes.py` (at the end of the file). First check
the top-of-file import includes `Ingredient` (it already does per the existing
`from ..models import Ingredient, Recipe, Step` line):

```python
class IngredientQuickEditViewTest(TestCase):
    """Test cases for the ingredient quick-edit view."""

    def setUp(self) -> None:
        """Create a recipe with one ingredient."""
        self.recipe = Recipe.objects.create(title="Soup", servings=4)
        self.ingredient = Ingredient.objects.create(
            recipe=self.recipe, name="salt", amount="1", unit="tsp", order=0
        )

    def test_get_redirects_without_saving(self) -> None:
        """GET requests redirect back to the detail page without changing anything."""
        response = self.client.get(
            reverse("ingredient_quick_edit", args=[self.recipe.pk, self.ingredient.pk])
        )
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python src/plated/manage.py test recipes.tests.test_views_recipes.IngredientQuickEditViewTest -v 2`
Expected: FAIL — `NoReverseMatch: Reverse for 'ingredient_quick_edit' not found`

- [ ] **Step 3: Implement the view**

In `src/plated/recipes/views/recipes.py`, update the imports:

```python
from django.urls import reverse, reverse_lazy
```

(adds `reverse` alongside the existing `reverse_lazy`), and:

```python
from ..forms import IngredientQuickEditForm, RecipeForm, StepQuickEditForm
from ..models import AISettings, Ingredient, Recipe, Step
```

(adds the two form imports and `Ingredient`/`Step` to the models import).

Then add this function. Place it directly after the `RecipeDeleteView` class (i.e. right before
the `# Import/Export` section that starts with `def export_recipe`):

```python
def ingredient_quick_edit(request: HttpRequest, recipe_pk: int, pk: int) -> HttpResponse:
    """Quick-edit a single ingredient's amount/unit/name/note from the recipe detail page."""
    ingredient = get_object_or_404(Ingredient, pk=pk, recipe_id=recipe_pk)

    if request.method == "POST":
        form = IngredientQuickEditForm(request.POST, instance=ingredient)
        if form.is_valid():
            form.save()
            logger.info(f"Ingredient quick-edited: '{ingredient.name}' (ID: {ingredient.pk}, Recipe ID: {recipe_pk})")
        else:
            logger.warning(f"Ingredient quick-edit failed (ID: {ingredient.pk}): {form.errors.as_text()}")
            messages.error(
                request,
                _("Couldn't save ingredient: %(errors)s") % {"errors": form.errors.as_text()},
            )

    return redirect(f"{reverse('recipe_detail', args=[recipe_pk])}#ingredient-{pk}")
```

In `src/plated/recipes/urls.py`, add this URL pattern directly after the `recipe_delete` pattern
(i.e. right before the `# Import/Export` comment):

```python
    path(
        "recipe/<int:recipe_pk>/ingredient/<int:pk>/quick-edit/",
        views.recipes.ingredient_quick_edit,
        name="ingredient_quick_edit",
    ),
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python src/plated/manage.py test recipes.tests.test_views_recipes.IngredientQuickEditViewTest -v 2`
Expected: `OK` (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/plated/recipes/views/recipes.py src/plated/recipes/urls.py src/plated/recipes/tests/test_views_recipes.py
git commit -m "feat(recipes): add ingredient_quick_edit view"
```

---

### Task 4: `step_quick_edit` view + URL

**Files:**
- Modify: `src/plated/recipes/views/recipes.py`
- Modify: `src/plated/recipes/urls.py`
- Test: `src/plated/recipes/tests/test_views_recipes.py`

- [ ] **Step 1: Write the failing tests**

Append to `src/plated/recipes/tests/test_views_recipes.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python src/plated/manage.py test recipes.tests.test_views_recipes.StepQuickEditViewTest -v 2`
Expected: FAIL — `NoReverseMatch: Reverse for 'step_quick_edit' not found`

- [ ] **Step 3: Implement the view**

Add this function in `src/plated/recipes/views/recipes.py` directly after `ingredient_quick_edit`:

```python
def step_quick_edit(request: HttpRequest, recipe_pk: int, pk: int) -> HttpResponse:
    """Quick-edit a single step's content/timer from the recipe detail page."""
    step = get_object_or_404(Step, pk=pk, recipe_id=recipe_pk)

    if request.method == "POST":
        form = StepQuickEditForm(request.POST, instance=step)
        if form.is_valid():
            form.save()
            logger.info(f"Step quick-edited: ID {step.pk} (Recipe ID: {recipe_pk})")
        else:
            logger.warning(f"Step quick-edit failed (ID: {step.pk}): {form.errors.as_text()}")
            messages.error(
                request,
                _("Couldn't save step: %(errors)s") % {"errors": form.errors.as_text()},
            )

    return redirect(f"{reverse('recipe_detail', args=[recipe_pk])}#step-{pk}")
```

In `src/plated/recipes/urls.py`, add this URL pattern directly after `ingredient_quick_edit`'s:

```python
    path(
        "recipe/<int:recipe_pk>/step/<int:pk>/quick-edit/",
        views.recipes.step_quick_edit,
        name="step_quick_edit",
    ),
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python src/plated/manage.py test recipes.tests.test_views_recipes.StepQuickEditViewTest -v 2`
Expected: `OK` (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/plated/recipes/views/recipes.py src/plated/recipes/urls.py src/plated/recipes/tests/test_views_recipes.py
git commit -m "feat(recipes): add step_quick_edit view"
```

---

### Task 5: Attach quick-edit forms to `RecipeDetailView`

**Files:**
- Modify: `src/plated/recipes/views/recipes.py`
- Test: `src/plated/recipes/tests/test_views_recipes.py`

**Why this task exists separately:** the template partials in Tasks 6-7 need
`ingredient.quick_edit_form` / `step.quick_edit_form` to already exist on each object. Rather than
look them up by id in the template (which would need a custom template filter), each `Ingredient`/
`Step` instance gets its form attached as a plain attribute in the view — a standard Django
pattern for per-object template-only data. This requires `RecipeDetailView` to prefetch
`ingredients`/`steps` (it doesn't currently) so that the *same* Python objects are reused when the
template calls `recipe.ingredients.all()`/`recipe.steps.all()` more than once (once for the
existing `{% if %}` check, once for the edit-button loop, once for the modal-include loop) —
without prefetching, each `.all()` call would hit the DB again and return fresh objects without the
attached form.

- [ ] **Step 1: Write the failing test**

Append to `src/plated/recipes/tests/test_views_recipes.py`, inside the existing
`RecipeDetailViewTest` class (after its last test method):

```python
    def test_detail_view_has_quick_edit_forms_prefilled(self) -> None:
        """Ingredients and steps carry a pre-filled quick-edit form for the template to render."""
        Step.objects.create(recipe=self.recipe, content="Mix everything", order=0)
        response = self.client.get(reverse("recipe_detail", args=[self.recipe.pk]))
        self.assertEqual(response.status_code, 200)
        ingredient = response.context["recipe"].ingredients.all()[0]
        step = response.context["recipe"].steps.all()[0]
        self.assertEqual(ingredient.quick_edit_form.initial["name"], ingredient.name)
        self.assertEqual(step.quick_edit_form.initial["content"], step.content)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run python src/plated/manage.py test recipes.tests.test_views_recipes.RecipeDetailViewTest.test_detail_view_has_quick_edit_forms_prefilled -v 2`
Expected: FAIL — `AttributeError: 'Ingredient' object has no attribute 'quick_edit_form'`

- [ ] **Step 3: Implement**

Replace the `RecipeDetailView` class in `src/plated/recipes/views/recipes.py` with:

```python
class RecipeDetailView(DetailView):
    """Display a single recipe with all its details."""

    model = Recipe
    template_name = "recipes/recipe_detail.html"
    context_object_name = "recipe"

    def get_queryset(self):
        """Prefetch ingredients and steps so quick-edit forms stay attached across template lookups."""
        return Recipe.objects.prefetch_related("ingredients", "steps")

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add all collections, recipe's current collections, and per-item quick-edit forms."""
        context = super().get_context_data(**kwargs)
        from ..models import RecipeCollection

        recipe = self.get_object()
        all_collections = RecipeCollection.objects.all()
        recipe_collection_ids = set(recipe.collections.values_list("id", flat=True))

        for ingredient in recipe.ingredients.all():
            ingredient.quick_edit_form = IngredientQuickEditForm(instance=ingredient)
        for step in recipe.steps.all():
            step.quick_edit_form = StepQuickEditForm(instance=step)

        context["all_collections"] = all_collections
        context["recipe_collection_ids"] = recipe_collection_ids
        return context
```

(Only the `get_queryset` method and the two `for` loops in `get_context_data` are new; the rest is
unchanged from the current implementation.)

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run python src/plated/manage.py test recipes.tests.test_views_recipes.RecipeDetailViewTest.test_detail_view_has_quick_edit_forms_prefilled -v 2`
Expected: `OK` (1 test)

- [ ] **Step 5: Run the full recipes test suite to check for regressions**

Run: `uv run python src/plated/manage.py test recipes -v 1`
Expected: `OK`, same or higher test count than before this task

- [ ] **Step 6: Commit**

```bash
git add src/plated/recipes/views/recipes.py src/plated/recipes/tests/test_views_recipes.py
git commit -m "feat(recipes): attach quick-edit forms to detail view ingredients/steps"
```

---

### Task 6: Ingredient quick-edit modal partial + template wiring

**Files:**
- Create: `src/plated/templates/recipes/_ingredient_quick_edit_modal.html`
- Modify: `src/plated/templates/recipes/recipe_detail.html`
- Test: `src/plated/recipes/tests/test_views_recipes.py`

- [ ] **Step 1: Write the failing test**

Append to `RecipeDetailViewTest` in `src/plated/recipes/tests/test_views_recipes.py`:

```python
    def test_detail_view_renders_ingredient_quick_edit_modal(self) -> None:
        """Each ingredient gets an edit button and a modal with its current values."""
        response = self.client.get(reverse("recipe_detail", args=[self.recipe.pk]))
        ingredient = self.recipe.ingredients.first()
        self.assertContains(response, f'data-bs-target="#edit-ingredient-{ingredient.pk}"')
        self.assertContains(response, f'id="edit-ingredient-{ingredient.pk}"')
        self.assertContains(response, f'value="{ingredient.name}"')
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run python src/plated/manage.py test recipes.tests.test_views_recipes.RecipeDetailViewTest.test_detail_view_renders_ingredient_quick_edit_modal -v 2`
Expected: FAIL — assertion error, the markup doesn't exist yet

- [ ] **Step 3: Create the modal partial**

Create `src/plated/templates/recipes/_ingredient_quick_edit_modal.html`:

```django
{% load i18n %}
<div class="modal fade"
     id="edit-ingredient-{{ ingredient.id }}"
     tabindex="-1"
     aria-labelledby="edit-ingredient-{{ ingredient.id }}-label"
     aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content">
            <form method="post"
                  action="{% url 'ingredient_quick_edit' recipe.pk ingredient.pk %}">
                {% csrf_token %}
                <div class="modal-header">
                    <h5 class="modal-title" id="edit-ingredient-{{ ingredient.id }}-label">
                        <i class="bi bi-pencil"></i> {% trans "Edit Ingredient" %}
                    </h5>
                    <button type="button"
                            class="btn-close"
                            data-bs-dismiss="modal"
                            aria-label='{% trans "Close" %}'></button>
                </div>
                <div class="modal-body">
                    <div class="row g-2">
                        <div class="col-4 mb-2">
                            <label for="{{ ingredient.quick_edit_form.amount.id_for_label }}"
                                   class="form-label">{% trans "Amount" %}</label>
                            {{ ingredient.quick_edit_form.amount }}
                        </div>
                        <div class="col-8 mb-2">
                            <label for="{{ ingredient.quick_edit_form.unit.id_for_label }}"
                                   class="form-label">{% trans "Unit" %}</label>
                            {{ ingredient.quick_edit_form.unit }}
                        </div>
                    </div>
                    <div class="mb-2">
                        <label for="{{ ingredient.quick_edit_form.name.id_for_label }}"
                               class="form-label">{% trans "Name" %}</label>
                        {{ ingredient.quick_edit_form.name }}
                    </div>
                    <div class="mb-2">
                        <label for="{{ ingredient.quick_edit_form.note.id_for_label }}"
                               class="form-label">{% trans "Note" %}</label>
                        {{ ingredient.quick_edit_form.note }}
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">{% trans "Cancel" %}</button>
                    <button type="submit" class="btn btn-primary">{% trans "Save" %}</button>
                </div>
            </form>
        </div>
    </div>
</div>
```

- [ ] **Step 4: Wire it into `recipe_detail.html`**

In `src/plated/templates/recipes/recipe_detail.html`, replace the ingredient `<li>` block (the
one starting `<li class="ingredient-item"` inside the `ingredient-list` `<ul>`) with:

```django
                                <li class="ingredient-item"
                                    id="ingredient-{{ ingredient.id }}"
                                    data-amount="{{ ingredient.amount }}"
                                    data-unit="{{ ingredient.unit }}"
                                    data-name="{{ ingredient.name }}">
                                    <span class="ingredient-amount">
                                        {% if ingredient.amount %}{{ ingredient.amount|format_amount }}{% endif %}
                                        {% if ingredient.unit %} {{ ingredient.unit }}{% endif %}
                                    </span>
                                    <div class="ingredient-content">
                                        <span class="ingredient-name">{{ ingredient.name }}</span>
                                        {% if ingredient.note %}<span class="ingredient-note">{{ ingredient.note }}</span>{% endif %}
                                    </div>
                                    <button type="button"
                                            class="btn btn-sm btn-link quick-edit-btn"
                                            data-bs-toggle="modal"
                                            data-bs-target="#edit-ingredient-{{ ingredient.id }}"
                                            aria-label='{% trans "Edit ingredient" %}'>
                                        <i class="bi bi-pencil"></i>
                                    </button>
                                </li>
```

Then, directly after the closing `</ul>` of the ingredient list (and still inside the
`{% if recipe.ingredients.all %} ... {% else %} ... {% endif %}` block's `if` branch, right after
`</ul>` and before the matching `{% else %}`), add:

```django
                        {% for ingredient in recipe.ingredients.all %}
                            {% include "recipes/_ingredient_quick_edit_modal.html" with ingredient=ingredient recipe=recipe %}
                        {% endfor %}
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `uv run python src/plated/manage.py test recipes.tests.test_views_recipes.RecipeDetailViewTest.test_detail_view_renders_ingredient_quick_edit_modal -v 2`
Expected: `OK` (1 test)

- [ ] **Step 6: Commit**

```bash
git add src/plated/templates/recipes/_ingredient_quick_edit_modal.html src/plated/templates/recipes/recipe_detail.html src/plated/recipes/tests/test_views_recipes.py
git commit -m "feat(recipes): add ingredient quick-edit button and modal"
```

---

### Task 7: Step quick-edit modal partial + template wiring

**Files:**
- Create: `src/plated/templates/recipes/_step_quick_edit_modal.html`
- Modify: `src/plated/templates/recipes/recipe_detail.html`
- Test: `src/plated/recipes/tests/test_views_recipes.py`

- [ ] **Step 1: Write the failing test**

Append to `RecipeDetailViewTest` in `src/plated/recipes/tests/test_views_recipes.py`:

```python
    def test_detail_view_renders_step_quick_edit_modal(self) -> None:
        """Each step gets an edit button and a modal with its current content."""
        step = Step.objects.create(recipe=self.recipe, content="Mix everything", order=0)
        response = self.client.get(reverse("recipe_detail", args=[self.recipe.pk]))
        self.assertContains(response, f'data-bs-target="#edit-step-{step.pk}"')
        self.assertContains(response, f'id="edit-step-{step.pk}"')
        self.assertContains(response, "Mix everything")
```

Note: `Step` must already be imported at the top of this test file — check the existing
`from ..models import Ingredient, Recipe, Step` line; it already covers this.

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run python src/plated/manage.py test recipes.tests.test_views_recipes.RecipeDetailViewTest.test_detail_view_renders_step_quick_edit_modal -v 2`
Expected: FAIL — assertion error, the markup doesn't exist yet

- [ ] **Step 3: Create the modal partial**

Create `src/plated/templates/recipes/_step_quick_edit_modal.html`:

```django
{% load i18n %}
<div class="modal fade"
     id="edit-step-{{ step.id }}"
     tabindex="-1"
     aria-labelledby="edit-step-{{ step.id }}-label"
     aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content">
            <form method="post"
                  action="{% url 'step_quick_edit' recipe.pk step.pk %}">
                {% csrf_token %}
                <div class="modal-header">
                    <h5 class="modal-title" id="edit-step-{{ step.id }}-label">
                        <i class="bi bi-pencil"></i> {% trans "Edit Step" %}
                    </h5>
                    <button type="button"
                            class="btn-close"
                            data-bs-dismiss="modal"
                            aria-label='{% trans "Close" %}'></button>
                </div>
                <div class="modal-body">
                    <div class="mb-2">
                        <label for="{{ step.quick_edit_form.content.id_for_label }}"
                               class="form-label">{% trans "Instructions" %}</label>
                        {{ step.quick_edit_form.content }}
                    </div>
                    <div class="mb-2">
                        <label for="{{ step.quick_edit_form.timer.id_for_label }}"
                               class="form-label">{% trans "Timer (minutes)" %}</label>
                        {{ step.quick_edit_form.timer }}
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">{% trans "Cancel" %}</button>
                    <button type="submit" class="btn btn-primary">{% trans "Save" %}</button>
                </div>
            </form>
        </div>
    </div>
</div>
```

- [ ] **Step 4: Wire it into `recipe_detail.html`**

In `src/plated/templates/recipes/recipe_detail.html`, replace the step rendering line:

```django
                                {% for step in recipe.steps.all %}<li class="instruction-item">{{ step.content|linebreaks }}</li>{% endfor %}
```

with:

```django
                                {% for step in recipe.steps.all %}
                                    <li class="instruction-item" id="step-{{ step.id }}">
                                        <div class="instruction-content">{{ step.content|linebreaks }}</div>
                                        <button type="button"
                                                class="btn btn-sm btn-link quick-edit-btn"
                                                data-bs-toggle="modal"
                                                data-bs-target="#edit-step-{{ step.id }}"
                                                aria-label='{% trans "Edit step" %}'>
                                            <i class="bi bi-pencil"></i>
                                        </button>
                                    </li>
                                {% endfor %}
```

Then, directly after the closing `</ol>` of the instruction list (still inside the `if` branch,
before the matching `{% else %}`), add:

```django
                        {% for step in recipe.steps.all %}
                            {% include "recipes/_step_quick_edit_modal.html" with step=step recipe=recipe %}
                        {% endfor %}
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `uv run python src/plated/manage.py test recipes.tests.test_views_recipes.RecipeDetailViewTest.test_detail_view_renders_step_quick_edit_modal -v 2`
Expected: `OK` (1 test)

- [ ] **Step 6: Commit**

```bash
git add src/plated/templates/recipes/_step_quick_edit_modal.html src/plated/templates/recipes/recipe_detail.html src/plated/recipes/tests/test_views_recipes.py
git commit -m "feat(recipes): add step quick-edit button and modal"
```

---

### Task 8: Layout CSS for the edit button

**Files:**
- Modify: `src/plated/static/styles.css`

The ingredient row (`.ingredient-item`) is already `display: flex` with its middle child
(`.ingredient-content`) set to `flex: 1`, so the new button naturally lands flush right after it —
no new ingredient-specific CSS is needed. The instruction row (`.instruction-item`) is also
`display: flex`, but its text was previously a single un-wrapped child; Task 7 wrapped it in
`.instruction-content`, which needs `flex: 1` so it fills the available space and pushes the
button to the right edge, matching the ingredient row's layout.

- [ ] **Step 1: Add the CSS rules**

In `src/plated/static/styles.css`, find the `.instruction-item` rule block (search for
`.instruction-item {`) and add a new rule directly after its closing `}` (and after the adjacent
`.instruction-item:last-child` and `.instruction-item::before` rules, before the
`.instruction-list-wrapper` rule):

```css
.instruction-content {
    flex: 1;
}

.quick-edit-btn {
    flex-shrink: 0;
    align-self: flex-start;
    color: var(--text-tertiary);
}

.quick-edit-btn:hover,
.quick-edit-btn:focus {
    color: var(--primary);
}
```

- [ ] **Step 2: Reformat with the project's CSS formatter**

Run: `uv run deno fmt src/plated/static/styles.css`
Expected: reformats the file to the project's existing deno-fmt style (indentation/quoting), no
content change beyond that.

- [ ] **Step 3: Visually verify**

Run the dev server (`uv run python src/plated/manage.py runserver`) and open a recipe detail page
in a browser at a mobile width (~375px). Confirm:
- Each ingredient row shows a pencil icon aligned to the right, vertically aligned with the
  ingredient's first line.
- Each step row shows the same, aligned with the first line of that step's text.
- Tapping a pencil icon opens the correct modal pre-filled with that item's current values.
- Saving a change updates the value shown on the page and scrolls back to that row.
- Submitting a blank ingredient name shows an error message and leaves the value unchanged.

- [ ] **Step 4: Commit**

```bash
git add src/plated/static/styles.css
git commit -m "style(recipes): align quick-edit button in ingredient/step rows"
```

---

### Task 9: Document the feature

**Files:**
- Modify: `docs/features.md`

- [ ] **Step 1: Add the documentation section**

In `docs/features.md`, directly after the existing `### Editing Recipes` section (which reads
`Click the **Edit** button on any recipe card or detail page.`), add:

```markdown
### Quick-Editing Ingredients and Steps

For small fixes — a typo, a wrong amount, a quick note — tap the pencil icon next to any
ingredient or step on the recipe detail page. This opens a small form for just that item, without
leaving the page or opening the full edit form. Use the full **Edit** button instead when you
need to add, delete, or reorder ingredients/steps, or make larger changes; quick-edit only
changes the values of items that already exist.
```

- [ ] **Step 2: Commit**

```bash
git add docs/features.md
git commit -m "docs: document ingredient/step quick-edit"
```

---

### Task 10: Full verification pass

**Files:** none (verification only)

- [ ] **Step 1: Run the full recipes test suite**

Run: `uv run python src/plated/manage.py test recipes`
Expected: `OK`, test count higher than the pre-feature baseline (145 + the ~17 tests added across
Tasks 1-7)

- [ ] **Step 2: Run the project's full check**

Run: `just check`
Expected: ruff check/format, deno lint/fmt, and mypy all pass with no errors

- [ ] **Step 3: Run the full CI pipeline**

Run: `just ci`
Expected: `OK` — this also runs `docs-build` and `build`, confirming the new `docs/features.md`
section doesn't break the mkdocs build

If any step fails, fix the issue and re-run from Step 1 before considering the feature done. No
new commit is needed for this task unless a fix was required, in which case commit that fix with
a message describing what was wrong.
