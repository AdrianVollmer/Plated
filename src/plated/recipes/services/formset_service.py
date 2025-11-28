"""Service for creating and validating recipe formsets."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from django import forms
from django.db import models as django_models
from django.forms import inlineformset_factory
from django.utils.translation import gettext as _

if TYPE_CHECKING:
    from django.http import HttpRequest

    from ..models import Recipe

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


def create_ingredient_formset(extra: int = 5) -> Any:
    """
    Create an ingredient formset with Bootstrap styling.

    Args:
        extra: Number of extra empty forms to display

    Returns:
        Ingredient formset class
    """
    from ..models import Ingredient, Recipe

    return _create_inline_formset(
        Recipe,
        Ingredient,
        fields=("amount", "unit", "name", "note", "order"),
        extra=extra,
    )


def create_step_formset(extra: int = 3) -> Any:
    """
    Create a step formset with Bootstrap styling.

    Args:
        extra: Number of extra empty forms to display

    Returns:
        Step formset class
    """
    from ..models import Recipe, Step

    return _create_inline_formset(
        Recipe,
        Step,
        fields=("content", "order"),
        extra=extra,
    )


def create_image_formset(extra: int = 2) -> Any:
    """
    Create an image formset with Bootstrap styling.

    Args:
        extra: Number of extra empty forms to display

    Returns:
        Image formset class
    """
    from ..models import Recipe, RecipeImage

    return _create_inline_formset(
        Recipe,
        RecipeImage,
        fields=("image", "caption", "order"),
        extra=extra,
    )


class FormsetValidationResult:
    """Result of formset validation."""

    def __init__(
        self,
        is_valid: bool,
        ingredient_count: int = 0,
        step_count: int = 0,
        errors: list[str] | None = None,
    ):
        """
        Initialize validation result.

        Args:
            is_valid: Whether validation passed
            ingredient_count: Number of valid ingredients
            step_count: Number of valid steps
            errors: List of validation error messages
        """
        self.is_valid = is_valid
        self.ingredient_count = ingredient_count
        self.step_count = step_count
        self.errors = errors or []


def validate_recipe_formsets(
    request: HttpRequest,
    ingredient_formset: Any,
    step_formset: Any,
    image_formset: Any,
    recipe_instance: Recipe | None = None,
    is_create: bool = True,
) -> FormsetValidationResult:
    """
    Validate recipe formsets and check minimum requirements.

    Args:
        request: HTTP request (for adding messages)
        ingredient_formset: Ingredient formset to validate
        step_formset: Step formset to validate
        image_formset: Image formset to validate
        recipe_instance: Recipe instance (for logging in update mode)
        is_create: Whether this is a create operation (affects logging)

    Returns:
        FormsetValidationResult with validation status and counts
    """
    from django.contrib import messages

    action = "creation" if is_create else "update"
    recipe_info = (
        "" if is_create or recipe_instance is None else f" for '{recipe_instance.title}' (ID: {recipe_instance.pk})"
    )

    errors = []

    # Validate formsets
    if not ingredient_formset.is_valid():
        logger.warning(f"Recipe {action} failed{recipe_info}: ingredient formset validation error")
        errors.append(_("Invalid ingredient data"))

    if not step_formset.is_valid():
        logger.warning(f"Recipe {action} failed{recipe_info}: step formset validation error")
        errors.append(_("Invalid step data"))

    if not image_formset.is_valid():
        logger.warning(f"Recipe {action} failed{recipe_info}: image formset validation error")
        errors.append(_("Invalid image data"))

    if errors:
        return FormsetValidationResult(is_valid=False, errors=errors)

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
        messages.error(request, _("Please add at least one ingredient to the recipe."))
        return FormsetValidationResult(is_valid=False, errors=[_("No ingredients provided")])

    if step_count == 0:
        logger.warning(f"Recipe {action} failed{recipe_info}: no steps provided")
        messages.error(request, _("Please add at least one instruction step to the recipe."))
        return FormsetValidationResult(is_valid=False, errors=[_("No steps provided")])

    return FormsetValidationResult(
        is_valid=True,
        ingredient_count=ingredient_count,
        step_count=step_count,
    )
