from __future__ import annotations

from django.urls import path

from . import views

urlpatterns = [
    path("", views.recipes.RecipeListView.as_view(), name="recipe_list"),
    path("recipe/<int:pk>/", views.recipes.RecipeDetailView.as_view(), name="recipe_detail"),
    path("recipe/new/", views.recipes.RecipeCreateView.as_view(), name="recipe_create"),
    path("recipe/<int:pk>/edit/", views.recipes.RecipeUpdateView.as_view(), name="recipe_update"),
    path(
        "recipe/<int:pk>/delete/",
        views.recipes.RecipeDeleteView.as_view(),
        name="recipe_delete",
    ),
    # Import/Export
    path("recipe/<int:pk>/export/", views.recipes.export_recipe, name="recipe_export"),
    path("recipe/import/", views.recipes.import_recipe, name="recipe_import"),
    # PDF Generation
    path("recipe/<int:pk>/pdf/", views.recipes.download_recipe_pdf, name="recipe_pdf"),
    # API endpoints for autocomplete
    path("api/ingredient-names/", views.properties.get_ingredient_names, name="api_ingredient_names"),
    path("api/ingredient-units/", views.properties.get_ingredient_units, name="api_ingredient_units"),
    path("api/keywords/", views.properties.get_keywords, name="api_keywords"),
    path("api/recipes/", views.recipes.get_recipes_api, name="api_recipes"),
    # Collection management
    path("collections/", views.collections.CollectionListView.as_view(), name="collection_list"),
    path(
        "collections/<int:pk>/",
        views.collections.CollectionDetailView.as_view(),
        name="collection_detail",
    ),
    path(
        "collections/new/",
        views.collections.CollectionCreateView.as_view(),
        name="collection_create",
    ),
    path(
        "collections/<int:pk>/edit/",
        views.collections.CollectionUpdateView.as_view(),
        name="collection_update",
    ),
    path(
        "collections/<int:pk>/delete/",
        views.collections.CollectionDeleteView.as_view(),
        name="collection_delete",
    ),
    # Meal plan management
    path("meal-plans/", views.meal_plans.MealPlanListView.as_view(), name="meal_plan_list"),
    path("meal-plans/<int:pk>/", views.meal_plans.MealPlanDetailView.as_view(), name="meal_plan_detail"),
    path("meal-plans/new/", views.meal_plans.MealPlanCreateView.as_view(), name="meal_plan_create"),
    path("meal-plans/<int:pk>/edit/", views.meal_plans.MealPlanUpdateView.as_view(), name="meal_plan_update"),
    path(
        "meal-plans/<int:pk>/delete/",
        views.meal_plans.MealPlanDeleteView.as_view(),
        name="meal_plan_delete",
    ),
    path("meal-plans/<int:pk>/add-entry/", views.meal_plans.add_meal_entry, name="add_meal_entry"),
    path(
        "meal-plans/<int:pk>/remove-entry/<int:entry_id>/",
        views.meal_plans.remove_meal_entry,
        name="remove_meal_entry",
    ),
    path("meal-plans/<int:pk>/shopping-list/", views.meal_plans.shopping_list, name="shopping_list"),
    # Ingredient and Unit management
    path(
        "manage/ingredient-names/",
        views.properties.manage_ingredient_names,
        name="manage_ingredient_names",
    ),
    path(
        "manage/ingredient-names/rename/",
        views.properties.rename_ingredient_name,
        name="rename_ingredient_name",
    ),
    path(
        "manage/ingredient-names/delete/",
        views.properties.delete_ingredient_name,
        name="delete_ingredient_name",
    ),
    path(
        "manage/ingredient-names/<str:name>/recipes/",
        views.properties.recipes_with_ingredient_name,
        name="recipes_with_ingredient_name",
    ),
    path("manage/units/", views.properties.manage_units, name="manage_units"),
    path("manage/units/rename/", views.properties.rename_unit, name="rename_unit"),
    path("manage/units/delete/", views.properties.delete_unit, name="delete_unit"),
    path("manage/units/<str:unit>/recipes/", views.properties.recipes_with_unit, name="recipes_with_unit"),
    path("manage/keywords/", views.properties.manage_keywords, name="manage_keywords"),
    path("manage/keywords/rename/", views.properties.rename_keyword, name="rename_keyword"),
    path("manage/keywords/delete/", views.properties.delete_keyword, name="delete_keyword"),
    path(
        "manage/keywords/<str:keyword>/recipes/",
        views.properties.recipes_with_keyword,
        name="recipes_with_keyword",
    ),
    # Settings
    path("settings/", views.settings.settings_view, name="settings"),
    # AI Integration
    path("ai/extract/", views.ai.ai_extract_recipe, name="ai_extract_recipe"),
    # Jobs
    path("jobs/", views.jobs.jobs_list, name="jobs_list"),
    path("jobs/<int:pk>/", views.jobs.job_detail, name="job_detail"),
    path("jobs/<int:pk>/cancel/", views.jobs.job_cancel, name="job_cancel"),
    path("jobs/<int:pk>/retry/", views.jobs.job_retry, name="job_retry"),
    path("jobs/<int:pk>/delete/", views.jobs.job_delete, name="job_delete"),
    path("jobs/<int:pk>/mark-seen/", views.jobs.job_mark_seen, name="job_mark_seen"),
    path("jobs/<int:pk>/use-result/", views.jobs.job_use_result, name="job_use_result"),
    path("api/jobs/<int:pk>/status/", views.jobs.api_job_status, name="api_job_status"),
    # PWA
    path("manifest.json", views.pwa.manifest_view, name="manifest"),
    path("service-worker.js", views.pwa.service_worker_view, name="service_worker"),
    # About
    path("about/", views.pwa.about_view, name="about"),
]
