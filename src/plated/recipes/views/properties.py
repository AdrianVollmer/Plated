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
    # Get all distinct values with usage counts from service
    query = request.GET.get("q")
    exclude_empty = field_name == "unit"
    items = get_ingredient_property_with_counts(field_name, exclude_empty=exclude_empty, search_query=query)

    return render(request, template_name, {context_var_name: items, "query": query})


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

        # Validate inputs (some validation is also done in service)
        if requires_new_value and not new_value:
            logger.warning(f"{display_name} rename failed: missing new value")
            messages.error(request, _("New %(name)s is required.") % {"name": display_name.lower()})
            return redirect(list_url_name)

        # Use service to rename
        try:
            updated = rename_ingredient_property(field_name, old_value, new_value)
            plural = "" if updated == 1 else "s"
            messages.success(
                request,
                _("Renamed '%(old)s' to '%(new)s' in %(count)s ingredient%(plural)s.")
                % {"old": old_value, "new": new_value, "count": updated, "plural": plural},
            )
            return redirect(list_url_name)
        except ValueError as e:
            logger.warning(f"{display_name} rename failed: {e}")
            messages.error(request, str(e))
            return redirect(list_url_name)
        except Exception as e:
            logger.error(f"Error renaming {display_name.lower()} '{old_value}' to '{new_value}': {e}", exc_info=True)
            messages.error(
                request, _("Error renaming %(name)s: %(error)s") % {"name": display_name.lower(), "error": e}
            )
            return redirect(list_url_name)

    # GET request - show rename form
    old_value = request.GET.get(field_name, "")
    usage_count = get_usage_count(field_name, old_value) if old_value else 0

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
        messages.error(request, _("%(name)s is required.") % {"name": display_name})
        return redirect(list_url_name)

    # Check usage count using service
    usage_count = get_usage_count(field_name, value)
    if usage_count > 0:
        logger.warning(f"Cannot delete {display_name.lower()} '{value}': usage count is {usage_count}")
        plural = "s" if usage_count > 1 else ""
        messages.error(
            request,
            _("Cannot delete '%(value)s' because it is used in %(count)s recipe%(plural)s.")
            % {"value": value, "count": usage_count, "plural": plural},
        )
        return redirect(list_url_name)

    logger.info(f"{display_name} deleted (no usage): '{value}'")
    messages.success(
        request, _("%(name)s '%(value)s' deleted (no usage found).") % {"name": display_name, "value": value}
    )
    return redirect(list_url_name)


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
