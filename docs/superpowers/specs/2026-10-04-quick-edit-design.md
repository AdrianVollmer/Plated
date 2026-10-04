# Quick-Edit Design

Date: 2026-10-04

## Overview

Add a lightweight way to fix a single ingredient or step from the recipe detail page without
opening the full recipe edit form. The full form (`recipe_update`) stays unchanged and is still
the only way to add, delete, or reorder ingredients/steps — quick-edit only changes the values
of items that already exist. This is aimed at the mobile case, where the full form's formsets are
long to scroll through for a one-field fix; on desktop the full "big" edit mode remains the
expected tool for larger changes.

## Trigger and UI

Each ingredient `<li class="ingredient-item">` and each step `<li class="instruction-item">` in
`recipe_detail.html` gets a small pencil-icon button (reusing the `bi-pencil` icon already used
for the main "Edit" action in the page header). The button is always visible — there is no
separate "enter edit mode" toggle — and opens a Bootstrap modal scoped to that one item, via
`data-bs-toggle="modal" data-bs-target="#edit-ingredient-{{ ingredient.id }}"` (and
`#edit-step-{{ step.id }}` for steps). This matches the existing `scaleRecipeModal` /
`addToCollectionModal` pattern already in the template.

One modal is rendered per ingredient/step, in the existing `{% for %}` loops, via two small
`{% include %}` partials (`recipes/_ingredient_quick_edit_modal.html`,
`recipes/_step_quick_edit_modal.html`) to keep the main loop body readable. Each modal's form
fields are pre-filled server-side from that item's current values — no JS is needed to populate
or sync a shared modal, since each item gets its own. This keeps the feature almost entirely
JS-free, in line with the project's minimal-JavaScript preference.

- Ingredient modal fields: `amount`, `unit`, `name`, `note`
- Step modal fields: `content`, `timer`

Each modal's `<form>` is a standard Django form with `{% csrf_token %}`, posting directly to the
quick-edit URL — no `fetch`/`XMLHttpRequest` involved.

Recipes in this app typically have well under 30 ingredients/steps combined, so the extra
server-rendered modal markup is cheap; no pagination or lazy-rendering is needed.

## Backend

Two new POST-only views in `recipes/views/recipes.py`, next to the existing
`RecipeDetailView`/`RecipeUpdateView`:

```python
class IngredientQuickEditView(UpdateView):
    model = Ingredient
    form_class = IngredientQuickEditForm  # fields: amount, unit, name, note
    http_method_names = ["post"]

    def get_queryset(self):
        return Ingredient.objects.filter(recipe_id=self.kwargs["recipe_pk"])

    def get_success_url(self) -> str:
        return f"{reverse('recipe_detail', args=[self.kwargs['recipe_pk']])}#ingredient-{self.object.pk}"

    def form_invalid(self, form: IngredientQuickEditForm) -> HttpResponse:
        messages.error(self.request, _("Couldn't save ingredient: %(errors)s") % {"errors": form.errors.as_text()})
        return redirect("recipe_detail", pk=self.kwargs["recipe_pk"])
```

`StepQuickEditView` mirrors this for `Step` with `form_class = StepQuickEditForm` (fields:
`content`, `timer`).

Both views filter their queryset by the `recipe_pk` from the URL (not just `pk` of the
ingredient/step), so a POST to `/recipe/<recipe_pk>/ingredient/<pk>/quick-edit/` for an ingredient
that doesn't belong to that recipe 404s via `get_object_or_404` semantics (standard
`SingleObjectMixin` behavior once the queryset is scoped).

Two new `ModelForm`s in `recipes/forms.py`:

```python
class IngredientQuickEditForm(forms.ModelForm):
    class Meta:
        model = Ingredient
        fields = ["amount", "unit", "name", "note"]


class StepQuickEditForm(forms.ModelForm):
    class Meta:
        model = Step
        fields = ["content", "timer"]
```

URLs (in `recipes/urls.py`):

```python
path("recipe/<int:recipe_pk>/ingredient/<int:pk>/quick-edit/", IngredientQuickEditView.as_view(), name="ingredient_quick_edit"),
path("recipe/<int:recipe_pk>/step/<int:pk>/quick-edit/", StepQuickEditView.as_view(), name="step_quick_edit"),
```

## Data Flow

Standard Django POST/redirect/GET, no AJAX/fetch/htmx:

1. User taps the pencil icon on an ingredient → Bootstrap modal opens (pure CSS/data-attribute
   toggle, no custom JS).
2. User edits a field and taps "Save" → browser POSTs the modal's form to the quick-edit URL.
3. On success: the view saves and redirects to `recipe_detail#ingredient-<id>`, so the page
   reloads scrolled back to the edited row. `recipe_detail.html`'s existing
   `<li class="ingredient-item" ...>` needs an `id="ingredient-{{ ingredient.id }}"` (and
   `id="step-{{ step.id }}"` for steps) added for the anchor to resolve.
4. On failure (e.g. a required field left blank): the view redirects back to `recipe_detail`
   with a Django message. No attempt is made to reopen the modal with inline field errors — this
   is a deliberately simple fallback since failures should be rare (the only required field is
   `Ingredient.name`; everything else is optional/free-text), and the user can just reopen the
   modal and retry. The existing base template's message/alert rendering (used elsewhere in the
   app) displays the error.

## Testing

New Django test cases in the `recipes` app test module, alongside existing `RecipeUpdateView`
tests:

- `IngredientQuickEditView`: valid POST updates the ingredient and redirects to the anchored
  detail URL; POST with blank `name` leaves the ingredient unchanged and redirects with an error
  message; POST targeting an ingredient belonging to a different recipe 404s; GET is not allowed
  (405).
- `StepQuickEditView`: same shape of tests for `content`/`timer`.

## Out of Scope

- Adding, deleting, or reordering ingredients/steps via quick-edit — stays in the full
  `recipe_update` form and its formset JS.
- Any change to the full edit form itself.
- Inline/autosave-on-blur editing, or making row text directly clickable/contenteditable.
- Reopening the modal with field-level errors on validation failure (see Data Flow, step 4).
