from __future__ import annotations

import json
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, cast

import requests
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

from .forms import AIRecipeExtractionForm, AISettingsForm, RecipeForm
from .models import AISettings, Ingredient, Recipe, RecipeCollection, RecipeImage, Step
from .schema import deserialize_recipe, serialize_recipe, validate_recipe_data

logger = logging.getLogger(__name__)


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
            logger.info(f"Recipe search performed with query: '{query}'")
            queryset = queryset.filter(title__icontains=query) | queryset.filter(keywords__icontains=query)
            logger.debug(f"Search returned {queryset.count()} results")
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

    def get_initial(self) -> dict[str, Any]:
        """Get initial data, including AI-extracted recipe if available."""
        initial = super().get_initial()

        # Check if there's AI-extracted recipe data in the session
        ai_recipe_data = self.request.session.get("ai_extracted_recipe")
        if ai_recipe_data:
            logger.info("Pre-filling recipe form with AI-extracted data")
            # Deserialize the recipe data
            deserialized = deserialize_recipe(ai_recipe_data)
            recipe_data = deserialized["recipe_data"]

            # Update initial data with recipe fields
            initial.update(recipe_data)

            # Store ingredients and steps data for formsets
            self.request.session["ai_ingredients_data"] = deserialized["ingredients_data"]
            self.request.session["ai_steps_data"] = deserialized["steps_data"]

            # Clear the AI-extracted recipe from session
            del self.request.session["ai_extracted_recipe"]

        return initial

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add formsets to the context."""
        data = super().get_context_data(**kwargs)

        # Check if there's AI-extracted ingredients and steps data
        ai_ingredients_data = self.request.session.get("ai_ingredients_data", [])
        ai_steps_data = self.request.session.get("ai_steps_data", [])

        # Determine extra forms based on AI data
        extra_ingredients = max(1, len(ai_ingredients_data))
        extra_steps = max(1, len(ai_steps_data))

        IngredientFormSet = get_ingredient_formset(extra=extra_ingredients)  # noqa: N806
        StepFormSet = get_step_formset(extra=extra_steps)  # noqa: N806
        ImageFormSet = get_image_formset(extra=0)  # noqa: N806

        if self.request.POST:
            data["ingredient_formset"] = IngredientFormSet(self.request.POST, prefix="ingredients")
            data["step_formset"] = StepFormSet(self.request.POST, prefix="steps")
            data["image_formset"] = ImageFormSet(self.request.POST, self.request.FILES, prefix="images")
        else:
            # Pre-fill formsets with AI data if available
            if ai_ingredients_data:
                data["ingredient_formset"] = IngredientFormSet(initial=ai_ingredients_data, prefix="ingredients")
                # Clear from session after using
                del self.request.session["ai_ingredients_data"]
            else:
                data["ingredient_formset"] = IngredientFormSet(prefix="ingredients")

            if ai_steps_data:
                data["step_formset"] = StepFormSet(initial=ai_steps_data, prefix="steps")
                # Clear from session after using
                del self.request.session["ai_steps_data"]
            else:
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
            logger.warning("Recipe creation failed: ingredient formset validation error")
            return self.form_invalid(form)

        if not step_formset.is_valid():
            logger.warning("Recipe creation failed: step formset validation error")
            return self.form_invalid(form)

        if not image_formset.is_valid():
            logger.warning("Recipe creation failed: image formset validation error")
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
            logger.warning("Recipe creation failed: no ingredients provided")
            messages.error(self.request, "Please add at least one ingredient to the recipe.")
            return self.form_invalid(form)

        if step_count == 0:
            logger.warning("Recipe creation failed: no steps provided")
            messages.error(self.request, "Please add at least one instruction step to the recipe.")
            return self.form_invalid(form)

        try:
            with transaction.atomic():
                self.object = form.save()
                ingredient_formset.instance = self.object
                ingredient_formset.save()
                step_formset.instance = self.object
                step_formset.save()
                image_formset.instance = self.object
                image_formset.save()

            logger.info(
                f"Recipe created: '{self.object.title}' (ID: {self.object.pk}, "
                f"Ingredients: {ingredient_count}, Steps: {step_count})"
            )
            messages.success(self.request, f"Recipe '{self.object.title}' created successfully!")
            return redirect("recipe_detail", pk=self.object.pk)
        except Exception as e:
            logger.error(f"Error creating recipe: {e}", exc_info=True)
            messages.error(self.request, f"Error creating recipe: {e}")
            return self.form_invalid(form)


class RecipeUpdateView(UpdateView):
    """Update an existing recipe with ingredients, steps, and images."""

    model = Recipe
    form_class = RecipeForm
    template_name = "recipes/recipe_form.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add formsets to the context."""
        data = super().get_context_data(**kwargs)

        # No extra forms - users can add more dynamically if needed
        IngredientFormSet = get_ingredient_formset(extra=0)  # noqa: N806
        StepFormSet = get_step_formset(extra=0)  # noqa: N806
        ImageFormSet = get_image_formset(extra=0)  # noqa: N806

        if self.request.POST:
            data["ingredient_formset"] = IngredientFormSet(
                self.request.POST, instance=self.object, prefix="ingredients"
            )
            data["step_formset"] = StepFormSet(self.request.POST, instance=self.object, prefix="steps")
            data["image_formset"] = ImageFormSet(
                self.request.POST,
                self.request.FILES,
                instance=self.object,
                prefix="images",
            )
        else:
            data["ingredient_formset"] = IngredientFormSet(instance=self.object, prefix="ingredients")
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
            logger.warning(
                f"Recipe update failed for '{self.object.title}' (ID: {self.object.pk}): "
                "ingredient formset validation error"
            )
            return self.form_invalid(form)

        if not step_formset.is_valid():
            logger.warning(
                f"Recipe update failed for '{self.object.title}' (ID: {self.object.pk}): step formset validation error"
            )
            return self.form_invalid(form)

        if not image_formset.is_valid():
            logger.warning(
                f"Recipe update failed for '{self.object.title}' (ID: {self.object.pk}): image formset validation error"
            )
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
            logger.warning(
                f"Recipe update failed for '{self.object.title}' (ID: {self.object.pk}): no ingredients provided"
            )
            messages.error(self.request, "Please add at least one ingredient to the recipe.")
            return self.form_invalid(form)

        if step_count == 0:
            logger.warning(f"Recipe update failed for '{self.object.title}' (ID: {self.object.pk}): no steps provided")
            messages.error(self.request, "Please add at least one instruction step to the recipe.")
            return self.form_invalid(form)

        try:
            with transaction.atomic():
                self.object = form.save()
                ingredient_formset.instance = self.object
                ingredient_formset.save()
                step_formset.instance = self.object
                step_formset.save()
                image_formset.instance = self.object
                image_formset.save()

            logger.info(
                f"Recipe updated: '{self.object.title}' (ID: {self.object.pk}, "
                f"Ingredients: {ingredient_count}, Steps: {step_count})"
            )
            messages.success(self.request, f"Recipe '{self.object.title}' updated successfully!")
            return redirect("recipe_detail", pk=self.object.pk)
        except Exception as e:
            logger.error(
                f"Error updating recipe '{self.object.title}' (ID: {self.object.pk}): {e}",
                exc_info=True,
            )
            messages.error(self.request, f"Error updating recipe: {e}")
            return self.form_invalid(form)


