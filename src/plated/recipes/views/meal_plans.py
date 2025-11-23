from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from django import forms
from django.contrib import messages
from django.db.models import Prefetch, QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from ..models import MealPlan, MealPlanEntry, Recipe

logger = logging.getLogger(__name__)


class MealPlanListView(ListView):
    """Display a list of all meal plans."""

    model = MealPlan
    template_name = "recipes/meal_plan_list.html"
    context_object_name = "meal_plans"
    paginate_by = 20


class MealPlanDetailView(DetailView):
    """Display a single meal plan with all its entries."""

    model = MealPlan
    template_name = "recipes/meal_plan_detail.html"
    context_object_name = "meal_plan"

    def get_queryset(self) -> QuerySet[MealPlan]:
        """Optimize query by prefetching related entries and recipes."""
        return MealPlan.objects.prefetch_related(
            Prefetch("entries", queryset=MealPlanEntry.objects.select_related("recipe"))
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add organized entries to context."""
        context = super().get_context_data(**kwargs)
        meal_plan = self.object

        # Organize entries by date and meal type
        entries_by_date: dict[str, dict[str, list[MealPlanEntry]]] = defaultdict(lambda: defaultdict(list))

        for entry in meal_plan.entries.all():
            date_str = entry.date.isoformat()
            entries_by_date[date_str][entry.meal_type].append(entry)

        # Generate list of dates in range
        current_date = meal_plan.start_date
        dates = []
        while current_date <= meal_plan.end_date:
            dates.append(current_date)
            current_date += timedelta(days=1)

        context["dates"] = dates
        context["entries_by_date"] = dict(entries_by_date)
        context["meal_types"] = ["breakfast", "lunch", "dinner", "snack"]

        return context


class MealPlanForm(forms.ModelForm):
    """Form for creating and editing meal plans."""

    class Meta:
        model = MealPlan
        fields = ["name", "description", "start_date", "end_date"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }


class MealPlanFormMixin:
    """Mixin for meal plan form customization."""

    def get_form(self, form_class: type[forms.ModelForm] | None = None) -> forms.ModelForm:  # type: ignore[override]
        """Customize the form to add Bootstrap classes."""
        form = super().get_form(form_class)  # type: ignore[misc]
        form.fields["name"].widget.attrs.update({"class": "form-control"})
        form.fields["description"].widget.attrs.update({"class": "form-control", "rows": 3})
        form.fields["start_date"].widget.attrs.update({"class": "form-control"})
        form.fields["end_date"].widget.attrs.update({"class": "form-control"})
        return form

    def get_success_url(self) -> str:
        """Redirect to meal plan detail page."""
        assert self.object is not None  # type: ignore[attr-defined]
        return str(reverse_lazy("meal_plan_detail", kwargs={"pk": self.object.pk}))  # type: ignore[attr-defined]


class MealPlanCreateView(MealPlanFormMixin, CreateView):  # type: ignore[misc]
    """Create a new meal plan."""

    model = MealPlan
    form_class = MealPlanForm
    template_name = "recipes/meal_plan_form.html"

    def form_valid(self, form: forms.ModelForm) -> HttpResponse:  # type: ignore[override]
        """Save the meal plan and show success message."""
        result = super().form_valid(form)
        logger.info(f"Meal plan created: '{form.instance.name}' (ID: {form.instance.pk})")
        messages.success(
            self.request,
            f"Meal plan '{form.instance.name}' created successfully!",
        )
        return result


class MealPlanUpdateView(MealPlanFormMixin, UpdateView):  # type: ignore[misc]
    """Update an existing meal plan."""

    model = MealPlan
    form_class = MealPlanForm
    template_name = "recipes/meal_plan_form.html"

    def form_valid(self, form: forms.ModelForm) -> HttpResponse:  # type: ignore[override]
        """Save the meal plan and show success message."""
        result = super().form_valid(form)
        logger.info(f"Meal plan updated: '{form.instance.name}' (ID: {form.instance.pk})")
        messages.success(
            self.request,
            f"Meal plan '{form.instance.name}' updated successfully!",
        )
        return result


class MealPlanDeleteView(DeleteView):
    """Delete a meal plan after confirmation."""

    model = MealPlan
    template_name = "recipes/meal_plan_confirm_delete.html"
    success_url = reverse_lazy("meal_plan_list")

    def delete(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Delete the meal plan and show a success message."""
        meal_plan = self.get_object()
        meal_plan_name = meal_plan.name
        meal_plan_id = meal_plan.pk
        logger.info(f"Meal plan deleted: '{meal_plan_name}' (ID: {meal_plan_id})")
        messages.success(request, f"Meal plan '{meal_plan_name}' deleted successfully!")
        return super().delete(request, *args, **kwargs)


def add_meal_entry(request: HttpRequest, pk: int) -> HttpResponse:
    """Add a recipe to a meal plan."""
    meal_plan = get_object_or_404(MealPlan, pk=pk)

    if request.method == "POST":
        recipe_id = request.POST.get("recipe_id")
        date_str = request.POST.get("date")
        meal_type = request.POST.get("meal_type")
        servings = request.POST.get("servings", "1")

        if recipe_id and date_str and meal_type:
            recipe = get_object_or_404(Recipe, pk=recipe_id)
            date = datetime.strptime(date_str, "%Y-%m-%d").date()

            MealPlanEntry.objects.create(
                meal_plan=meal_plan,
                recipe=recipe,
                date=date,
                meal_type=meal_type,
                servings=int(servings),
            )
            logger.info(f"Added {recipe.title} to meal plan '{meal_plan.name}' on {date} for {meal_type}")
            messages.success(request, f"Added {recipe.title} to {meal_type} on {date}")
        else:
            messages.error(request, "Missing required fields")

    return redirect("meal_plan_detail", pk=pk)


def remove_meal_entry(request: HttpRequest, pk: int, entry_id: int) -> HttpResponse:
    """Remove a recipe from a meal plan."""
    meal_plan = get_object_or_404(MealPlan, pk=pk)
    entry = get_object_or_404(MealPlanEntry, pk=entry_id, meal_plan=meal_plan)

    entry_info = f"{entry.recipe.title} from {entry.get_meal_type_display()} on {entry.date}"
    entry.delete()
    logger.info(f"Removed {entry_info} from meal plan '{meal_plan.name}'")
    messages.success(request, f"Removed {entry_info}")

    return redirect("meal_plan_detail", pk=pk)


def shopping_list(request: HttpRequest, pk: int) -> HttpResponse:
    """Generate a shopping list from a meal plan."""
    meal_plan = get_object_or_404(
        MealPlan.objects.prefetch_related(
            Prefetch(
                "entries",
                queryset=MealPlanEntry.objects.select_related("recipe").prefetch_related("recipe__ingredients"),
            )
        ),
        pk=pk,
    )

    # Aggregate ingredients by name
    ingredients_dict: dict[str, dict[str, Any]] = defaultdict(lambda: {"items": [], "total_amount": ""})

    for entry in meal_plan.entries.all():
        recipe = entry.recipe
        servings_multiplier = entry.servings / recipe.servings if recipe.servings > 0 else 1

        for ingredient in recipe.ingredients.all():
            key = ingredient.name.lower()
            ingredients_dict[key]["items"].append(
                {
                    "amount": ingredient.amount,
                    "unit": ingredient.unit,
                    "note": ingredient.note,
                    "recipe": recipe.title,
                    "date": entry.date,
                    "meal_type": entry.get_meal_type_display(),
                    "servings_multiplier": servings_multiplier,
                }
            )

    # Sort ingredients alphabetically
    sorted_ingredients = sorted(ingredients_dict.items())

    context = {
        "meal_plan": meal_plan,
        "ingredients": sorted_ingredients,
    }

    return render(request, "recipes/shopping_list.html", context)
