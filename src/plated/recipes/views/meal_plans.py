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
from django.utils.translation import gettext as _
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from ..models import MealPlan, MealPlanEntry, Recipe
from ..services import typst_service

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
            _("Meal plan '%(name)s' created successfully!") % {"name": form.instance.name},
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
            _("Meal plan '%(name)s' updated successfully!") % {"name": form.instance.name},
        )
        return result


class MealPlanDeleteView(DeleteView):
    """Delete a meal plan after confirmation."""

    model = MealPlan
    template_name = "recipes/meal_plan_confirm_delete.html"
    success_url = reverse_lazy("meal_plan_list")

    def get_success_url(self) -> str:
        """Redirect to meal plan list page after deletion."""
        return str(reverse_lazy("meal_plan_list"))

    def delete(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Delete the meal plan and show a success message."""
        meal_plan = self.get_object()
        meal_plan_name = meal_plan.name
        meal_plan_id = meal_plan.pk
        logger.info(f"Meal plan deleted: '{meal_plan_name}' (ID: {meal_plan_id})")
        messages.success(request, _("Meal plan '%(name)s' deleted successfully!") % {"name": meal_plan_name})
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
            messages.success(
                request,
                _("Added %(recipe)s to %(meal_type)s on %(date)s")
                % {"recipe": recipe.title, "meal_type": meal_type, "date": date},
            )
        else:
            messages.error(request, _("Missing required fields"))

    return redirect("meal_plan_detail", pk=pk)


def remove_meal_entry(request: HttpRequest, pk: int, entry_id: int) -> HttpResponse:
    """Remove a recipe from a meal plan."""
    meal_plan = get_object_or_404(MealPlan, pk=pk)
    entry = get_object_or_404(MealPlanEntry, pk=entry_id, meal_plan=meal_plan)

    entry_info = f"{entry.recipe.title} from {entry.get_meal_type_display()} on {entry.date}"
    entry.delete()
    logger.info(f"Removed {entry_info} from meal plan '{meal_plan.name}'")
    messages.success(request, _("Removed %(entry)s") % {"entry": entry_info})

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

    # Aggregate ingredients by name and unit
    from fractions import Fraction

    ingredients_dict: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    ingredients_non_numeric: dict[str, list[str]] = defaultdict(list)

    for entry in meal_plan.entries.all():
        recipe = entry.recipe
        servings_multiplier = entry.servings / recipe.servings if recipe.servings > 0 else 1

        for ingredient in recipe.ingredients.all():
            key = ingredient.name.lower()
            unit = ingredient.unit.strip() if ingredient.unit else ""

            # Try to parse and aggregate amounts
            if ingredient.amount:
                amount_str = ingredient.amount.strip()
                try:
                    # Try to parse as fraction or decimal
                    amount_value = float(Fraction(amount_str)) * servings_multiplier
                    ingredients_dict[key][unit] += amount_value
                except (ValueError, ZeroDivisionError):
                    # If can't parse, store as non-numeric
                    display = f"{amount_str} {unit}" if unit else amount_str
                    if display not in ingredients_non_numeric[key]:
                        ingredients_non_numeric[key].append(display)
            else:
                # No amount specified
                if unit:
                    display = unit
                    if display not in ingredients_non_numeric[key]:
                        ingredients_non_numeric[key].append(display)

    # Build formatted ingredient list
    ingredients_list: list[tuple[str, str]] = []
    for name in sorted(set(ingredients_dict.keys()) | set(ingredients_non_numeric.keys())):
        parts = []

        # Add numeric amounts grouped by unit
        if name in ingredients_dict:
            for unit in sorted(ingredients_dict[name].keys()):
                total = ingredients_dict[name][unit]
                # Format number nicely
                if total == int(total):
                    amount_str = str(int(total))
                else:
                    # Show up to 2 decimal places, remove trailing zeros
                    amount_str = f"{total:.2f}".rstrip("0").rstrip(".")

                if unit:
                    parts.append(f"{amount_str} {unit}")
                else:
                    parts.append(amount_str)

        # Add non-numeric amounts
        if name in ingredients_non_numeric:
            parts.extend(ingredients_non_numeric[name])

        display_value = ", ".join(parts) if parts else ""
        ingredients_list.append((name, display_value))

    context = {
        "meal_plan": meal_plan,
        "ingredients": ingredients_list,
    }

    return render(request, "recipes/shopping_list.html", context)


def download_meal_plan_pdf(request: HttpRequest, pk: int) -> HttpResponse:
    """Generate and download a meal plan as a PDF using Typst."""
    meal_plan = get_object_or_404(
        MealPlan.objects.prefetch_related(
            Prefetch(
                "entries",
                queryset=MealPlanEntry.objects.select_related("recipe").prefetch_related(
                    "recipe__ingredients", "recipe__steps"
                ),
            )
        ),
        pk=pk,
    )

    try:
        # Serialize meal plan data
        entries_data = []
        for entry in meal_plan.entries.all():
            prep_time_mins = int(entry.recipe.prep_time.total_seconds() / 60) if entry.recipe.prep_time else 0
            wait_time_mins = int(entry.recipe.wait_time.total_seconds() / 60) if entry.recipe.wait_time else 0

            entries_data.append(
                {
                    "date": str(entry.date),
                    "meal_type": entry.meal_type,
                    "recipe_title": entry.recipe.title,
                    "servings": entry.servings,
                    "notes": entry.notes,
                    "prep_time_minutes": prep_time_mins,
                    "wait_time_minutes": wait_time_mins,
                }
            )

        meal_plan_data = {
            "name": meal_plan.name,
            "description": meal_plan.description,
            "start_date": str(meal_plan.start_date),
            "end_date": str(meal_plan.end_date),
            "entries": entries_data,
        }

        # Generate PDF using the Typst service
        pdf_content = typst_service.generate_typst_pdf(
            template_name="meal_plan.typ",
            data=meal_plan_data,
            context_name="meal_plan",
            entity_name="meal plan",
            entity_id=pk,
        )

        # Create response with PDF
        response = HttpResponse(pdf_content, content_type="application/pdf")

        # Sanitize filename
        safe_name = typst_service.sanitize_filename(meal_plan.name)
        response["Content-Disposition"] = f'attachment; filename="{safe_name}.pdf"'

        return response

    except typst_service.TypstTemplateNotFoundError:
        messages.error(request, _("Typst template file not found."))
        return redirect("meal_plan_detail", pk=pk)
    except typst_service.TypstExecutableNotFoundError:
        messages.error(request, _("Typst is not installed. Please install Typst to generate PDFs."))
        return redirect("meal_plan_detail", pk=pk)
    except typst_service.TypstTimeoutError:
        messages.error(request, _("PDF generation timed out."))
        return redirect("meal_plan_detail", pk=pk)
    except typst_service.TypstCompilationError as e:
        messages.error(request, _("Error generating PDF: %(error)s") % {"error": str(e)})
        return redirect("meal_plan_detail", pk=pk)
    except typst_service.TypstError as e:
        messages.error(request, _("Error generating PDF: %(error)s") % {"error": str(e)})
        return redirect("meal_plan_detail", pk=pk)


def download_shopping_list_pdf(request: HttpRequest, pk: int) -> HttpResponse:
    """Generate and download a shopping list as a PDF using Typst."""
    meal_plan = get_object_or_404(
        MealPlan.objects.prefetch_related(
            Prefetch(
                "entries",
                queryset=MealPlanEntry.objects.select_related("recipe").prefetch_related("recipe__ingredients"),
            )
        ),
        pk=pk,
    )

    try:
        # Aggregate ingredients by name
        ingredients_dict: dict[str, dict[str, Any]] = defaultdict(lambda: {"items": [], "total_amount": ""})

        for entry in meal_plan.entries.all():
            recipe = entry.recipe

            for ingredient in recipe.ingredients.all():
                key = ingredient.name.lower()
                ingredients_dict[key]["items"].append(
                    {
                        "amount": ingredient.amount,
                        "unit": ingredient.unit,
                        "recipe": recipe.title,
                    }
                )

        # Sort ingredients alphabetically
        sorted_ingredients = []
        for name, data in sorted(ingredients_dict.items()):
            sorted_ingredients.append(
                {
                    "name": name.title(),
                    "items": data["items"],
                    "total_amount": data.get("total_amount", ""),
                }
            )

        # Count unique recipes
        recipe_ids = set(entry.recipe_id for entry in meal_plan.entries.all())

        shopping_list_data = {
            "meal_plan_name": meal_plan.name,
            "start_date": str(meal_plan.start_date),
            "end_date": str(meal_plan.end_date),
            "ingredients": sorted_ingredients,
            "recipe_count": len(recipe_ids),
        }

        # Generate PDF using the Typst service
        pdf_content = typst_service.generate_typst_pdf(
            template_name="shopping_list.typ",
            data=shopping_list_data,
            context_name="shopping_list",
            entity_name="shopping list",
            entity_id=pk,
        )

        # Create response with PDF
        response = HttpResponse(pdf_content, content_type="application/pdf")

        # Sanitize filename
        safe_name = typst_service.sanitize_filename(meal_plan.name)
        response["Content-Disposition"] = f'attachment; filename="{safe_name}_shopping_list.pdf"'

        return response

    except typst_service.TypstTemplateNotFoundError:
        messages.error(request, _("Typst template file not found."))
        return redirect("shopping_list", pk=pk)
    except typst_service.TypstExecutableNotFoundError:
        messages.error(request, _("Typst is not installed. Please install Typst to generate PDFs."))
        return redirect("shopping_list", pk=pk)
    except typst_service.TypstTimeoutError:
        messages.error(request, _("PDF generation timed out."))
        return redirect("shopping_list", pk=pk)
    except typst_service.TypstCompilationError as e:
        messages.error(request, _("Error generating PDF: %(error)s") % {"error": str(e)})
        return redirect("shopping_list", pk=pk)
    except typst_service.TypstError as e:
        messages.error(request, _("Error generating PDF: %(error)s") % {"error": str(e)})
        return redirect("shopping_list", pk=pk)
