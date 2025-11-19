from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, cast

from django import forms
from django.contrib import messages
from django.core.files.uploadedfile import UploadedFile
from django.db import models as django_models
from django.db import transaction
from django.forms import inlineformset_factory
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from .forms import RecipeForm
from .models import Ingredient, Recipe, RecipeCollection, RecipeImage, Step
from .schema import deserialize_recipe, serialize_recipe, validate_recipe_data


def get_ingredient_formset(extra: int = 5):
    """Create an ingredient formset with Bootstrap styling."""
    return inlineformset_factory(
        Recipe,
        Ingredient,
        fields=("amount", "unit", "name", "note", "order"),
        extra=extra,
        can_delete=True,
        widgets={
            "amount": forms.TextInput(attrs={"class": "form-control form-control-sm"}),
            "unit": forms.TextInput(attrs={"class": "form-control form-control-sm"}),
            "name": forms.TextInput(attrs={"class": "form-control form-control-sm"}),
            "note": forms.TextInput(attrs={"class": "form-control form-control-sm"}),
            "order": forms.NumberInput(attrs={"class": "form-control form-control-sm"}),
        },
    )


def get_step_formset(extra: int = 3):
    """Create a step formset with Bootstrap styling."""
    return inlineformset_factory(
        Recipe,
        Step,
        fields=("content", "order"),
        extra=extra,
        can_delete=True,
        widgets={
            "content": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "order": forms.NumberInput(attrs={"class": "form-control form-control-sm"}),
        },
    )


def get_image_formset(extra: int = 2):
    """Create an image formset with Bootstrap styling."""
    return inlineformset_factory(
        Recipe,
        RecipeImage,
        fields=("image", "caption", "order"),
        extra=extra,
        can_delete=True,
        widgets={
            "caption": forms.TextInput(attrs={"class": "form-control form-control-sm"}),
            "order": forms.NumberInput(attrs={"class": "form-control form-control-sm"}),
        },
    )


class RecipeListView(ListView):
    """Display a list of all recipes."""

    model = Recipe
    template_name = "recipes/recipe_list.html"
    context_object_name = "recipes"
    paginate_by = 12

    def get_queryset(self):
        """Return recipes, optionally filtered by search query."""
        queryset = super().get_queryset()
        query = self.request.GET.get("q")
        if query:
            queryset = queryset.filter(title__icontains=query) | queryset.filter(
                keywords__icontains=query
            )
        return queryset


class RecipeDetailView(DetailView):
    """Display a single recipe with all its details."""

    model = Recipe
    template_name = "recipes/recipe_detail.html"
    context_object_name = "recipe"


class RecipeCreateView(CreateView):
    """Create a new recipe with ingredients, steps, and images."""

    model = Recipe
    form_class = RecipeForm
    template_name = "recipes/recipe_form.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add formsets to the context."""
        data = super().get_context_data(**kwargs)

        IngredientFormSet = get_ingredient_formset(extra=5)  # noqa: N806
        StepFormSet = get_step_formset(extra=3)  # noqa: N806
        ImageFormSet = get_image_formset(extra=2)  # noqa: N806

        if self.request.POST:
            data["ingredient_formset"] = IngredientFormSet(
                self.request.POST, prefix="ingredients"
            )
            data["step_formset"] = StepFormSet(self.request.POST, prefix="steps")
            data["image_formset"] = ImageFormSet(
                self.request.POST, self.request.FILES, prefix="images"
            )
        else:
            data["ingredient_formset"] = IngredientFormSet(prefix="ingredients")
            data["step_formset"] = StepFormSet(prefix="steps")
            data["image_formset"] = ImageFormSet(prefix="images")

        return data

    def form_valid(self, form: RecipeForm) -> HttpResponse:
        """Save the recipe and all related formsets."""
        context = self.get_context_data()
        ingredient_formset = context["ingredient_formset"]
        step_formset = context["step_formset"]
        image_formset = context["image_formset"]

        # Validate formsets
        if not ingredient_formset.is_valid():
            return self.form_invalid(form)

        if not step_formset.is_valid():
            return self.form_invalid(form)

        if not image_formset.is_valid():
            return self.form_invalid(form)

        # Check that at least one ingredient and one step are provided
        ingredient_count = sum(
            1
            for form_item in ingredient_formset
            if form_item.cleaned_data
            and not form_item.cleaned_data.get("DELETE", False)
            and form_item.cleaned_data.get("name")
        )
        step_count = sum(
            1
            for form_item in step_formset
            if form_item.cleaned_data
            and not form_item.cleaned_data.get("DELETE", False)
            and form_item.cleaned_data.get("content")
        )

        if ingredient_count == 0:
            messages.error(
                self.request, "Please add at least one ingredient to the recipe."
            )
            return self.form_invalid(form)

        if step_count == 0:
            messages.error(
                self.request, "Please add at least one instruction step to the recipe."
            )
            return self.form_invalid(form)

        with transaction.atomic():
            self.object = form.save()
            ingredient_formset.instance = self.object
            ingredient_formset.save()
            step_formset.instance = self.object
            step_formset.save()
            image_formset.instance = self.object
            image_formset.save()

        messages.success(
            self.request, f"Recipe '{self.object.title}' created successfully!"
        )
        return redirect("recipe_detail", pk=self.object.pk)


