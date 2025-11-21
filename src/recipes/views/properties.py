from __future__ import annotations

import logging
from typing import Any

from django.contrib import messages
from django.db import models as django_models
from django.db import transaction
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render

from ..models import Ingredient, Recipe

logger = logging.getLogger(__name__)


# Ingredient and Unit Management Views


def _manage_ingredient_property(
    request: HttpRequest,
    field_name: str,
    display_name: str,
    template_name: str,
    list_url_name: str,
    context_var_name: str,
) -> HttpResponse:
    """
    Generic view for managing ingredient properties (name or unit).

    Args:
        request: HTTP request
        field_name: Field name on Ingredient model ('name' or 'unit')
        display_name: Human-readable name for display
        template_name: Template to render
        list_url_name: URL name for redirect
        context_var_name: Name for the context variable in template
    """
    # Get all distinct values with usage counts
    queryset = (
        Ingredient.objects.values(field_name).annotate(usage_count=django_models.Count("id")).order_by(field_name)
    )

    # For units, exclude empty values
    if field_name == "unit":
        queryset = queryset.exclude(**{field_name: ""})

    # Handle search query
    query = request.GET.get("q")
    if query:
        queryset = queryset.filter(**{f"{field_name}__icontains": query})

    return render(request, template_name, {context_var_name: queryset, "query": query})


def _rename_ingredient_property(
    request: HttpRequest,
    field_name: str,
    display_name: str,
    old_param: str,
    new_param: str,
    template_name: str,
    list_url_name: str,
    requires_new_value: bool = True,
) -> HttpResponse:
    """
    Generic view for renaming ingredient properties (name or unit).

    Args:
        request: HTTP request
        field_name: Field name on Ingredient model
        display_name: Human-readable name for messages
        old_param: POST parameter name for old value
        new_param: POST parameter name for new value
        template_name: Template to render for GET requests
        list_url_name: URL name for redirect
        requires_new_value: Whether new value is required (False allows clearing)
    """
    if request.method == "POST":
        old_value = request.POST.get(old_param, "").strip()
        new_value = request.POST.get(new_param, "").strip()

        logger.info(f"{display_name} rename requested: '{old_value}' -> '{new_value}'")

        # Validate inputs
        if not old_value:
            logger.warning(f"{display_name} rename failed: missing old value")
            messages.error(request, f"Old {display_name.lower()} is required.")
            return redirect(list_url_name)

        if requires_new_value and not new_value:
            logger.warning(f"{display_name} rename failed: missing new value")
            messages.error(request, f"New {display_name.lower()} is required.")
            return redirect(list_url_name)

        if old_value == new_value:
            logger.warning(f"{display_name} rename skipped: old and new values are identical ('{old_value}')")
            messages.warning(request, f"Old and new {display_name.lower()}s are the same.")
            return redirect(list_url_name)

        # Check if old value exists
        count = Ingredient.objects.filter(**{field_name: old_value}).count()
        if count == 0:
            logger.warning(
                f"{display_name} rename failed: no ingredients found with {display_name.lower()} '{old_value}'"
            )
            messages.error(request, f"No ingredients found with {display_name.lower()} '{old_value}'.")
            return redirect(list_url_name)

        # Update all ingredients with the old value
        try:
            with transaction.atomic():
                updated = Ingredient.objects.filter(**{field_name: old_value}).update(**{field_name: new_value})

            logger.info(f"{display_name} renamed: '{old_value}' -> '{new_value}' ({updated} occurrences)")
            plural = "" if updated == 1 else "s"
            messages.success(
                request,
                f"Renamed '{old_value}' to '{new_value}' in {updated} ingredient{plural}.",
            )
            return redirect(list_url_name)
        except Exception as e:
            logger.error(f"Error renaming {display_name.lower()} '{old_value}' to '{new_value}': {e}", exc_info=True)
            messages.error(request, f"Error renaming {display_name.lower()}: {e}")
            return redirect(list_url_name)

    # GET request - show rename form
    old_value = request.GET.get(field_name, "")
    usage_count = Ingredient.objects.filter(**{field_name: old_value}).count() if old_value else 0

    context = {
        old_param: old_value,
        "usage_count": usage_count,
    }
    return render(request, template_name, context)


def manage_ingredient_names(request: HttpRequest) -> HttpResponse:
    """View and manage distinct ingredient names."""
    return _manage_ingredient_property(
        request,
        field_name="name",
        display_name="Ingredient Name",
        template_name="recipes/manage_ingredient_names.html",
        list_url_name="manage_ingredient_names",
        context_var_name="ingredients",
    )


def rename_ingredient_name(request: HttpRequest) -> HttpResponse:
    """Rename an ingredient name across all recipes."""
    return _rename_ingredient_property(
        request,
        field_name="name",
        display_name="Ingredient Name",
        old_param="old_name",
        new_param="new_name",
        template_name="recipes/rename_ingredient_name.html",
        list_url_name="manage_ingredient_names",
    )


def manage_units(request: HttpRequest) -> HttpResponse:
    """View and manage distinct units."""
    return _manage_ingredient_property(
        request,
        field_name="unit",
        display_name="Unit",
        template_name="recipes/manage_units.html",
        list_url_name="manage_units",
        context_var_name="units",
    )


def rename_unit(request: HttpRequest) -> HttpResponse:
    """Rename a unit across all recipes."""
    return _rename_ingredient_property(
        request,
        field_name="unit",
        display_name="Unit",
        old_param="old_unit",
        new_param="new_unit",
        template_name="recipes/rename_unit.html",
        list_url_name="manage_units",
        requires_new_value=False,  # Allow clearing unit
    )


