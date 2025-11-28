"""Services for recipe operations."""

from .base import RecipeFormatHandler
from .export_service import (
    ExportError,
    export_json_database,
    export_sql_dump,
    export_sqlite_database,
    get_available_export_formats,
    get_export_filename,
)
from .formset_service import (
    FormsetValidationResult,
    create_image_formset,
    create_ingredient_formset,
    create_step_formset,
    validate_recipe_formsets,
)
from .json_format import JSONFormatHandler
from .property_service import (
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
    parse_keywords,
    rename_ingredient_property,
    rename_keyword,
)
from .recipe_service import (
    PDFGenerationError,
    generate_recipe_pdf,
    get_recipes_for_autocomplete,
    sanitize_filename,
    search_recipes,
)
from .registry import format_registry

__all__ = [
    # Format handlers
    "RecipeFormatHandler",
    "JSONFormatHandler",
    "format_registry",
    # Formset services
    "create_ingredient_formset",
    "create_step_formset",
    "create_image_formset",
    "validate_recipe_formsets",
    "FormsetValidationResult",
    # Recipe services
    "generate_recipe_pdf",
    "PDFGenerationError",
    "search_recipes",
    "get_recipes_for_autocomplete",
    "sanitize_filename",
    # Property services
    "get_ingredient_property_with_counts",
    "get_keywords_with_counts",
    "rename_ingredient_property",
    "rename_keyword",
    "get_ingredient_names_for_autocomplete",
    "get_units_for_autocomplete",
    "get_keywords_for_autocomplete",
    "get_usage_count",
    "get_keyword_usage_count",
    "get_recipes_by_ingredient_name",
    "get_recipes_by_unit",
    "get_recipes_by_keyword",
    "parse_keywords",
    # Export services
    "export_sqlite_database",
    "export_json_database",
    "export_sql_dump",
    "get_available_export_formats",
    "get_export_filename",
    "ExportError",
]