class RecipeUpdateView(UpdateView):
    """Update an existing recipe with ingredients, steps, and images."""

    model = Recipe
    form_class = RecipeForm
    template_name = "recipes/recipe_form.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add formsets to the context."""
        data = super().get_context_data(**kwargs)

        IngredientFormSet = get_ingredient_formset(extra=2)  # noqa: N806
        StepFormSet = get_step_formset(extra=1)  # noqa: N806
        ImageFormSet = get_image_formset(extra=1)  # noqa: N806

        if self.request.POST:
            data["ingredient_formset"] = IngredientFormSet(
                self.request.POST, instance=self.object, prefix="ingredients"
            )
            data["step_formset"] = StepFormSet(
                self.request.POST, instance=self.object, prefix="steps"
            )
            data["image_formset"] = ImageFormSet(
                self.request.POST,
                self.request.FILES,
                instance=self.object,
                prefix="images",
            )
        else:
            data["ingredient_formset"] = IngredientFormSet(
                instance=self.object, prefix="ingredients"
            )
            data["step_formset"] = StepFormSet(instance=self.object, prefix="steps")
            data["image_formset"] = ImageFormSet(instance=self.object, prefix="images")

        return data

    def form_valid(self, form: RecipeForm) -> HttpResponse:
        """Save the recipe and all related formsets."""
        context = self.get_context_data()
        ingredient_formset = context["ingredient_formset"]
        step_formset = context["step_formset"]
        image_formset = context["image_formset"]

        # Validate formsets
        if not ingredient_formset.is_valid():
            return self.form_invalid(form)

        if not step_formset.is_valid():
            return self.form_invalid(form)

        if not image_formset.is_valid():
            return self.form_invalid(form)

        # Check that at least one ingredient and one step are provided
        ingredient_count = sum(
            1
            for form_item in ingredient_formset
            if form_item.cleaned_data
            and not form_item.cleaned_data.get("DELETE", False)
            and form_item.cleaned_data.get("name")
        )
        step_count = sum(
            1
            for form_item in step_formset
            if form_item.cleaned_data
            and not form_item.cleaned_data.get("DELETE", False)
            and form_item.cleaned_data.get("content")
        )

        if ingredient_count == 0:
            messages.error(
                self.request, "Please add at least one ingredient to the recipe."
            )
            return self.form_invalid(form)

        if step_count == 0:
            messages.error(
                self.request, "Please add at least one instruction step to the recipe."
            )
            return self.form_invalid(form)

        with transaction.atomic():
            self.object = form.save()
            ingredient_formset.instance = self.object
            ingredient_formset.save()
            step_formset.instance = self.object
            step_formset.save()
            image_formset.instance = self.object
            image_formset.save()

        messages.success(
            self.request, f"Recipe '{self.object.title}' updated successfully!"
        )
        return redirect("recipe_detail", pk=self.object.pk)


