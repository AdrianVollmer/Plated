from __future__ import annotations

import logging

from django.contrib import messages
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _

from ..services import (
    get_ingredient_names_for_autocomplete,
    get_ingredient_property_with_counts,
    get_keyword_usage_count,
    get_keywords_for_autocomplete,
    get_keywords_with_counts,
    get_recipes_by_ingredient_name,
    get_recipes_by_keyword,
    get_recipes_by_unit,
    get_units_for_autocomplete,
    get_usage_count,
    rename_ingredient_property,
    rename_keyword,
)

logger = logging.getLogger(__name__)


# Ingredient and Unit Management Views


def manage_ingredient_names(request: HttpRequest) -> HttpResponse:
    """View and manage distinct ingredient names."""
    query = request.GET.get("q")
    ingredients = get_ingredient_property_with_counts("name", exclude_empty=False, search_query=query)
    return render(request, "recipes/manage_ingredient_names.html", {"ingredients": ingredients, "query": query})


def rename_ingredient_name(request: HttpRequest) -> HttpResponse:
    """Rename an ingredient name across all recipes."""
    if request.method == "POST":
        old_name = request.POST.get("old_name", "").strip()
        new_name = request.POST.get("new_name", "").strip()

        logger.info(f"Ingredient name rename requested: '{old_name}' -> '{new_name}'")

        if not new_name:
            logger.warning("Ingredient name rename failed: missing new value")
            messages.error(request, _("New ingredient name is required."))
            return redirect("manage_ingredient_names")

        try:
            updated = rename_ingredient_property("name", old_name, new_name)
            plural = "" if updated == 1 else "s"
            messages.success(
                request,
                _("Renamed '%(old)s' to '%(new)s' in %(count)s ingredient%(plural)s.")
                % {"old": old_name, "new": new_name, "count": updated, "plural": plural},
            )
            return redirect("manage_ingredient_names")
        except ValueError as e:
            logger.warning(f"Ingredient name rename failed: {e}")
            messages.error(request, str(e))
            return redirect("manage_ingredient_names")
        except Exception as e:
            logger.error(f"Error renaming ingredient name '{old_name}' to '{new_name}': {e}", exc_info=True)
            messages.error(request, _("Error renaming ingredient name: %(error)s") % {"error": e})
            return redirect("manage_ingredient_names")

    # GET request - show rename form
    old_name = request.GET.get("name", "")
    usage_count = get_usage_count("name", old_name) if old_name else 0

    return render(request, "recipes/rename_ingredient_name.html", {"old_name": old_name, "usage_count": usage_count})


def manage_units(request: HttpRequest) -> HttpResponse:
    """View and manage distinct units."""
    query = request.GET.get("q")
    units = get_ingredient_property_with_counts("unit", exclude_empty=True, search_query=query)
    return render(request, "recipes/manage_units.html", {"units": units, "query": query})


def rename_unit(request: HttpRequest) -> HttpResponse:
    """Rename a unit across all recipes."""
    if request.method == "POST":
        old_unit = request.POST.get("old_unit", "").strip()
        new_unit = request.POST.get("new_unit", "").strip()

        logger.info(f"Unit rename requested: '{old_unit}' -> '{new_unit}'")

        # Note: new_unit can be empty to clear the unit
        try:
            updated = rename_ingredient_property("unit", old_unit, new_unit)
            plural = "" if updated == 1 else "s"
            messages.success(
                request,
                _("Renamed '%(old)s' to '%(new)s' in %(count)s ingredient%(plural)s.")
                % {"old": old_unit, "new": new_unit, "count": updated, "plural": plural},
            )
            return redirect("manage_units")
        except ValueError as e:
            logger.warning(f"Unit rename failed: {e}")
            messages.error(request, str(e))
            return redirect("manage_units")
        except Exception as e:
            logger.error(f"Error renaming unit '{old_unit}' to '{new_unit}': {e}", exc_info=True)
            messages.error(request, _("Error renaming unit: %(error)s") % {"error": e})
            return redirect("manage_units")

    # GET request - show rename form
    old_unit = request.GET.get("unit", "")
    usage_count = get_usage_count("unit", old_unit) if old_unit else 0

    return render(request, "recipes/rename_unit.html", {"old_unit": old_unit, "usage_count": usage_count})


def manage_keywords(request: HttpRequest) -> HttpResponse:
    """View and manage distinct keywords."""
    query = request.GET.get("q")
    keywords = get_keywords_with_counts(search_query=query)

    return render(
        request,
        "recipes/manage_keywords.html",
        {"keywords": keywords, "query": query},
    )


def recipes_with_ingredient_name(request: HttpRequest, name: str) -> HttpResponse:
    """Show all recipes that use a specific ingredient name."""
    recipes = get_recipes_by_ingredient_name(name)
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
    recipes = get_recipes_by_unit(unit)
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
    recipes = get_recipes_by_keyword(keyword)

    return render(
        request,
        "recipes/recipes_by_property.html",
        {
            "recipes": recipes,
            "property_type": "Keyword",
            "property_value": keyword,
            "back_url": "manage_keywords",
        },
    )


