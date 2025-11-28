from __future__ import annotations

import json
import logging
from typing import Any, cast

from django.contrib import messages
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
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

from ..forms import RecipeForm
from ..models import AISettings, Recipe
from ..schema import deserialize_recipe
from ..services import (
    PDFGenerationError,
    create_image_formset,
    create_ingredient_formset,
    create_step_formset,
    generate_recipe_pdf,
    get_recipes_for_autocomplete,
    sanitize_filename,
    search_recipes,
    validate_recipe_formsets,
)

logger = logging.getLogger(__name__)


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
        return search_recipes(queryset, query)

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

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add all collections and recipe's current collections to context."""
        context = super().get_context_data(**kwargs)
        from ..models import RecipeCollection

        recipe = self.get_object()
        all_collections = RecipeCollection.objects.all()
        recipe_collection_ids = set(recipe.collections.values_list("id", flat=True))

        context["all_collections"] = all_collections
        context["recipe_collection_ids"] = recipe_collection_ids
        return context


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

        IngredientFormSet = create_ingredient_formset(extra=extra_ingredients)  # noqa: N806
        StepFormSet = create_step_formset(extra=extra_steps)  # noqa: N806
        ImageFormSet = create_image_formset(extra=0)  # noqa: N806

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

        # Validate formsets using service
        validation = validate_recipe_formsets(
            self.request, ingredient_formset, step_formset, image_formset, is_create=True
        )

        if not validation.is_valid:
            for error in validation.errors:
                form.add_error(None, error)
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
                f"Ingredients: {validation.ingredient_count}, Steps: {validation.step_count})"
            )
            messages.success(self.request, _("Recipe '%(title)s' created successfully!") % {"title": self.object.title})
            return redirect("recipe_detail", pk=self.object.pk)
        except Exception as e:
            logger.error(f"Error creating recipe: {e}", exc_info=True)
            messages.error(self.request, _("Error creating recipe: %(error)s") % {"error": e})
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
        IngredientFormSet = create_ingredient_formset(extra=0)  # noqa: N806
        StepFormSet = create_step_formset(extra=0)  # noqa: N806
        ImageFormSet = create_image_formset(extra=0)  # noqa: N806

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

        # Validate formsets using service
        validation = validate_recipe_formsets(
            self.request,
            ingredient_formset,
            step_formset,
            image_formset,
            recipe_instance=self.object,
            is_create=False,
        )

        if not validation.is_valid:
            for error in validation.errors:
                form.add_error(None, error)
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
                f"Ingredients: {validation.ingredient_count}, Steps: {validation.step_count})"
            )
            messages.success(self.request, _("Recipe '%(title)s' updated successfully!") % {"title": self.object.title})
            return redirect("recipe_detail", pk=self.object.pk)
        except Exception as e:
            logger.error(
                f"Error updating recipe '{self.object.title}' (ID: {self.object.pk}): {e}",
                exc_info=True,
            )
            messages.error(self.request, _("Error updating recipe: %(error)s") % {"error": e})
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
        messages.success(request, _("Recipe '%(title)s' deleted successfully!") % {"title": recipe_title})
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
        messages.error(request, _("Unknown format: %(format)s") % {"format": format_id})
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
        messages.error(request, _("Error exporting recipe: %(error)s") % {"error": e})
        return redirect("recipe_detail", pk=pk)


def import_recipe(request: HttpRequest) -> HttpResponse:
    """Import a recipe from a file using the selected format handler."""
    from ..services import format_registry

    if request.method == "POST":
        logger.info("Recipe import initiated")

        if "recipe_file" not in request.FILES:
            logger.warning("Recipe import failed: no file uploaded")
            messages.error(request, _("No file was uploaded."))
            return redirect("recipe_import")

        recipe_file = cast(UploadedFile, request.FILES["recipe_file"])
        format_id = request.POST.get("format", "json")
        logger.debug(f"Importing recipe from file: {recipe_file.name} using format: {format_id}")

        # Get the format handler
        handler = format_registry.get_handler(format_id)
        if not handler:
            logger.error(f"Recipe import failed: unknown format '{format_id}'")
            messages.error(request, _("Unknown format: %(format)s") % {"format": format_id})
            return redirect("recipe_import")

        # Read the file content
        try:
            content = recipe_file.read().decode("utf-8")
        except Exception as e:
            logger.error(f"Recipe import failed: error reading file {recipe_file.name}: {e}")
            messages.error(request, _("Error reading file: %(error)s") % {"error": e})
            return redirect("recipe_import")

        # Import using the handler
        try:
            recipe = handler.import_recipe(content)
            logger.info(
                f"Recipe imported successfully: '{recipe.title}' (ID: {recipe.pk}) from file {recipe_file.name}"
            )
            messages.success(
                request,
                _("Recipe '%(title)s' imported successfully! You can now add images if needed.")
                % {"title": recipe.title},
            )
            return redirect("recipe_detail", pk=recipe.pk)

        except Exception as e:
            logger.error(
                f"Error creating recipe from import file {recipe_file.name}: {e}",
                exc_info=True,
            )
            messages.error(request, _("Error creating recipe: %(error)s") % {"error": e})
            return redirect("recipe_import")

    # GET request - show the upload form
    formats = format_registry.get_import_formats()
    return render(request, "recipes/recipe_import.html", {"formats": formats})


def download_recipe_pdf(request: HttpRequest, pk: int) -> HttpResponse:
    """Generate and download a recipe as a PDF using Typst."""
    recipe = get_object_or_404(Recipe, pk=pk)

    try:
        pdf_content = generate_recipe_pdf(recipe)

        # Create response with PDF
        response = HttpResponse(pdf_content, content_type="application/pdf")

        # Sanitize filename
        safe_title = sanitize_filename(recipe.title)
        response["Content-Disposition"] = f'attachment; filename="{safe_title}.pdf"'

        return response
    except PDFGenerationError as e:
        logger.error(f"PDF generation failed for recipe '{recipe.title}' (ID: {pk}): {e}")
        messages.error(request, _("Error generating PDF: %(error)s") % {"error": e})
        return redirect("recipe_detail", pk=pk)


def get_recipes_api(request: HttpRequest) -> HttpResponse:
    """API endpoint to get all recipes for autocomplete."""
    recipes_data = get_recipes_for_autocomplete()
    return HttpResponse(json.dumps(recipes_data), content_type="application/json")
