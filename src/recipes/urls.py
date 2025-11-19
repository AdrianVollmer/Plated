from __future__ import annotations

from django.urls import path

from . import views

urlpatterns = [
    path("", views.RecipeListView.as_view(), name="recipe_list"),
    path("recipe/<int:pk>/", views.RecipeDetailView.as_view(), name="recipe_detail"),
    path("recipe/new/", views.RecipeCreateView.as_view(), name="recipe_create"),
    path(
        "recipe/<int:pk>/edit/", views.RecipeUpdateView.as_view(), name="recipe_update"
    ),
    path(
        "recipe/<int:pk>/delete/",
        views.RecipeDeleteView.as_view(),
        name="recipe_delete",
    ),
    # Import/Export
    path("recipe/<int:pk>/export/", views.export_recipe, name="recipe_export"),
    path("recipe/import/", views.import_recipe, name="recipe_import"),
    # PDF Generation
    path("recipe/<int:pk>/pdf/", views.download_recipe_pdf, name="recipe_pdf"),
    # API endpoints for autocomplete
    path(
        "api/ingredient-names/", views.get_ingredient_names, name="api_ingredient_names"
    ),
    path(
        "api/ingredient-units/", views.get_ingredient_units, name="api_ingredient_units"
    ),
]
