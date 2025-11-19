from __future__ import annotations

from typing import Any

from django import forms
from django.contrib import messages
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

from .forms import RecipeForm
from .models import Ingredient, Recipe, RecipeImage, Step


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

        IngredientFormSet = get_ingredient_formset(extra=5)
        StepFormSet = get_step_formset(extra=3)
        ImageFormSet = get_image_formset(extra=2)

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

        with transaction.atomic():
            self.object = form.save()

            if ingredient_formset.is_valid():
                ingredient_formset.instance = self.object
                ingredient_formset.save()
            else:
                return self.form_invalid(form)

            if step_formset.is_valid():
                step_formset.instance = self.object
                step_formset.save()
            else:
                return self.form_invalid(form)

            if image_formset.is_valid():
                image_formset.instance = self.object
                image_formset.save()
            else:
                return self.form_invalid(form)

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

        IngredientFormSet = get_ingredient_formset(extra=2)
        StepFormSet = get_step_formset(extra=1)
        ImageFormSet = get_image_formset(extra=1)

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

        with transaction.atomic():
            self.object = form.save()

            if ingredient_formset.is_valid():
                ingredient_formset.instance = self.object
                ingredient_formset.save()
            else:
                return self.form_invalid(form)

            if step_formset.is_valid():
                step_formset.instance = self.object
                step_formset.save()
            else:
                return self.form_invalid(form)

            if image_formset.is_valid():
                image_formset.instance = self.object
                image_formset.save()
            else:
                return self.form_invalid(form)

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
