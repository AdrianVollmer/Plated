from __future__ import annotations

import json
import logging
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

from ..forms import RecipeForm
from ..models import AISettings, Ingredient, Recipe, RecipeImage, Step
from ..schema import deserialize_recipe, serialize_recipe, validate_recipe_data

logger = logging.getLogger(__name__)


def _create_bootstrap_widget(field_name: str, model_field: Any) -> forms.Widget:
    """
    Create a Bootstrap-styled widget based on field type.

    Args:
        field_name: Name of the field
        model_field: Django model field instance

    Returns:
        Appropriately styled widget
    """
    base_class = "form-control"
    small_class = "form-control form-control-sm"

    # Determine widget type based on field
    if isinstance(model_field, django_models.TextField):
        return forms.Textarea(attrs={"class": base_class, "rows": 3})
    elif isinstance(model_field, django_models.IntegerField):
        return forms.NumberInput(attrs={"class": small_class})
    elif isinstance(model_field, django_models.ImageField):
        # Image fields use default widget
        return forms.FileInput(attrs={"class": base_class})
    else:
        # Default to text input for CharField and others
        return forms.TextInput(attrs={"class": small_class})


def _create_inline_formset(
    parent_model: type[django_models.Model],
    child_model: type[django_models.Model],
    fields: tuple[str, ...],
    extra: int = 0,
    custom_widgets: dict[str, forms.Widget] | None = None,
) -> Any:
    """
    Create an inline formset with automatic Bootstrap styling.

    Args:
        parent_model: Parent model class
        child_model: Child model class
        fields: Tuple of field names to include
        extra: Number of empty forms to display
        custom_widgets: Optional dict of custom widgets to override defaults

    Returns:
        Formset factory
    """
    # Build widgets dict with Bootstrap styling
    widgets: dict[str, type[forms.Widget] | forms.Widget] = {}
    for field_name in fields:
        if custom_widgets and field_name in custom_widgets:
            # Use custom widget if provided
            widgets[field_name] = custom_widgets[field_name]
        else:
            # Auto-generate Bootstrap widget
            model_field = child_model._meta.get_field(field_name)
            widgets[field_name] = _create_bootstrap_widget(field_name, model_field)

    return inlineformset_factory(
        parent_model,
        child_model,
        fields=fields,
        extra=extra,
        can_delete=True,
        widgets=widgets,
    )


def get_ingredient_formset(extra: int = 5):
    """Create an ingredient formset with Bootstrap styling."""
    return _create_inline_formset(
        Recipe,
        Ingredient,
        fields=("amount", "unit", "name", "note", "order"),
        extra=extra,
    )


def get_step_formset(extra: int = 3):
    """Create a step formset with Bootstrap styling."""
    return _create_inline_formset(
        Recipe,
        Step,
        fields=("content", "order"),
        extra=extra,
    )