def manage_keywords(request: HttpRequest) -> HttpResponse:
    """View and manage distinct keywords."""
    # Count keyword usage across all recipes
    keyword_counts: dict[str, int] = {}
    for keywords_str in _get_all_recipe_keywords():
        for keyword in _parse_keywords(keywords_str):
            keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1

    # Convert to list of dicts and sort
    keywords: list[dict[str, Any]] = [{"keyword": k, "usage_count": v} for k, v in keyword_counts.items()]
    keywords.sort(key=lambda x: str(x["keyword"]).lower())

    # Handle search query
    query = request.GET.get("q")
    if query:
        keywords = [k for k in keywords if query.lower() in str(k["keyword"]).lower()]

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


def _delete_ingredient_property(
    request: HttpRequest,
    field_name: str,
    display_name: str,
    param_name: str,
    list_url_name: str,
) -> HttpResponse:
    """
    Generic view for deleting unused ingredient properties.

    Args:
        request: HTTP request
        field_name: Field name on Ingredient model
        display_name: Human-readable name for messages
        param_name: POST parameter name
        list_url_name: URL name for redirect
    """
    if request.method != "POST":
        return redirect(list_url_name)

    value = request.POST.get(param_name, "").strip()
    if not value:
        messages.error(request, f"{display_name} is required.")
        return redirect(list_url_name)

    # Check usage count
    usage_count = Ingredient.objects.filter(**{field_name: value}).count()
    if usage_count > 0:
        logger.warning(f"Cannot delete {display_name.lower()} '{value}': usage count is {usage_count}")
        plural = "s" if usage_count > 1 else ""
        messages.error(
            request,
            f"Cannot delete '{value}' because it is used in {usage_count} recipe{plural}.",
        )
        return redirect(list_url_name)

    logger.info(f"{display_name} deleted (no usage): '{value}'")
    messages.success(request, f"{display_name} '{value}' deleted (no usage found).")
    return redirect(list_url_name)


def recipes_with_keyword(request: HttpRequest, keyword: str) -> HttpResponse:
    """Show all recipes that use a specific keyword."""
    recipes = Recipe.objects.filter(keywords__icontains=keyword).distinct()
    # Further filter to ensure exact keyword match (not just substring)
    filtered_recipes = [recipe for recipe in recipes if keyword in _parse_keywords(recipe.keywords)]

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
    return _delete_ingredient_property(
        request,
        field_name="name",
        display_name="Ingredient name",
        param_name="name",
        list_url_name="manage_ingredient_names",
    )


def delete_unit(request: HttpRequest) -> HttpResponse:
    """Delete a unit if its usage count is 0."""
    return _delete_ingredient_property(
        request,
        field_name="unit",
        display_name="Unit",
        param_name="unit",
        list_url_name="manage_units",
    )


def get_ingredient_names(request: HttpRequest) -> JsonResponse:
    """API endpoint to get distinct ingredient names for autocomplete."""
    names = Ingredient.objects.values_list("name", flat=True).distinct().order_by("name")
    return JsonResponse({"names": list(names)})


def get_ingredient_units(request: HttpRequest) -> JsonResponse:
    """API endpoint to get distinct ingredient units for autocomplete."""
    units = Ingredient.objects.exclude(unit="").values_list("unit", flat=True).distinct().order_by("unit")
    return JsonResponse({"units": list(units)})


def _parse_keywords(keywords_str: str) -> list[str]:
    """
    Parse a comma-separated keyword string into a list of cleaned keywords.

    Args:
        keywords_str: Comma-separated string of keywords

    Returns:
        List of cleaned, non-empty keywords
    """
    return [kw.strip() for kw in keywords_str.split(",") if kw.strip()]


def _get_all_recipe_keywords() -> list[str]:
    """
    Get all distinct keywords from recipes as a flat list.

    Returns:
        List of all keyword strings (comma-separated) from recipes
    """
    return list(Recipe.objects.exclude(keywords="").values_list("keywords", flat=True))


def get_keywords(request: HttpRequest) -> JsonResponse:
    """API endpoint to get distinct keywords for autocomplete."""
    # Get all keywords and flatten into a unique set
    keywords_set = set()
    for keywords_str in _get_all_recipe_keywords():
        keywords_set.update(_parse_keywords(keywords_str))

    # Convert to sorted list
    keywords_list = sorted(keywords_set, key=str.lower)

    return JsonResponse({"keywords": keywords_list})


def delete_keyword(request: HttpRequest) -> HttpResponse:
    """Delete a keyword if its usage count is 0."""
    if request.method == "POST":
        keyword = request.POST.get("keyword", "").strip()
        if not keyword:
            messages.error(request, "Keyword is required.")
            return redirect("manage_keywords")

        # Check usage count - count how many recipes have this keyword
        usage_count = sum(1 for keywords_str in _get_all_recipe_keywords() if keyword in _parse_keywords(keywords_str))

        if usage_count > 0:
            logger.warning(f"Cannot delete keyword '{keyword}': usage count is {usage_count}")
            plural = "s" if usage_count > 1 else ""
            messages.error(
                request,
                f"Cannot delete '{keyword}' because it is used in {usage_count} recipe{plural}.",
            )
            return redirect("manage_keywords")

        logger.info(f"Keyword deleted (no usage): '{keyword}'")
        messages.success(request, f"Keyword '{keyword}' deleted (no usage found).")
        return redirect("manage_keywords")

    return redirect("manage_keywords")
