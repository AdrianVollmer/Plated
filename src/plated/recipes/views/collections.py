from __future__ import annotations

import json
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from django import forms
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from ..models import Recipe, RecipeCollection
from ..schema import serialize_recipe

logger = logging.getLogger(__name__)


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


class CollectionFormMixin:
    """Mixin for collection form customization."""

    def get_form(self, form_class: type[forms.ModelForm] | None = None) -> forms.ModelForm:  # type: ignore[override]
        """Customize the form to add Bootstrap classes."""
        form = super().get_form(form_class)  # type: ignore[misc]
        form.fields["name"].widget.attrs.update({"class": "form-control"})
        form.fields["description"].widget.attrs.update({"class": "form-control", "rows": 3})
        form.fields["recipes"].widget.attrs.update({"class": "form-select", "size": "10"})
        form.fields["recipes"].help_text = "Hold Ctrl/Cmd to select multiple recipes"
        return form

    def get_success_url(self) -> str:
        """Redirect to collection detail page."""
        assert self.object is not None  # type: ignore[attr-defined]
        return str(reverse_lazy("collection_detail", kwargs={"pk": self.object.pk}))  # type: ignore[attr-defined]


class CollectionCreateView(CollectionFormMixin, CreateView):  # type: ignore[misc]
    """Create a new recipe collection."""

    model = RecipeCollection
    fields = ["name", "description", "recipes"]
    template_name = "recipes/collection_form.html"

    def form_valid(self, form: forms.ModelForm) -> HttpResponse:  # type: ignore[override]
        """Save the collection and show success message."""
        result = super().form_valid(form)
        logger.info(f"Collection created: '{form.instance.name}' (ID: {form.instance.pk})")
        messages.success(
            self.request,
            _("Collection '%(name)s' created successfully!") % {"name": form.instance.name},
        )
        return result


class CollectionUpdateView(CollectionFormMixin, UpdateView):  # type: ignore[misc]
    """Update an existing recipe collection."""

    model = RecipeCollection
    fields = ["name", "description", "recipes"]
    template_name = "recipes/collection_form.html"

    def form_valid(self, form: forms.ModelForm) -> HttpResponse:  # type: ignore[override]
        """Save the collection and show success message."""
        result = super().form_valid(form)
        logger.info(f"Collection updated: '{form.instance.name}' (ID: {form.instance.pk})")
        messages.success(
            self.request,
            _("Collection '%(name)s' updated successfully!") % {"name": form.instance.name},
        )
        return result


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
        messages.success(request, _("Collection '%(name)s' deleted successfully!") % {"name": collection_name})
        return super().delete(request, *args, **kwargs)


def add_recipe_to_collections(request: HttpRequest, recipe_pk: int) -> HttpResponse:
    """Add or remove a recipe from collections."""
    recipe = get_object_or_404(Recipe, pk=recipe_pk)

    if request.method == "POST":
        # Get the list of collection IDs from the form
        collection_ids = request.POST.getlist("collections")
        logger.debug(f"Adding recipe {recipe_pk} to collections: {collection_ids}")

        # Get all collections
        all_collections = RecipeCollection.objects.all()

        # Update collections: add or remove recipe based on checkbox state
        for collection in all_collections:
            if str(collection.pk) in collection_ids:
                # Add recipe to collection if not already there
                if recipe not in collection.recipes.all():
                    collection.recipes.add(recipe)
                    logger.info(f"Added recipe '{recipe.title}' to collection '{collection.name}'")
            else:
                # Remove recipe from collection if it's there
                if recipe in collection.recipes.all():
                    collection.recipes.remove(recipe)
                    logger.info(f"Removed recipe '{recipe.title}' from collection '{collection.name}'")

        messages.success(
            request,
            _("Recipe '%(recipe)s' collections updated successfully!") % {"recipe": recipe.title},
        )
        return redirect("recipe_detail", pk=recipe_pk)

    # GET request - redirect to recipe detail
    return redirect("recipe_detail", pk=recipe_pk)


def download_collection_pdf(request: HttpRequest, pk: int) -> HttpResponse:
    """Generate and download a collection as a PDF using Typst."""
    collection = get_object_or_404(
        RecipeCollection.objects.prefetch_related("recipes__ingredients", "recipes__steps"), pk=pk
    )
    logger.info(f"PDF generation initiated for collection: '{collection.name}' (ID: {pk})")

    try:
        # Serialize collection data
        collection_data = {
            "name": collection.name,
            "description": collection.description,
            "recipes": [serialize_recipe(recipe) for recipe in collection.recipes.all()],
        }

        # Get the path to the Typst template
        base_dir = Path(__file__).resolve().parent.parent
        typst_template = base_dir / "typst" / "collection.typ"

        if not typst_template.exists():
            logger.error(f"Typst template not found at {typst_template}")
            messages.error(request, _("Typst template file not found."))
            return redirect("collection_detail", pk=pk)

        # Create temporary directory for intermediate files
        with tempfile.TemporaryDirectory(prefix="plated_typst_") as temp_dir:
            temp_path = Path(temp_dir)
            logger.debug(f"Using temporary directory: {temp_dir}")

            # Copy typst template to temp directory
            temp_typst = temp_path / "collection.typ"
            shutil.copy(typst_template, temp_typst)

            # Write collection JSON to temp directory
            collection_json_path = temp_path / "collection.json"
            with open(collection_json_path, "w", encoding="utf-8") as f:
                json.dump(collection_data, f, indent=2, ensure_ascii=False)

            # Prepare output PDF path
            output_pdf = temp_path / "collection.pdf"

            # Prepare Typst input data with relative paths
            typst_input_data = json.dumps({"collection": "collection.json"})

            # Call Typst to compile the PDF
            try:
                logger.debug(f"Running Typst compiler for collection '{collection.name}'")
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
                return redirect("collection_detail", pk=pk)
            except subprocess.TimeoutExpired:
                logger.error(f"Typst compilation timed out for collection '{collection.name}' (ID: {pk})")
                messages.error(request, _("PDF generation timed out."))
                return redirect("collection_detail", pk=pk)
            except subprocess.CalledProcessError as e:
                logger.error(
                    f"Typst compilation failed for collection '{collection.name}' (ID: {pk}): {e.stderr}",
                    exc_info=True,
                )
                messages.error(
                    request,
                    _("Error generating PDF: %(error)s") % {"error": e.stderr if e.stderr else str(e)},
                )
                return redirect("collection_detail", pk=pk)

            # Check if PDF was created
            if not output_pdf.exists():
                logger.error(f"PDF file not created for collection '{collection.name}' (ID: {pk})")
                messages.error(request, _("PDF file was not generated."))
                return redirect("collection_detail", pk=pk)

            # Read the PDF file
            with open(output_pdf, "rb") as pdf_file:
                pdf_content = pdf_file.read()

            # Create response with PDF
            response = HttpResponse(pdf_content, content_type="application/pdf")

            # Sanitize filename
            safe_name = "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in collection.name)
            safe_name = safe_name.replace(" ", "_")
            response["Content-Disposition"] = f'attachment; filename="{safe_name}.pdf"'

            logger.info(f"PDF generated successfully for collection '{collection.name}' (ID: {pk})")
            return response
    except Exception as e:
        logger.error(
            f"Unexpected error generating PDF for collection '{collection.name}' (ID: {pk}): {e}",
            exc_info=True,
        )
        messages.error(request, _("Error generating PDF: %(error)s") % {"error": e})
        return redirect("collection_detail", pk=pk)
