from __future__ import annotations

import logging
from typing import Any

from django import forms
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from ..models import RecipeCollection

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
            f"Collection '{form.instance.name}' created successfully!",
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
            f"Collection '{form.instance.name}' updated successfully!",
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
        messages.success(request, f"Collection '{collection_name}' deleted successfully!")
        return super().delete(request, *args, **kwargs)