class RecipeDeleteView(DeleteView):
    """Delete a recipe after confirmation."""

    model = Recipe
    template_name = "recipes/recipe_confirm_delete.html"
    success_url = reverse_lazy("recipe_list")

    def delete(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Delete the recipe and show a success message."""
        recipe = self.get_object()
        recipe_title = recipe.title
        recipe_id = recipe.pk
        logger.info(f"Recipe deleted: '{recipe_title}' (ID: {recipe_id})")
        messages.success(request, f"Recipe '{recipe_title}' deleted successfully!")
        return super().delete(request, *args, **kwargs)


def get_ingredient_names(request: HttpRequest) -> JsonResponse:
    """API endpoint to get distinct ingredient names for autocomplete."""
    names = Ingredient.objects.values_list("name", flat=True).distinct().order_by("name")
    return JsonResponse({"names": list(names)})


def get_ingredient_units(request: HttpRequest) -> JsonResponse:
    """API endpoint to get distinct ingredient units for autocomplete."""
    units = Ingredient.objects.exclude(unit="").values_list("unit", flat=True).distinct().order_by("unit")
    return JsonResponse({"units": list(units)})


def get_keywords(request: HttpRequest) -> JsonResponse:
    """API endpoint to get distinct keywords for autocomplete."""
    # Get all non-empty keywords from recipes
    all_keywords_raw = Recipe.objects.exclude(keywords="").values_list("keywords", flat=True)

    # Split comma-separated keywords and clean them up
    keywords_set = set()
    for keywords_str in all_keywords_raw:
        for keyword in keywords_str.split(","):
            keyword = keyword.strip()
            if keyword:  # Only add non-empty keywords
                keywords_set.add(keyword)

    # Convert to sorted list
    keywords_list = sorted(keywords_set, key=str.lower)

    return JsonResponse({"keywords": keywords_list})


def export_recipe(request: HttpRequest, pk: int) -> HttpResponse:
    """Export a recipe as a JSON file."""
    recipe = get_object_or_404(Recipe, pk=pk)
    logger.info(f"Exporting recipe: '{recipe.title}' (ID: {pk})")

    try:
        recipe_data = serialize_recipe(recipe)

        # Create JSON response with proper filename
        response = HttpResponse(
            json.dumps(recipe_data, indent=2, ensure_ascii=False),
            content_type="application/json",
        )
        # Sanitize filename by replacing spaces and special chars
        safe_title = "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in recipe.title)
        safe_title = safe_title.replace(" ", "_")
        response["Content-Disposition"] = f'attachment; filename="{safe_title}.json"'

        logger.debug(f"Recipe export successful: '{recipe.title}' (ID: {pk})")
        return response
    except Exception as e:
        logger.error(f"Error exporting recipe '{recipe.title}' (ID: {pk}): {e}", exc_info=True)
        messages.error(request, f"Error exporting recipe: {e}")
        return redirect("recipe_detail", pk=pk)


def import_recipe(request: HttpRequest) -> HttpResponse:
    """Import a recipe from a JSON file."""
    if request.method == "POST":
        logger.info("Recipe import initiated")

        if "json_file" not in request.FILES:
            logger.warning("Recipe import failed: no file uploaded")
            messages.error(request, "No file was uploaded.")
            return redirect("recipe_import")

        json_file = cast(UploadedFile, request.FILES["json_file"])
        logger.debug(f"Importing recipe from file: {json_file.name}")

        # Read and parse JSON
        try:
            content = json_file.read().decode("utf-8")
            data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Recipe import failed: invalid JSON in file {json_file.name}: {e}")
            messages.error(request, f"Invalid JSON file: {e}")
            return redirect("recipe_import")
        except Exception as e:
            logger.error(f"Recipe import failed: error reading file {json_file.name}: {e}")
            messages.error(request, f"Error reading file: {e}")
            return redirect("recipe_import")

        # Validate the data
        errors = validate_recipe_data(data)
        if errors:
            logger.warning(f"Recipe import validation failed for file {json_file.name}: {len(errors)} errors")
            for error in errors:
                logger.debug(f"Validation error: {error}")
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

            logger.info(f"Recipe imported successfully: '{recipe.title}' (ID: {recipe.pk}) from file {json_file.name}")
            messages.success(
                request,
                f"Recipe '{recipe.title}' imported successfully! You can now add images if needed.",
            )
            return redirect("recipe_detail", pk=recipe.pk)

        except Exception as e:
            logger.error(
                f"Error creating recipe from import file {json_file.name}: {e}",
                exc_info=True,
            )
            messages.error(request, f"Error creating recipe: {e}")
            return redirect("recipe_import")

    # GET request - show the upload form
    return render(request, "recipes/recipe_import.html")


def download_recipe_pdf(request: HttpRequest, pk: int) -> HttpResponse:
    """Generate and download a recipe as a PDF using Typst."""
    recipe = get_object_or_404(Recipe, pk=pk)
    logger.info(f"PDF generation initiated for recipe: '{recipe.title}' (ID: {pk})")

    try:
        recipe_data = serialize_recipe(recipe)

        # Get the path to the Typst template
        base_dir = Path(__file__).resolve().parent.parent
        typst_template = base_dir / "recipe.typ"

        if not typst_template.exists():
            logger.error(f"Typst template not found at {typst_template}")
            messages.error(request, "Typst template file not found.")
            return redirect("recipe_detail", pk=pk)

        # Create temporary directory for intermediate files
        with tempfile.TemporaryDirectory(prefix="plated_typst_") as temp_dir:
            temp_path = Path(temp_dir)
            logger.debug(f"Using temporary directory: {temp_dir}")

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
                logger.debug(f"Running Typst compiler for recipe '{recipe.title}'")
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
                logger.error("Typst executable not found on system")
                messages.error(
                    request,
                    "Typst is not installed. Please install Typst to generate PDFs.",
                )
                return redirect("recipe_detail", pk=pk)
            except subprocess.TimeoutExpired:
                logger.error(f"Typst compilation timed out for recipe '{recipe.title}' (ID: {pk})")
                messages.error(request, "PDF generation timed out.")
                return redirect("recipe_detail", pk=pk)
            except subprocess.CalledProcessError as e:
                logger.error(
                    f"Typst compilation failed for recipe '{recipe.title}' (ID: {pk}): {e.stderr}",
                    exc_info=True,
                )
                messages.error(
                    request,
                    f"Error generating PDF: {e.stderr if e.stderr else str(e)}",
                )
                return redirect("recipe_detail", pk=pk)

            # Check if PDF was created
            if not output_pdf.exists():
                logger.error(f"PDF file not created for recipe '{recipe.title}' (ID: {pk})")
                messages.error(request, "PDF file was not generated.")
                return redirect("recipe_detail", pk=pk)

            # Read the PDF file
            with open(output_pdf, "rb") as pdf_file:
                pdf_content = pdf_file.read()

            # Create response with PDF
            response = HttpResponse(pdf_content, content_type="application/pdf")

            # Sanitize filename
            safe_title = "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in recipe.title)
            safe_title = safe_title.replace(" ", "_")
            response["Content-Disposition"] = f'attachment; filename="{safe_title}.pdf"'

            logger.info(f"PDF generated successfully for recipe '{recipe.title}' (ID: {pk})")
            return response
    except Exception as e:
        logger.error(
            f"Unexpected error generating PDF for recipe '{recipe.title}' (ID: {pk}): {e}",
            exc_info=True,
        )
        messages.error(request, f"Error generating PDF: {e}")
        return redirect("recipe_detail", pk=pk)


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

    def get_form(self, form_class: type[forms.ModelForm] | None = None) -> forms.ModelForm:  # type: ignore[override]
        """Customize the form to add Bootstrap classes."""
        form = super().get_form(form_class)
        form.fields["name"].widget.attrs.update({"class": "form-control"})
        form.fields["description"].widget.attrs.update({"class": "form-control", "rows": 3})
        form.fields["recipes"].widget.attrs.update({"class": "form-select", "size": "10"})
        form.fields["recipes"].help_text = "Hold Ctrl/Cmd to select multiple recipes"
        return form

    def form_valid(self, form: forms.ModelForm) -> HttpResponse:  # type: ignore[override]
        """Save the collection and show success message."""
        result = super().form_valid(form)
        logger.info(f"Collection created: '{form.instance.name}' (ID: {form.instance.pk})")
        messages.success(
            self.request,
            f"Collection '{form.instance.name}' created successfully!",
        )
        return result

    def get_success_url(self) -> str:
        """Redirect to collection detail page."""
        assert self.object is not None
        return str(reverse_lazy("collection_detail", kwargs={"pk": self.object.pk}))


class CollectionUpdateView(UpdateView):
    """Update an existing recipe collection."""

    model = RecipeCollection
    fields = ["name", "description", "recipes"]
    template_name = "recipes/collection_form.html"

    def get_form(self, form_class: type[forms.ModelForm] | None = None) -> forms.ModelForm:  # type: ignore[override]
        """Customize the form to add Bootstrap classes."""
        form = super().get_form(form_class)
        form.fields["name"].widget.attrs.update({"class": "form-control"})
        form.fields["description"].widget.attrs.update({"class": "form-control", "rows": 3})
        form.fields["recipes"].widget.attrs.update({"class": "form-select", "size": "10"})
        form.fields["recipes"].help_text = "Hold Ctrl/Cmd to select multiple recipes"
        return form

    def form_valid(self, form: forms.ModelForm) -> HttpResponse:  # type: ignore[override]
        """Save the collection and show success message."""
        result = super().form_valid(form)
        logger.info(f"Collection updated: '{form.instance.name}' (ID: {form.instance.pk})")
        messages.success(
            self.request,
            f"Collection '{form.instance.name}' updated successfully!",
        )
        return result

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
        collection_name = collection.name
        collection_id = collection.pk
        logger.info(f"Collection deleted: '{collection_name}' (ID: {collection_id})")
        messages.success(request, f"Collection '{collection_name}' deleted successfully!")
        return super().delete(request, *args, **kwargs)


# Ingredient and Unit Management Views


def manage_ingredient_names(request: HttpRequest) -> HttpResponse:
    """View and manage distinct ingredient names."""
    # Get all distinct ingredient names with usage counts
    ingredients = Ingredient.objects.values("name").annotate(usage_count=django_models.Count("id")).order_by("name")

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

        logger.info(f"Ingredient rename requested: '{old_name}' -> '{new_name}'")

        if not old_name or not new_name:
            logger.warning("Ingredient rename failed: missing old or new name")
            messages.error(request, "Both old and new names are required.")
            return redirect("manage_ingredient_names")

        if old_name == new_name:
            logger.warning(f"Ingredient rename skipped: old and new names are identical ('{old_name}')")
            messages.warning(request, "Old and new names are the same.")
            return redirect("manage_ingredient_names")

        # Check if old name exists
        count = Ingredient.objects.filter(name=old_name).count()
        if count == 0:
            logger.warning(f"Ingredient rename failed: no ingredients found with name '{old_name}'")
            messages.error(request, f"No ingredients found with name '{old_name}'.")
            return redirect("manage_ingredient_names")

        # Update all ingredients with the old name
        try:
            with transaction.atomic():
                updated = Ingredient.objects.filter(name=old_name).update(name=new_name)

            logger.info(f"Ingredient renamed: '{old_name}' -> '{new_name}' ({updated} occurrences)")
            plural = "" if updated == 1 else "s"
            messages.success(
                request,
                f"Renamed '{old_name}' to '{new_name}' in {updated} ingredient{plural}.",
            )
            return redirect("manage_ingredient_names")
        except Exception as e:
            logger.error(
                f"Error renaming ingredient '{old_name}' to '{new_name}': {e}",
                exc_info=True,
            )
            messages.error(request, f"Error renaming ingredient: {e}")
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

    return render(request, "recipes/manage_units.html", {"units": units, "query": query})


def rename_unit(request: HttpRequest) -> HttpResponse:
    """Rename a unit across all recipes."""
    if request.method == "POST":
        old_unit = request.POST.get("old_unit", "").strip()
        new_unit = request.POST.get("new_unit", "").strip()

        logger.info(f"Unit rename requested: '{old_unit}' -> '{new_unit}'")

        if not old_unit:
            logger.warning("Unit rename failed: missing old unit name")
            messages.error(request, "Old unit name is required.")
            return redirect("manage_units")

        if old_unit == new_unit:
            logger.warning(f"Unit rename skipped: old and new units are identical ('{old_unit}')")
            messages.warning(request, "Old and new units are the same.")
            return redirect("manage_units")

        # Check if old unit exists
        count = Ingredient.objects.filter(unit=old_unit).count()
        if count == 0:
            logger.warning(f"Unit rename failed: no ingredients found with unit '{old_unit}'")
            messages.error(request, f"No ingredients found with unit '{old_unit}'.")
            return redirect("manage_units")

        # Update all ingredients with the old unit
        try:
            with transaction.atomic():
                updated = Ingredient.objects.filter(unit=old_unit).update(unit=new_unit)

            logger.info(f"Unit renamed: '{old_unit}' -> '{new_unit}' ({updated} occurrences)")
            plural = "" if updated == 1 else "s"
            msg = f"Renamed unit '{old_unit}' to '{new_unit}' in {updated} ingredient{plural}."
            messages.success(request, msg)
            return redirect("manage_units")
        except Exception as e:
            logger.error(f"Error renaming unit '{old_unit}' to '{new_unit}': {e}", exc_info=True)
            messages.error(request, f"Error renaming unit: {e}")
            return redirect("manage_units")

    # GET request - show rename form
    old_unit = request.GET.get("unit", "")
    usage_count = Ingredient.objects.filter(unit=old_unit).count() if old_unit else 0

    return render(
        request,
        "recipes/rename_unit.html",
        {"old_unit": old_unit, "usage_count": usage_count},
    )


def manage_keywords(request: HttpRequest) -> HttpResponse:
    """View and manage distinct keywords."""
    # Get all non-empty keywords from recipes
    all_keywords_raw = Recipe.objects.exclude(keywords="").values_list("keywords", flat=True)

    # Split comma-separated keywords and count their usage
    keyword_counts: dict[str, int] = {}
    for keywords_str in all_keywords_raw:
        for keyword in keywords_str.split(","):
            keyword = keyword.strip()
            if keyword:  # Only add non-empty keywords
                keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1

    # Convert to list of dicts and sort
    keywords = [{"keyword": k, "usage_count": v} for k, v in keyword_counts.items()]
    keywords.sort(key=lambda x: x["keyword"].lower())

    # Handle search query
    query = request.GET.get("q")
    if query:
        keywords = [k for k in keywords if query.lower() in k["keyword"].lower()]

    return render(
        request,
        "recipes/manage_keywords.html",
        {"keywords": keywords, "query": query},
    )


def recipes_with_ingredient_name(request: HttpRequest, name: str) -> HttpResponse:
    """Show all recipes that use a specific ingredient name."""
    recipes = Recipe.objects.filter(ingredients__name=name).distinct()
    return render(
        request,
        "recipes/recipes_by_property.html",
        {
            "recipes": recipes,
            "property_type": "Ingredient Name",
            "property_value": name,
            "back_url": "manage_ingredient_names",
        },
    )


def recipes_with_unit(request: HttpRequest, unit: str) -> HttpResponse:
    """Show all recipes that use a specific unit."""
    recipes = Recipe.objects.filter(ingredients__unit=unit).distinct()
    return render(
        request,
        "recipes/recipes_by_property.html",
        {
            "recipes": recipes,
            "property_type": "Unit",
            "property_value": unit,
            "back_url": "manage_units",
        },
    )


def recipes_with_keyword(request: HttpRequest, keyword: str) -> HttpResponse:
    """Show all recipes that use a specific keyword."""
    recipes = Recipe.objects.filter(keywords__icontains=keyword).distinct()
    # Further filter to ensure exact keyword match (not just substring)
    filtered_recipes = []
    for recipe in recipes:
        keywords_list = [k.strip() for k in recipe.keywords.split(",")]
        if keyword in keywords_list:
            filtered_recipes.append(recipe)

    return render(
        request,
        "recipes/recipes_by_property.html",
        {
            "recipes": filtered_recipes,
            "property_type": "Keyword",
            "property_value": keyword,
            "back_url": "manage_keywords",
        },
    )


def delete_ingredient_name(request: HttpRequest) -> HttpResponse:
    """Delete an ingredient name if its usage count is 0."""
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        if not name:
            messages.error(request, "Ingredient name is required.")
            return redirect("manage_ingredient_names")

        # Check usage count
        usage_count = Ingredient.objects.filter(name=name).count()
        if usage_count > 0:
            logger.warning(f"Cannot delete ingredient '{name}': usage count is {usage_count}")
            messages.error(
                request,
                f"Cannot delete '{name}' because it is used in {usage_count} recipe{'s' if usage_count > 1 else ''}.",
            )
            return redirect("manage_ingredient_names")

        logger.info(f"Ingredient name deleted (no usage): '{name}'")
        messages.success(request, f"Ingredient name '{name}' deleted (no usage found).")
        return redirect("manage_ingredient_names")

    return redirect("manage_ingredient_names")


def delete_unit(request: HttpRequest) -> HttpResponse:
    """Delete a unit if its usage count is 0."""
    if request.method == "POST":
        unit = request.POST.get("unit", "").strip()
        if not unit:
            messages.error(request, "Unit is required.")
            return redirect("manage_units")

        # Check usage count
        usage_count = Ingredient.objects.filter(unit=unit).count()
        if usage_count > 0:
            logger.warning(f"Cannot delete unit '{unit}': usage count is {usage_count}")
            messages.error(
                request,
                f"Cannot delete '{unit}' because it is used in {usage_count} recipe{'s' if usage_count > 1 else ''}.",
            )
            return redirect("manage_units")

        logger.info(f"Unit deleted (no usage): '{unit}'")
        messages.success(request, f"Unit '{unit}' deleted (no usage found).")
        return redirect("manage_units")

    return redirect("manage_units")


def delete_keyword(request: HttpRequest) -> HttpResponse:
    """Delete a keyword if its usage count is 0."""
    if request.method == "POST":
        keyword = request.POST.get("keyword", "").strip()
        if not keyword:
            messages.error(request, "Keyword is required.")
            return redirect("manage_keywords")

        # Check usage count - count how many recipes have this keyword
        usage_count = 0
        all_keywords_raw = Recipe.objects.exclude(keywords="").values_list("keywords", flat=True)
        for keywords_str in all_keywords_raw:
            keywords_list = [k.strip() for k in keywords_str.split(",")]
            if keyword in keywords_list:
                usage_count += 1

        if usage_count > 0:
            logger.warning(f"Cannot delete keyword '{keyword}': usage count is {usage_count}")
            messages.error(
                request,
                f"Cannot delete '{keyword}' because it is used in {usage_count} recipe{'s' if usage_count > 1 else ''}.",
            )
            return redirect("manage_keywords")

        logger.info(f"Keyword deleted (no usage): '{keyword}'")
        messages.success(request, f"Keyword '{keyword}' deleted (no usage found).")
        return redirect("manage_keywords")

    return redirect("manage_keywords")


# Settings View


def settings_view(request: HttpRequest) -> HttpResponse:
    """Display application settings page."""
    # Since we only support one set of AI settings, get or create it
    ai_settings = AISettings.objects.first()

    if request.method == "POST" and "ai_settings" in request.POST:
        if ai_settings:
            ai_form = AISettingsForm(request.POST, instance=ai_settings)
        else:
            ai_form = AISettingsForm(request.POST)

        if ai_form.is_valid():
            ai_form.save()
            messages.success(request, "AI settings saved successfully!")
            logger.info("AI settings updated")
            return redirect("settings")
    else:
        ai_form = AISettingsForm(instance=ai_settings) if ai_settings else AISettingsForm()

    return render(
        request,
        "recipes/settings.html",
        {"ai_settings": ai_settings, "ai_form": ai_form},
    )


# AI Recipe Extraction


def ai_extract_recipe(request: HttpRequest) -> HttpResponse:
    """Extract a recipe using AI from text, HTML, or URL."""
    # Check if AI settings are configured
    ai_settings = AISettings.objects.first()
    if not ai_settings:
        messages.error(
            request,
            "AI settings are not configured. Please configure AI settings in the settings page.",
        )
        return redirect("settings")

    if request.method == "POST":
        form = AIRecipeExtractionForm(request.POST)
        if form.is_valid():
            input_type = form.cleaned_data["input_type"]
            input_content = form.cleaned_data["input_content"]
            prompt = form.cleaned_data["prompt"]

            logger.info(f"AI recipe extraction initiated with input_type: {input_type}")

            try:
                # Fetch content if it's a URL
                if input_type == "url":
                    logger.debug(f"Fetching content from URL: {input_content}")
                    try:
                        response = requests.get(input_content, timeout=30)
                        response.raise_for_status()
                        content = response.text
                        logger.debug(f"URL content fetched successfully: {len(content)} characters")
                    except requests.RequestException as e:
                        logger.error(f"Error fetching URL {input_content}: {e}")
                        messages.error(request, f"Error fetching URL: {e}")
                        return render(request, "recipes/ai_extract.html", {"form": form})
                else:
                    content = input_content

                # Build the prompt for the LLM
                schema_description = """
Extract the recipe information from the provided content and return it as a JSON object with the following schema:

{
  "title": "Recipe title (required)",
  "description": "Brief description",
  "servings": 4,
  "keywords": "comma, separated, keywords",
  "prep_time_minutes": 30,
  "wait_time_minutes": 45,
  "url": "source URL if applicable",
  "notes": "any additional notes",
  "special_equipment": "special equipment needed",
  "ingredients": [
    {
      "amount": "2",
      "unit": "cups",
      "name": "flour",
      "note": "sifted",
      "order": 0
    }
  ],
  "steps": [
    {
      "content": "Step instructions (markdown supported)",
      "order": 0
    }
  ]
}

IMPORTANT: Return ONLY valid JSON, no additional text or markdown formatting.
"""

                system_message = schema_description
                if prompt:
                    system_message += f"\n\nAdditional instructions: {prompt}"

                user_message = f"Content type: {input_type}\n\nContent:\n{content}"

                # Call the LLM API
                logger.debug(f"Calling LLM API: {ai_settings.api_url}")
                try:
                    # Try OpenAI-compatible API format
                    api_payload = {
                        "model": ai_settings.model,
                        "messages": [
                            {"role": "system", "content": system_message},
                            {"role": "user", "content": user_message},
                        ],
                        "max_tokens": ai_settings.max_tokens,
                        "temperature": ai_settings.temperature,
                    }

                    api_response = requests.post(
                        ai_settings.api_url,
                        headers={
                            "Authorization": f"Bearer {ai_settings.api_key}",
                            "Content-Type": "application/json",
                        },
                        json=api_payload,
                        timeout=120,
                    )
                    api_response.raise_for_status()
                    response_data = api_response.json()

                    logger.debug("LLM API call successful")

                    # Extract the response text (try OpenAI format first)
                    if "choices" in response_data and len(response_data["choices"]) > 0:
                        recipe_json_str = response_data["choices"][0]["message"]["content"]
                    elif "content" in response_data:
                        # Alternative format
                        recipe_json_str = response_data["content"]
                    else:
                        logger.error(f"Unexpected API response format: {response_data}")
                        messages.error(
                            request,
                            "Unexpected response format from AI API. Please check your API configuration.",
                        )
                        return render(request, "recipes/ai_extract.html", {"form": form})

                    # Clean up the response (remove markdown code blocks if present)
                    recipe_json_str = recipe_json_str.strip()
                    if recipe_json_str.startswith("```json"):
                        recipe_json_str = recipe_json_str[7:]
                    if recipe_json_str.startswith("```"):
                        recipe_json_str = recipe_json_str[3:]
                    if recipe_json_str.endswith("```"):
                        recipe_json_str = recipe_json_str[:-3]
                    recipe_json_str = recipe_json_str.strip()

                    # Parse the JSON
                    try:
                        recipe_data = json.loads(recipe_json_str)
                        logger.debug("Recipe JSON parsed successfully")
                    except json.JSONDecodeError as e:
                        logger.error(f"Error parsing recipe JSON: {e}\nJSON string: {recipe_json_str[:500]}")
                        messages.error(
                            request,
                            f"Error parsing AI response as JSON: {e}. The AI may have returned invalid JSON.",
                        )
                        return render(request, "recipes/ai_extract.html", {"form": form})

                    # Validate the recipe data
                    errors = validate_recipe_data(recipe_data)
                    if errors:
                        logger.warning(f"AI-extracted recipe validation failed: {len(errors)} errors")
                        for error in errors[:5]:  # Show first 5 errors
                            messages.error(request, f"Validation error: {error}")
                        return render(request, "recipes/ai_extract.html", {"form": form})

                    # Store the recipe data in the session
                    request.session["ai_extracted_recipe"] = recipe_data
                    logger.info("Recipe extracted successfully via AI, redirecting to recipe form")
                    messages.success(
                        request,
                        "Recipe extracted successfully! Please review and save the recipe.",
                    )
                    return redirect("recipe_create")

                except requests.RequestException as e:
                    logger.error(f"Error calling LLM API: {e}")
                    messages.error(request, f"Error calling AI API: {e}")
                    return render(request, "recipes/ai_extract.html", {"form": form})

            except Exception as e:
                logger.error(f"Unexpected error during AI recipe extraction: {e}", exc_info=True)
                messages.error(request, f"Unexpected error: {e}")
                return render(request, "recipes/ai_extract.html", {"form": form})

    else:
        form = AIRecipeExtractionForm()

    return render(request, "recipes/ai_extract.html", {"form": form})


# PWA Views


def manifest_view(request: HttpRequest) -> JsonResponse:
    """Serve the PWA manifest with proper content type."""
    from django.templatetags.static import static

    manifest = {
        "name": "Plated - Recipe Manager",
        "short_name": "Plated",
        "description": "Your personal recipe manager for organizing, creating, and sharing recipes",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#0d6efd",
        "orientation": "portrait-primary",
        "icons": [
            {
                "src": request.build_absolute_uri(static("icons/icon-72x72.png")),
                "sizes": "72x72",
                "type": "image/png",
                "purpose": "any maskable",
            },
            {
                "src": request.build_absolute_uri(static("icons/icon-96x96.png")),
                "sizes": "96x96",
                "type": "image/png",
                "purpose": "any maskable",
            },
            {
                "src": request.build_absolute_uri(static("icons/icon-128x128.png")),
                "sizes": "128x128",
                "type": "image/png",
                "purpose": "any maskable",
            },
            {
                "src": request.build_absolute_uri(static("icons/icon-144x144.png")),
                "sizes": "144x144",
                "type": "image/png",
                "purpose": "any maskable",
            },
            {
                "src": request.build_absolute_uri(static("icons/icon-152x152.png")),
                "sizes": "152x152",
                "type": "image/png",
                "purpose": "any maskable",
            },
            {
                "src": request.build_absolute_uri(static("icons/icon-192x192.png")),
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any maskable",
            },
            {
                "src": request.build_absolute_uri(static("icons/icon-384x384.png")),
                "sizes": "384x384",
                "type": "image/png",
                "purpose": "any maskable",
            },
            {
                "src": request.build_absolute_uri(static("icons/icon-512x512.png")),
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any maskable",
            },
        ],
    }
    return JsonResponse(manifest, content_type="application/manifest+json")


def service_worker_view(request: HttpRequest) -> HttpResponse:
    """Serve the service worker from the static directory."""
    from django.conf import settings

    service_worker_path = Path(settings.BASE_DIR) / "static" / "service-worker.js"

    try:
        with open(service_worker_path, encoding="utf-8") as f:
            content = f.read()
        return HttpResponse(content, content_type="application/javascript")
    except FileNotFoundError:
        logger.error(f"Service worker not found at {service_worker_path}")
        return HttpResponse("Service worker not found", status=404)
