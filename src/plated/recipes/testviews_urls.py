"""URL configuration for test view server - completely separate from production URLs."""

from __future__ import annotations

from django.urls import path

from .views import testviews

urlpatterns = [
    # Test view server index
    path("", testviews.TestViewIndexView.as_view(), name="testviews_index"),
    # Recipe views
    path("recipes/empty/", testviews.recipe_list_test_view, {"count": 0}, name="testviews_recipe_list_empty"),
    path("recipes/one/", testviews.recipe_list_test_view, {"count": 1}, name="testviews_recipe_list_one"),
    path("recipes/three/", testviews.recipe_list_test_view, {"count": 3}, name="testviews_recipe_list_three"),
    path("recipes/many/", testviews.recipe_list_test_view, {"count": 30}, name="testviews_recipe_list_many"),
    path("recipes/detail/", testviews.recipe_detail_test_view, name="testviews_recipe_detail"),
    path("recipes/edit/", testviews.recipe_edit_test_view, name="testviews_recipe_edit"),
    path("recipes/cooking/", testviews.recipe_cooking_test_view, name="testviews_recipe_cooking"),
    # Collection views
    path(
        "collections/empty/", testviews.collection_list_test_view, {"count": 0}, name="testviews_collection_list_empty"
    ),
    path("collections/one/", testviews.collection_list_test_view, {"count": 1}, name="testviews_collection_list_one"),
    path(
        "collections/three/", testviews.collection_list_test_view, {"count": 3}, name="testviews_collection_list_three"
    ),
    path("collections/many/", testviews.collection_list_test_view, {"count": 5}, name="testviews_collection_list_many"),
    path(
        "collections/detail-empty/",
        testviews.collection_detail_test_view,
        {"empty": True},
        name="testviews_collection_detail_empty",
    ),
    path("collections/detail/", testviews.collection_detail_test_view, name="testviews_collection_detail"),
    # Meal plan views
    path("meal-plans/empty/", testviews.meal_plan_list_test_view, {"count": 0}, name="testviews_meal_plan_list_empty"),
    path("meal-plans/one/", testviews.meal_plan_list_test_view, {"count": 1}, name="testviews_meal_plan_list_one"),
    path("meal-plans/three/", testviews.meal_plan_list_test_view, {"count": 3}, name="testviews_meal_plan_list_three"),
    path("meal-plans/many/", testviews.meal_plan_list_test_view, {"count": 5}, name="testviews_meal_plan_list_many"),
    path(
        "meal-plans/detail-empty/",
        testviews.meal_plan_detail_test_view,
        {"empty": True},
        name="testviews_meal_plan_detail_empty",
    ),
    path("meal-plans/detail/", testviews.meal_plan_detail_test_view, name="testviews_meal_plan_detail"),
    path("meal-plans/shopping-list/", testviews.shopping_list_test_view, name="testviews_shopping_list"),
    # Job views
    path("jobs/empty/", testviews.job_list_test_view, {"count": 0}, name="testviews_job_list_empty"),
    path("jobs/one/", testviews.job_list_test_view, {"count": 1}, name="testviews_job_list_one"),
    path("jobs/three/", testviews.job_list_test_view, {"count": 3}, name="testviews_job_list_three"),
    path("jobs/many/", testviews.job_list_test_view, {"count": 10}, name="testviews_job_list_many"),
    path(
        "jobs/detail/pending/",
        testviews.job_detail_test_view,
        {"status": "pending"},
        name="testviews_job_detail_pending",
    ),
    path(
        "jobs/detail/running/",
        testviews.job_detail_test_view,
        {"status": "running"},
        name="testviews_job_detail_running",
    ),
    path(
        "jobs/detail/completed/",
        testviews.job_detail_test_view,
        {"status": "completed"},
        name="testviews_job_detail_completed",
    ),
    path(
        "jobs/detail/failed/", testviews.job_detail_test_view, {"status": "failed"}, name="testviews_job_detail_failed"
    ),
    path(
        "jobs/detail/cancelled/",
        testviews.job_detail_test_view,
        {"status": "cancelled"},
        name="testviews_job_detail_cancelled",
    ),
]