def get_image_formset(extra: int = 2):
    """Create an image formset with Bootstrap styling."""
    return _create_inline_formset(
        Recipe,
        RecipeImage,
        fields=("image", "caption", "order"),
        extra=extra,
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

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add AI settings availability to context."""
        context = super().get_context_data(**kwargs)
        context["ai_settings_available"] = AISettings.objects.exists()
        return context


class RecipeDetailView(DetailView):
    """Display a single recipe with all its details."""

    model = Recipe
    template_name = "recipes/recipe_detail.html"
    context_object_name = "recipe"


def _validate_and_save_recipe_formsets(
    request: HttpRequest,
    form: RecipeForm,
    ingredient_formset: Any,
    step_formset: Any,
    image_formset: Any,
    recipe_instance: Recipe | None = None,
    is_create: bool = True,
) -> tuple[bool, HttpResponse | None, int, int]:
    """
    Common validation and saving logic for recipe formsets.

    Returns:
        tuple: (success, response, ingredient_count, step_count)
        - success: True if validation passed
        - response: HttpResponse to return if validation failed, None otherwise
        - ingredient_count: Number of valid ingredients
        - step_count: Number of valid steps
    """
    action = "creation" if is_create else "update"
    recipe_info = (
        "" if is_create or recipe_instance is None else f" for '{recipe_instance.title}' (ID: {recipe_instance.pk})"
    )

    # Validate formsets
    if not ingredient_formset.is_valid():
        logger.warning(f"Recipe {action} failed{recipe_info}: ingredient formset validation error")
        form.add_error(None, "Invalid ingredient data")
        return False, None, 0, 0

    if not step_formset.is_valid():
        logger.warning(f"Recipe {action} failed{recipe_info}: step formset validation error")
        form.add_error(None, "Invalid step data")
        return False, None, 0, 0

    if not image_formset.is_valid():
        logger.warning(f"Recipe {action} failed{recipe_info}: image formset validation error")
        form.add_error(None, "Invalid image data")
        return False, None, 0, 0

    # Count non-deleted forms
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

    # Validate minimum requirements
    if ingredient_count == 0:
        logger.warning(f"Recipe {action} failed{recipe_info}: no ingredients provided")
        messages.error(request, "Please add at least one ingredient to the recipe.")
        return False, None, 0, 0

    if step_count == 0:
        logger.warning(f"Recipe {action} failed{recipe_info}: no steps provided")
        messages.error(request, "Please add at least one instruction step to the recipe.")
        return False, None, 0, 0

    return True, None, ingredient_count, step_count


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

        # Validate formsets using common helper
        success, response, ingredient_count, step_count = _validate_and_save_recipe_formsets(
            self.request, form, ingredient_formset, step_formset, image_formset, is_create=True
        )

        if not success:
            return self.form_invalid(form)

        # Save everything in a transaction
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

        # Validate formsets using common helper
        success, response, ingredient_count, step_count = _validate_and_save_recipe_formsets(
            self.request,
            form,
            ingredient_formset,
            step_formset,
            image_formset,
            recipe_instance=self.object,
            is_create=False,
        )

        if not success:
            return self.form_invalid(form)

        # Save everything in a transaction
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


def export_recipe(request: HttpRequest, pk: int) -> HttpResponse:
    """Export a recipe using the specified format handler."""
    from ..services import format_registry

    recipe = get_object_or_404(Recipe, pk=pk)
    format_id = request.GET.get("format", "json")
    logger.info(f"Exporting recipe: '{recipe.title}' (ID: {pk}) as {format_id}")

    # Get the format handler
    handler = format_registry.get_handler(format_id)
    if not handler:
        logger.error(f"Recipe export failed: unknown format '{format_id}'")
        messages.error(request, f"Unknown format: {format_id}")
        return redirect("recipe_detail", pk=pk)

    try:
        content = handler.export_recipe(recipe)

        # Create response with proper content type
        response = HttpResponse(content, content_type=handler.mime_type)

        # Sanitize filename by replacing spaces and special chars
        safe_title = "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in recipe.title)
        safe_title = safe_title.replace(" ", "_")
        response["Content-Disposition"] = f'attachment; filename="{safe_title}{handler.file_extension}"'

        logger.debug(f"Recipe export successful: '{recipe.title}' (ID: {pk}) as {format_id}")
        return response
    except Exception as e:
        logger.error(f"Error exporting recipe '{recipe.title}' (ID: {pk}): {e}", exc_info=True)
        messages.error(request, f"Error exporting recipe: {e}")
        return redirect("recipe_detail", pk=pk)


def import_recipe(request: HttpRequest) -> HttpResponse:
    """Import a recipe from a file using the selected format handler."""
    from ..services import format_registry

    if request.method == "POST":
        logger.info("Recipe import initiated")

        if "recipe_file" not in request.FILES:
            logger.warning("Recipe import failed: no file uploaded")
            messages.error(request, "No file was uploaded.")
            return redirect("recipe_import")

        recipe_file = cast(UploadedFile, request.FILES["recipe_file"])
        format_id = request.POST.get("format", "json")
        logger.debug(f"Importing recipe from file: {recipe_file.name} using format: {format_id}")

        # Get the format handler
        handler = format_registry.get_handler(format_id)
        if not handler:
            logger.error(f"Recipe import failed: unknown format '{format_id}'")
            messages.error(request, f"Unknown format: {format_id}")
            return redirect("recipe_import")

        # Read the file content
        try:
            content = recipe_file.read().decode("utf-8")
        except Exception as e:
            logger.error(f"Recipe import failed: error reading file {recipe_file.name}: {e}")
            messages.error(request, f"Error reading file: {e}")
            return redirect("recipe_import")

        # Import using the handler
        try:
            recipe = handler.import_recipe(content)
            logger.info(
                f"Recipe imported successfully: '{recipe.title}' (ID: {recipe.pk}) from file {recipe_file.name}"
            )
            messages.success(
                request,
                f"Recipe '{recipe.title}' imported successfully! You can now add images if needed.",
            )
            return redirect("recipe_detail", pk=recipe.pk)

        except Exception as e:
            logger.error(
                f"Error creating recipe from import file {recipe_file.name}: {e}",
                exc_info=True,
            )
            messages.error(request, f"Error creating recipe: {e}")
            return redirect("recipe_import")

    # GET request - show the upload form
    formats = format_registry.get_import_formats()
    return render(request, "recipes/recipe_import.html", {"formats": formats})


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
                    # TODO render output in `<pre><code>` tags
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


def get_recipes_api(request: HttpRequest) -> HttpResponse:
    """API endpoint to get all recipes for autocomplete."""
    recipes = Recipe.objects.all().order_by("title")
    recipes_data = [{"id": recipe.pk, "title": recipe.title} for recipe in recipes]
    return HttpResponse(json.dumps(recipes_data), content_type="application/json")