class RecipeDeleteView(DeleteView):
    """Delete a recipe after confirmation."""

    model = Recipe
    template_name = "recipes/recipe_confirm_delete.html"
    success_url = reverse_lazy("recipe_list")

    def delete(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Delete the recipe and show a success message."""
        recipe = self.get_object()
        messages.success(request, f"Recipe '{recipe.title}' deleted successfully!")
        return super().delete(request, *args, **kwargs)


def get_ingredient_names(request: HttpRequest) -> JsonResponse:
    """API endpoint to get distinct ingredient names for autocomplete."""
    names = (
        Ingredient.objects.values_list("name", flat=True).distinct().order_by("name")
    )
    return JsonResponse({"names": list(names)})


def get_ingredient_units(request: HttpRequest) -> JsonResponse:
    """API endpoint to get distinct ingredient units for autocomplete."""
    units = (
        Ingredient.objects.exclude(unit="")
        .values_list("unit", flat=True)
        .distinct()
        .order_by("unit")
    )
    return JsonResponse({"units": list(units)})


def export_recipe(request: HttpRequest, pk: int) -> HttpResponse:
    """Export a recipe as a JSON file."""
    recipe = get_object_or_404(Recipe, pk=pk)
    recipe_data = serialize_recipe(recipe)

    # Create JSON response with proper filename
    response = HttpResponse(
        json.dumps(recipe_data, indent=2, ensure_ascii=False),
        content_type="application/json",
    )
    # Sanitize filename by replacing spaces and special chars
    safe_title = "".join(
        c if c.isalnum() or c in (" ", "-", "_") else "_" for c in recipe.title
    )
    safe_title = safe_title.replace(" ", "_")
    response["Content-Disposition"] = f'attachment; filename="{safe_title}.json"'

    return response


def import_recipe(request: HttpRequest) -> HttpResponse:
    """Import a recipe from a JSON file."""
    if request.method == "POST":
        if "json_file" not in request.FILES:
            messages.error(request, "No file was uploaded.")
            return redirect("recipe_import")

        json_file = cast(UploadedFile, request.FILES["json_file"])

        # Read and parse JSON
        try:
            content = json_file.read().decode("utf-8")
            data = json.loads(content)
        except json.JSONDecodeError as e:
            messages.error(request, f"Invalid JSON file: {e}")
            return redirect("recipe_import")
        except Exception as e:
            messages.error(request, f"Error reading file: {e}")
            return redirect("recipe_import")

        # Validate the data
        errors = validate_recipe_data(data)
        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect("recipe_import")

        # Deserialize and create recipe
        try:
            with transaction.atomic():
                deserialized = deserialize_recipe(data)

                # Create the recipe
                recipe = Recipe.objects.create(**deserialized["recipe_data"])

                # Create ingredients
                for ing_data in deserialized["ingredients_data"]:
                    Ingredient.objects.create(recipe=recipe, **ing_data)

                # Create steps
                for step_data in deserialized["steps_data"]:
                    Step.objects.create(recipe=recipe, **step_data)

                # Note: We don't import images since they're just metadata
                # Users would need to manually add images after import

            messages.success(
                request,
                f"Recipe '{recipe.title}' imported successfully! "
                "You can now add images if needed.",
            )
            return redirect("recipe_detail", pk=recipe.pk)

        except Exception as e:
            messages.error(request, f"Error creating recipe: {e}")
            return redirect("recipe_import")

    # GET request - show the upload form
    return render(request, "recipes/recipe_import.html")


def download_recipe_pdf(request: HttpRequest, pk: int) -> HttpResponse:
    """Generate and download a recipe as a PDF using Typst."""
    recipe = get_object_or_404(Recipe, pk=pk)
    recipe_data = serialize_recipe(recipe)

    # Get the path to the Typst template
    base_dir = Path(__file__).resolve().parent.parent
    typst_template = base_dir / "recipe.typ"

    if not typst_template.exists():
        messages.error(request, "Typst template file not found.")
        return redirect("recipe_detail", pk=pk)

    # Create temporary directory for intermediate files
    with tempfile.TemporaryDirectory(prefix="plated_typst_") as temp_dir:
        temp_path = Path(temp_dir)

        # Copy typst template to temp directory
        temp_typst = temp_path / "recipe.typ"
        shutil.copy(typst_template, temp_typst)

        # Write recipe JSON to temp directory (same location as typst file)
        recipe_json_path = temp_path / "recipe.json"
        with open(recipe_json_path, "w", encoding="utf-8") as f:
            json.dump(recipe_data, f, indent=2, ensure_ascii=False)

        # Prepare output PDF path
        output_pdf = temp_path / "recipe.pdf"

        # Prepare Typst input data with relative paths
        typst_input_data = json.dumps({"recipe": "recipe.json"})

        # Call Typst to compile the PDF
        try:
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
                timeout=30,
                check=True,
            )
        except FileNotFoundError:
            messages.error(
                request,
                "Typst is not installed. Please install Typst to generate PDFs.",
            )
            return redirect("recipe_detail", pk=pk)
        except subprocess.TimeoutExpired:
            messages.error(request, "PDF generation timed out.")
            return redirect("recipe_detail", pk=pk)
        except subprocess.CalledProcessError as e:
            messages.error(
                request,
                f"Error generating PDF: {e.stderr if e.stderr else str(e)}",
            )
            return redirect("recipe_detail", pk=pk)

        # Check if PDF was created
        if not output_pdf.exists():
            messages.error(request, "PDF file was not generated.")
            return redirect("recipe_detail", pk=pk)

        # Read the PDF file
        with open(output_pdf, "rb") as pdf_file:
            pdf_content = pdf_file.read()

        # Create response with PDF
        response = HttpResponse(pdf_content, content_type="application/pdf")

        # Sanitize filename
        safe_title = "".join(
            c if c.isalnum() or c in (" ", "-", "_") else "_" for c in recipe.title
        )
        safe_title = safe_title.replace(" ", "_")
        response["Content-Disposition"] = f'attachment; filename="{safe_title}.pdf"'

        return response


# Recipe Collection Views


class CollectionListView(ListView):
    """Display a list of all recipe collections."""

    model = RecipeCollection
    template_name = "recipes/collection_list.html"
    context_object_name = "collections"
    paginate_by = 20


class CollectionDetailView(DetailView):
    """Display a single collection with all its recipes."""

    model = RecipeCollection
    template_name = "recipes/collection_detail.html"
    context_object_name = "collection"


class CollectionCreateView(CreateView):
    """Create a new recipe collection."""

    model = RecipeCollection
    fields = ["name", "description", "recipes"]
    template_name = "recipes/collection_form.html"

    def get_form(
        self, form_class: type[forms.ModelForm] | None = None
    ) -> forms.ModelForm:  # type: ignore[override]
        """Customize the form to add Bootstrap classes."""
        form = super().get_form(form_class)
        form.fields["name"].widget.attrs.update({"class": "form-control"})
        form.fields["description"].widget.attrs.update(
            {"class": "form-control", "rows": 3}
        )
        form.fields["recipes"].widget.attrs.update(
            {"class": "form-select", "size": "10"}
        )
        form.fields["recipes"].help_text = "Hold Ctrl/Cmd to select multiple recipes"
        return form

    def form_valid(self, form: forms.ModelForm) -> HttpResponse:  # type: ignore[override]
        """Save the collection and show success message."""
        messages.success(
            self.request,
            f"Collection '{form.instance.name}' created successfully!",
        )
        return super().form_valid(form)

    def get_success_url(self) -> str:
        """Redirect to collection detail page."""
        assert self.object is not None
        return str(reverse_lazy("collection_detail", kwargs={"pk": self.object.pk}))


class CollectionUpdateView(UpdateView):
    """Update an existing recipe collection."""

    model = RecipeCollection
    fields = ["name", "description", "recipes"]
    template_name = "recipes/collection_form.html"

    def get_form(
        self, form_class: type[forms.ModelForm] | None = None
    ) -> forms.ModelForm:  # type: ignore[override]
        """Customize the form to add Bootstrap classes."""
        form = super().get_form(form_class)
        form.fields["name"].widget.attrs.update({"class": "form-control"})
        form.fields["description"].widget.attrs.update(
            {"class": "form-control", "rows": 3}
        )
        form.fields["recipes"].widget.attrs.update(
            {"class": "form-select", "size": "10"}
        )
        form.fields["recipes"].help_text = "Hold Ctrl/Cmd to select multiple recipes"
        return form

    def form_valid(self, form: forms.ModelForm) -> HttpResponse:  # type: ignore[override]
        """Save the collection and show success message."""
        messages.success(
            self.request,
            f"Collection '{form.instance.name}' updated successfully!",
        )
        return super().form_valid(form)

    def get_success_url(self) -> str:
        """Redirect to collection detail page."""
        assert self.object is not None
        return str(reverse_lazy("collection_detail", kwargs={"pk": self.object.pk}))


class CollectionDeleteView(DeleteView):
    """Delete a collection after confirmation."""

    model = RecipeCollection
    template_name = "recipes/collection_confirm_delete.html"
    success_url = reverse_lazy("collection_list")

    def delete(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Delete the collection and show a success message."""
        collection = self.get_object()
        messages.success(
            request, f"Collection '{collection.name}' deleted successfully!"
        )
        return super().delete(request, *args, **kwargs)


# Ingredient and Unit Management Views


def manage_ingredient_names(request: HttpRequest) -> HttpResponse:
    """View and manage distinct ingredient names."""
    # Get all distinct ingredient names with usage counts
    ingredients = (
        Ingredient.objects.values("name")
        .annotate(usage_count=django_models.Count("id"))
        .order_by("name")
    )

    # Handle search query
    query = request.GET.get("q")
    if query:
        ingredients = ingredients.filter(name__icontains=query)

    return render(
        request,
        "recipes/manage_ingredient_names.html",
        {"ingredients": ingredients, "query": query},
    )


def rename_ingredient_name(request: HttpRequest) -> HttpResponse:
    """Rename an ingredient name across all recipes."""
    if request.method == "POST":
        old_name = request.POST.get("old_name", "").strip()
        new_name = request.POST.get("new_name", "").strip()

        if not old_name or not new_name:
            messages.error(request, "Both old and new names are required.")
            return redirect("manage_ingredient_names")

        if old_name == new_name:
            messages.warning(request, "Old and new names are the same.")
            return redirect("manage_ingredient_names")

        # Check if old name exists
        count = Ingredient.objects.filter(name=old_name).count()
        if count == 0:
            messages.error(request, f"No ingredients found with name '{old_name}'.")
            return redirect("manage_ingredient_names")

        # Update all ingredients with the old name
        with transaction.atomic():
            updated = Ingredient.objects.filter(name=old_name).update(name=new_name)

        plural = "" if updated == 1 else "s"
        messages.success(
            request,
            f"Renamed '{old_name}' to '{new_name}' in {updated} ingredient{plural}.",
        )
        return redirect("manage_ingredient_names")

    # GET request - show rename form
    old_name = request.GET.get("name", "")
    usage_count = Ingredient.objects.filter(name=old_name).count() if old_name else 0

    return render(
        request,
        "recipes/rename_ingredient_name.html",
        {"old_name": old_name, "usage_count": usage_count},
    )


def manage_units(request: HttpRequest) -> HttpResponse:
    """View and manage distinct units."""
    # Get all distinct units with usage counts
    units = (
        Ingredient.objects.exclude(unit="")
        .values("unit")
        .annotate(usage_count=django_models.Count("id"))
        .order_by("unit")
    )

    # Handle search query
    query = request.GET.get("q")
    if query:
        units = units.filter(unit__icontains=query)

    return render(
        request, "recipes/manage_units.html", {"units": units, "query": query}
    )


def rename_unit(request: HttpRequest) -> HttpResponse:
    """Rename a unit across all recipes."""
    if request.method == "POST":
        old_unit = request.POST.get("old_unit", "").strip()
        new_unit = request.POST.get("new_unit", "").strip()

        if not old_unit:
            messages.error(request, "Old unit name is required.")
            return redirect("manage_units")

        if old_unit == new_unit:
            messages.warning(request, "Old and new units are the same.")
            return redirect("manage_units")

        # Check if old unit exists
        count = Ingredient.objects.filter(unit=old_unit).count()
        if count == 0:
            messages.error(request, f"No ingredients found with unit '{old_unit}'.")
            return redirect("manage_units")

        # Update all ingredients with the old unit
        with transaction.atomic():
            updated = Ingredient.objects.filter(unit=old_unit).update(unit=new_unit)

        plural = "" if updated == 1 else "s"
        msg = (
            f"Renamed unit '{old_unit}' to '{new_unit}' "
            f"in {updated} ingredient{plural}."
        )
        messages.success(request, msg)
        return redirect("manage_units")

    # GET request - show rename form
    old_unit = request.GET.get("unit", "")
    usage_count = Ingredient.objects.filter(unit=old_unit).count() if old_unit else 0

    return render(
        request,
        "recipes/rename_unit.html",
        {"old_unit": old_unit, "usage_count": usage_count},
    )