def delete_ingredient_name(request: HttpRequest) -> HttpResponse:
    """Delete an ingredient name if its usage count is 0."""
    if request.method != "POST":
        return redirect("manage_ingredient_names")

    name = request.POST.get("name", "").strip()
    if not name:
        messages.error(request, _("Ingredient name is required."))
        return redirect("manage_ingredient_names")

    # Check usage count using service
    usage_count = get_usage_count("name", name)
    if usage_count > 0:
        logger.warning(f"Cannot delete ingredient name '{name}': usage count is {usage_count}")
        plural = "s" if usage_count > 1 else ""
        messages.error(
            request,
            _("Cannot delete '%(value)s' because it is used in %(count)s recipe%(plural)s.")
            % {"value": name, "count": usage_count, "plural": plural},
        )
        return redirect("manage_ingredient_names")

    logger.info(f"Ingredient name deleted (no usage): '{name}'")
    messages.success(request, _("Ingredient name '%(value)s' deleted (no usage found).") % {"value": name})
    return redirect("manage_ingredient_names")


def delete_unit(request: HttpRequest) -> HttpResponse:
    """Delete a unit if its usage count is 0."""
    if request.method != "POST":
        return redirect("manage_units")

    unit = request.POST.get("unit", "").strip()
    if not unit:
        messages.error(request, _("Unit is required."))
        return redirect("manage_units")

    # Check usage count using service
    usage_count = get_usage_count("unit", unit)
    if usage_count > 0:
        logger.warning(f"Cannot delete unit '{unit}': usage count is {usage_count}")
        plural = "s" if usage_count > 1 else ""
        messages.error(
            request,
            _("Cannot delete '%(value)s' because it is used in %(count)s recipe%(plural)s.")
            % {"value": unit, "count": usage_count, "plural": plural},
        )
        return redirect("manage_units")

    logger.info(f"Unit deleted (no usage): '{unit}'")
    messages.success(request, _("Unit '%(value)s' deleted (no usage found).") % {"value": unit})
    return redirect("manage_units")


def get_ingredient_names(request: HttpRequest) -> JsonResponse:
    """API endpoint to get distinct ingredient names for autocomplete."""
    names = get_ingredient_names_for_autocomplete()
    return JsonResponse({"names": names})


def get_ingredient_units(request: HttpRequest) -> JsonResponse:
    """API endpoint to get distinct ingredient units for autocomplete."""
    units = get_units_for_autocomplete()
    return JsonResponse({"units": units})


def get_keywords(request: HttpRequest) -> JsonResponse:
    """API endpoint to get distinct keywords for autocomplete."""
    keywords_list = get_keywords_for_autocomplete()
    return JsonResponse({"keywords": keywords_list})


def rename_keyword_view(request: HttpRequest) -> HttpResponse:
    """Rename a keyword across all recipes."""
    if request.method == "POST":
        old_keyword = request.POST.get("old_keyword", "").strip()
        new_keyword = request.POST.get("new_keyword", "").strip()

        logger.info(f"Keyword rename requested: '{old_keyword}' -> '{new_keyword}'")

        # Use service to rename
        try:
            updated_count = rename_keyword(old_keyword, new_keyword)
            plural = "" if updated_count == 1 else "s"
            messages.success(
                request,
                _("Renamed '%(old)s' to '%(new)s' in %(count)s recipe%(plural)s.")
                % {"old": old_keyword, "new": new_keyword, "count": updated_count, "plural": plural},
            )
            return redirect("manage_keywords")
        except ValueError as e:
            logger.warning(f"Keyword rename failed: {e}")
            messages.error(request, str(e))
            return redirect("manage_keywords")
        except Exception as e:
            logger.error(f"Error renaming keyword '{old_keyword}' to '{new_keyword}': {e}", exc_info=True)
            messages.error(request, _("Error renaming keyword: %(error)s") % {"error": e})
            return redirect("manage_keywords")

    # GET request - show rename form
    old_keyword = request.GET.get("keyword", "")
    usage_count = get_keyword_usage_count(old_keyword) if old_keyword else 0

    context = {
        "old_keyword": old_keyword,
        "usage_count": usage_count,
    }
    return render(request, "recipes/rename_keyword.html", context)


def delete_keyword(request: HttpRequest) -> HttpResponse:
    """Delete a keyword if its usage count is 0."""
    if request.method == "POST":
        keyword = request.POST.get("keyword", "").strip()
        if not keyword:
            messages.error(request, _("Keyword is required."))
            return redirect("manage_keywords")

        # Check usage count using service
        usage_count = get_keyword_usage_count(keyword)

        if usage_count > 0:
            logger.warning(f"Cannot delete keyword '{keyword}': usage count is {usage_count}")
            plural = "s" if usage_count > 1 else ""
            messages.error(
                request,
                _("Cannot delete '%(keyword)s' because it is used in %(count)s recipe%(plural)s.")
                % {"keyword": keyword, "count": usage_count, "plural": plural},
            )
            return redirect("manage_keywords")

        logger.info(f"Keyword deleted (no usage): '{keyword}'")
        messages.success(request, _("Keyword '%(keyword)s' deleted (no usage found).") % {"keyword": keyword})
        return redirect("manage_keywords")

    return redirect("manage_keywords")
