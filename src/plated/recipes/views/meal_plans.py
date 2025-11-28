from __future__ import annotations

import json
import logging
import shutil
import subprocess
import tempfile
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
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
    logger.info(f"PDF generation initiated for meal plan: '{meal_plan.name}' (ID: {pk})")

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

        # Get the path to the Typst template
        base_dir = Path(__file__).resolve().parent.parent
        typst_template = base_dir / "typst" / "meal_plan.typ"

        if not typst_template.exists():
            logger.error(f"Typst template not found at {typst_template}")
            messages.error(request, _("Typst template file not found."))
            return redirect("meal_plan_detail", pk=pk)

        # Create temporary directory for intermediate files
        with tempfile.TemporaryDirectory(prefix="plated_typst_") as temp_dir:
            temp_path = Path(temp_dir)
            logger.debug(f"Using temporary directory: {temp_dir}")

            # Copy typst template to temp directory
            temp_typst = temp_path / "meal_plan.typ"
            shutil.copy(typst_template, temp_typst)

            # Write meal plan JSON to temp directory
            meal_plan_json_path = temp_path / "meal_plan.json"
            with open(meal_plan_json_path, "w", encoding="utf-8") as f:
                json.dump(meal_plan_data, f, indent=2, ensure_ascii=False)

            # Prepare output PDF path
            output_pdf = temp_path / "meal_plan.pdf"

            # Prepare Typst input data with relative paths
            typst_input_data = json.dumps({"meal_plan": "meal_plan.json"})

            # Call Typst to compile the PDF
            try:
                logger.debug(f"Running Typst compiler for meal plan '{meal_plan.name}'")
                subprocess.run(
                    [
                        "typst",
                        "compile",
                        str(temp_typst),
                        str(output_pdf),
                        "--input",
                        f"data={typst_input_data}",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    check=True,
                )
            except FileNotFoundError:
                logger.error("Typst executable not found on system")
                messages.error(
                    request,
                    _("Typst is not installed. Please install Typst to generate PDFs."),
                )
                return redirect("meal_plan_detail", pk=pk)
            except subprocess.TimeoutExpired:
                logger.error(f"Typst compilation timed out for meal plan '{meal_plan.name}' (ID: {pk})")
                messages.error(request, _("PDF generation timed out."))
                return redirect("meal_plan_detail", pk=pk)
            except subprocess.CalledProcessError as e:
                logger.error(
                    f"Typst compilation failed for meal plan '{meal_plan.name}' (ID: {pk}): {e.stderr}",
                    exc_info=True,
                )
                messages.error(
                    request,
                    _("Error generating PDF: %(error)s") % {"error": e.stderr if e.stderr else str(e)},
                )
                return redirect("meal_plan_detail", pk=pk)

            # Check if PDF was created
            if not output_pdf.exists():
                logger.error(f"PDF file not created for meal plan '{meal_plan.name}' (ID: {pk})")
                messages.error(request, _("PDF file was not generated."))
                return redirect("meal_plan_detail", pk=pk)

            # Read the PDF file
            with open(output_pdf, "rb") as pdf_file:
                pdf_content = pdf_file.read()

            # Create response with PDF
            response = HttpResponse(pdf_content, content_type="application/pdf")

            # Sanitize filename
            safe_name = "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in meal_plan.name)
            safe_name = safe_name.replace(" ", "_")
            response["Content-Disposition"] = f'attachment; filename="{safe_name}.pdf"'

            logger.info(f"PDF generated successfully for meal plan '{meal_plan.name}' (ID: {pk})")
            return response
    except Exception as e:
        logger.error(
            f"Unexpected error generating PDF for meal plan '{meal_plan.name}' (ID: {pk}): {e}",
            exc_info=True,
        )
        messages.error(request, _("Error generating PDF: %(error)s") % {"error": e})
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
    logger.info(f"PDF generation initiated for shopping list: '{meal_plan.name}' (ID: {pk})")

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

        # Get the path to the Typst template
        base_dir = Path(__file__).resolve().parent.parent
        typst_template = base_dir / "typst" / "shopping_list.typ"

        if not typst_template.exists():
            logger.error(f"Typst template not found at {typst_template}")
            messages.error(request, _("Typst template file not found."))
            return redirect("shopping_list", pk=pk)

        # Create temporary directory for intermediate files
        with tempfile.TemporaryDirectory(prefix="plated_typst_") as temp_dir:
            temp_path = Path(temp_dir)
            logger.debug(f"Using temporary directory: {temp_dir}")

            # Copy typst template to temp directory
            temp_typst = temp_path / "shopping_list.typ"
            shutil.copy(typst_template, temp_typst)

            # Write shopping list JSON to temp directory
            shopping_list_json_path = temp_path / "shopping_list.json"
            with open(shopping_list_json_path, "w", encoding="utf-8") as f:
                json.dump(shopping_list_data, f, indent=2, ensure_ascii=False)

            # Prepare output PDF path
            output_pdf = temp_path / "shopping_list.pdf"

            # Prepare Typst input data with relative paths
            typst_input_data = json.dumps({"shopping_list": "shopping_list.json"})

            # Call Typst to compile the PDF
            try:
                logger.debug(f"Running Typst compiler for shopping list '{meal_plan.name}'")
                subprocess.run(
                    [
                        "typst",
                        "compile",
                        str(temp_typst),
                        str(output_pdf),
                        "--input",
                        f"data={typst_input_data}",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    check=True,
                )
            except FileNotFoundError:
                logger.error("Typst executable not found on system")
                messages.error(
                    request,
                    _("Typst is not installed. Please install Typst to generate PDFs."),
                )
                return redirect("shopping_list", pk=pk)
            except subprocess.TimeoutExpired:
                logger.error(f"Typst compilation timed out for shopping list '{meal_plan.name}' (ID: {pk})")
                messages.error(request, _("PDF generation timed out."))
                return redirect("shopping_list", pk=pk)
            except subprocess.CalledProcessError as e:
                logger.error(
                    f"Typst compilation failed for shopping list '{meal_plan.name}' (ID: {pk}): {e.stderr}",
                    exc_info=True,
                )
                messages.error(
                    request,
                    _("Error generating PDF: %(error)s") % {"error": e.stderr if e.stderr else str(e)},
                )
                return redirect("shopping_list", pk=pk)

            # Check if PDF was created
            if not output_pdf.exists():
                logger.error(f"PDF file not created for shopping list '{meal_plan.name}' (ID: {pk})")
                messages.error(request, _("PDF file was not generated."))
                return redirect("shopping_list", pk=pk)

            # Read the PDF file
            with open(output_pdf, "rb") as pdf_file:
                pdf_content = pdf_file.read()

            # Create response with PDF
            response = HttpResponse(pdf_content, content_type="application/pdf")

            # Sanitize filename
            safe_name = "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in meal_plan.name)
            safe_name = safe_name.replace(" ", "_")
            response["Content-Disposition"] = f'attachment; filename="{safe_name}_shopping_list.pdf"'

            logger.info(f"PDF generated successfully for shopping list '{meal_plan.name}' (ID: {pk})")
            return response
    except Exception as e:
        logger.error(
            f"Unexpected error generating PDF for shopping list '{meal_plan.name}' (ID: {pk}): {e}",
            exc_info=True,
        )
        messages.error(request, _("Error generating PDF: %(error)s") % {"error": e})
        return redirect("shopping_list", pk=pk)
