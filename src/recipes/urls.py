from __future__ import annotations

from django.urls import path

from . import views

urlpatterns = [
    path("", views.RecipeListView.as_view(), name="recipe_list"),
    path("recipe/<int:pk>/", views.RecipeDetailView.as_view(), name="recipe_detail"),
    path("recipe/new/", views.RecipeCreateView.as_view(), name="recipe_create"),
    path("recipe/<int:pk>/edit/", views.RecipeUpdateView.as_view(), name="recipe_update"),
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
    path("api/ingredient-names/", views.get_ingredient_names, name="api_ingredient_names"),
    path("api/ingredient-units/", views.get_ingredient_units, name="api_ingredient_units"),
    # Collection management
    path("collections/", views.CollectionListView.as_view(), name="collection_list"),
    path(
        "collections/<int:pk>/",
        views.CollectionDetailView.as_view(),
        name="collection_detail",
    ),
    path(
        "collections/new/",
        views.CollectionCreateView.as_view(),
        name="collection_create",
    ),
    path(
        "collections/<int:pk>/edit/",
        views.CollectionUpdateView.as_view(),
        name="collection_update",
    ),
    path(
        "collections/<int:pk>/delete/",
        views.CollectionDeleteView.as_view(),
        name="collection_delete",
    ),
    # Ingredient and Unit management
    path(
        "manage/ingredient-names/",
        views.manage_ingredient_names,
        name="manage_ingredient_names",
    ),
    path(
        "manage/ingredient-names/rename/",
        views.rename_ingredient_name,
        name="rename_ingredient_name",
    ),
    path("manage/units/", views.manage_units, name="manage_units"),
    path("manage/units/rename/", views.rename_unit, name="rename_unit"),
    # Settings
    path("settings/", views.settings_view, name="settings"),
    # AI Integration
    path("ai/extract/", views.ai_extract_recipe, name="ai_extract_recipe"),
    # PWA
    path("manifest.json", views.manifest_view, name="manifest"),
    path("service-worker.js", views.service_worker_view, name="service_worker"),
]
