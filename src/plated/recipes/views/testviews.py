"""Views for the test view server."""

from __future__ import annotations

from typing import Any

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.generic import TemplateView

from ..models import AIJob, MealPlan, MealPlanEntry, Recipe, RecipeCollection


class TestViewIndexView(TemplateView):
    """Main index page for the test view server."""

    template_name = "testviews/index.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add test view categories to context."""
        context = super().get_context_data(**kwargs)

        # Define all available test views
        context["test_categories"] = [
            {
                "name": "Recipe Views",
                "views": [
                    {"name": "Recipe List - Empty", "url": "testviews_recipe_list_empty"},
                    {"name": "Recipe List - 1 Item", "url": "testviews_recipe_list_one"},
                    {"name": "Recipe List - 3 Items", "url": "testviews_recipe_list_three"},
                    {"name": "Recipe List - 30 Items", "url": "testviews_recipe_list_many"},
                    {"name": "Recipe Detail", "url": "testviews_recipe_detail"},
                    {"name": "Recipe Create", "url": "recipe_create"},
                    {"name": "Recipe Edit", "url": "testviews_recipe_edit"},
                    {"name": "Recipe Cooking View", "url": "testviews_recipe_cooking"},
                    {"name": "Recipe Import", "url": "recipe_import"},
                ],
            },
            {
                "name": "Collection Views",
                "views": [
                    {"name": "Collection List - Empty", "url": "testviews_collection_list_empty"},
                    {"name": "Collection List - 1 Item", "url": "testviews_collection_list_one"},
                    {"name": "Collection List - 3 Items", "url": "testviews_collection_list_three"},
                    {"name": "Collection List - Many Items", "url": "testviews_collection_list_many"},
                    {"name": "Collection Detail - Empty", "url": "testviews_collection_detail_empty"},
                    {"name": "Collection Detail - With Recipes", "url": "testviews_collection_detail"},
                    {"name": "Collection Create", "url": "collection_create"},
                ],
            },
            {
                "name": "Meal Plan Views",
                "views": [
                    {"name": "Meal Plan List - Empty", "url": "testviews_meal_plan_list_empty"},
                    {"name": "Meal Plan List - 1 Item", "url": "testviews_meal_plan_list_one"},
                    {"name": "Meal Plan List - 3 Items", "url": "testviews_meal_plan_list_three"},
                    {"name": "Meal Plan List - Many Items", "url": "testviews_meal_plan_list_many"},
                    {"name": "Meal Plan Detail - Empty", "url": "testviews_meal_plan_detail_empty"},
                    {"name": "Meal Plan Detail - With Entries", "url": "testviews_meal_plan_detail"},
                    {"name": "Meal Plan Create", "url": "meal_plan_create"},
                    {"name": "Shopping List", "url": "testviews_shopping_list"},
                ],
            },
            {
                "name": "Management Views",
                "views": [
                    {"name": "Ingredient Names", "url": "manage_ingredient_names"},
                    {"name": "Units", "url": "manage_units"},
                    {"name": "Keywords", "url": "manage_keywords"},
                ],
            },
            {
                "name": "AI & Jobs Views",
                "views": [
                    {"name": "AI Extract Recipe", "url": "ai_extract_recipe"},
                    {"name": "Jobs List - Empty", "url": "testviews_job_list_empty"},
                    {"name": "Jobs List - 1 Item", "url": "testviews_job_list_one"},
                    {"name": "Jobs List - 3 Items", "url": "testviews_job_list_three"},
                    {"name": "Jobs List - Many Items", "url": "testviews_job_list_many"},
                    {"name": "Job Detail - Pending", "url": "testviews_job_detail_pending"},
                    {"name": "Job Detail - Running", "url": "testviews_job_detail_running"},
                    {"name": "Job Detail - Completed", "url": "testviews_job_detail_completed"},
                    {"name": "Job Detail - Failed", "url": "testviews_job_detail_failed"},
                    {"name": "Job Detail - Cancelled", "url": "testviews_job_detail_cancelled"},
                ],
            },
            {
                "name": "Other Views",
                "views": [
                    {"name": "Settings", "url": "settings"},
                    {"name": "About", "url": "about"},
                ],
            },
        ]

        return context


def recipe_list_test_view(request: HttpRequest, count: int) -> HttpResponse:
    """Display recipe list with specific number of items."""
    recipes = Recipe.objects.filter(title__startswith="[TEST]")[:count] if count > 0 else Recipe.objects.none()
    return render(request, "recipes/recipe_list.html", {"recipes": recipes, "page_obj": None})


def recipe_detail_test_view(request: HttpRequest) -> HttpResponse:
    """Display recipe detail view."""
    recipe = Recipe.objects.filter(title__startswith="[TEST]").first()
    if not recipe:
        return render(
            request, "testviews/no_data.html", {"message": "No test recipes found. Run testviews command first."}
        )

    from ..models import RecipeCollection

    all_collections = RecipeCollection.objects.all()
    recipe_collection_ids = set(recipe.collections.values_list("id", flat=True))

    return render(
        request,
        "recipes/recipe_detail.html",
        {"recipe": recipe, "all_collections": all_collections, "recipe_collection_ids": recipe_collection_ids},
    )


def recipe_edit_test_view(request: HttpRequest) -> HttpResponse:
    """Display recipe edit view - redirects to actual edit page."""
    recipe = Recipe.objects.filter(title__startswith="[TEST]").first()
    if not recipe:
        return render(
            request, "testviews/no_data.html", {"message": "No test recipes found. Run testviews command first."}
        )

    from django.http import HttpResponseRedirect
    from django.urls import reverse

    return HttpResponseRedirect(reverse("recipe_update", kwargs={"pk": recipe.pk}))


def recipe_cooking_test_view(request: HttpRequest) -> HttpResponse:
    """Display recipe cooking view."""
    recipe = Recipe.objects.filter(title__startswith="[TEST]").prefetch_related("ingredients", "steps").first()
    if not recipe:
        return render(
            request, "testviews/no_data.html", {"message": "No test recipes found. Run testviews command first."}
        )

    return render(request, "recipes/recipe_cooking.html", {"recipe": recipe})


def collection_list_test_view(request: HttpRequest, count: int) -> HttpResponse:
    """Display collection list with specific number of items."""
    collections = (
        RecipeCollection.objects.filter(name__startswith="[TEST]")[:count]
        if count > 0
        else RecipeCollection.objects.none()
    )
    return render(request, "recipes/collection_list.html", {"collections": collections, "page_obj": None})


def collection_detail_test_view(request: HttpRequest, empty: bool = False) -> HttpResponse:
    """Display collection detail view."""
    from django.db.models import Count

    collection: RecipeCollection | None
    if empty:
        # Find a collection with no recipes or create one
        collection = (
            RecipeCollection.objects.filter(name__startswith="[TEST]")
            .annotate(recipe_count=Count("recipes"))
            .filter(recipe_count=0)
            .first()
        )
        if not collection:
            # Create one temporarily
            collection = RecipeCollection.objects.create(
                name="[TEST] Empty Collection", description="A collection with no recipes for testing"
            )
    else:
        # Find a collection with recipes
        collection = (
            RecipeCollection.objects.filter(name__startswith="[TEST]")
            .annotate(recipe_count=Count("recipes"))
            .filter(recipe_count__gt=0)
            .first()
        )

    if not collection:
        return render(
            request, "testviews/no_data.html", {"message": "No test collections found. Run testviews command first."}
        )

    return render(request, "recipes/collection_detail.html", {"collection": collection})


def meal_plan_list_test_view(request: HttpRequest, count: int) -> HttpResponse:
    """Display meal plan list with specific number of items."""
    meal_plans = MealPlan.objects.filter(name__startswith="[TEST]")[:count] if count > 0 else MealPlan.objects.none()
    return render(request, "recipes/meal_plan_list.html", {"meal_plans": meal_plans, "page_obj": None})


def meal_plan_detail_test_view(request: HttpRequest, empty: bool = False) -> HttpResponse:
    """Display meal plan detail view."""
    from datetime import timedelta

    from django.db.models import Count, Prefetch

    meal_plan: MealPlan | None
    if empty:
        # Find a meal plan with no entries or create one
        meal_plan = (
            MealPlan.objects.filter(name__startswith="[TEST]")
            .annotate(entry_count=Count("entries"))
            .filter(entry_count=0)
            .first()
        )
        if not meal_plan:
            from datetime import date

            meal_plan = MealPlan.objects.create(
                name="[TEST] Empty Meal Plan",
                description="A meal plan with no entries for testing",
                start_date=date.today(),
                end_date=date.today() + timedelta(days=6),
            )
    else:
        # Find a meal plan with entries
        meal_plan = (
            MealPlan.objects.filter(name__startswith="[TEST]")
            .prefetch_related(Prefetch("entries", queryset=MealPlanEntry.objects.select_related("recipe")))
            .annotate(entry_count=Count("entries"))
            .filter(entry_count__gt=0)
            .first()
        )

    if not meal_plan:
        return render(
            request, "testviews/no_data.html", {"message": "No test meal plans found. Run testviews command first."}
        )

    # Generate list of dates in range
    current_date = meal_plan.start_date
    dates = []
    while current_date <= meal_plan.end_date:
        dates.append(current_date)
        current_date += timedelta(days=1)

    return render(
        request,
        "recipes/meal_plan_detail.html",
        {
            "meal_plan": meal_plan,
            "recipes": Recipe.objects.all(),
            "dates": dates,
            "meal_types": ["breakfast", "lunch", "dinner", "snack"],
        },
    )


def shopping_list_test_view(request: HttpRequest) -> HttpResponse:
    """Display shopping list view."""
    meal_plan = MealPlan.objects.filter(name__startswith="[TEST]").exclude(entries__isnull=True).first()

    if not meal_plan:
        return render(
            request, "testviews/no_data.html", {"message": "No test meal plans found. Run testviews command first."}
        )

    # Generate shopping list data (simplified version of actual view logic)
    from collections import defaultdict

    ingredient_totals: dict[tuple[str, str], dict[str, Any]] = defaultdict(
        lambda: {"amounts": [], "notes": set(), "recipes": set()}
    )

    for entry in meal_plan.entries.select_related("recipe").prefetch_related("recipe__ingredients"):
        for ingredient in entry.recipe.ingredients.all():
            key = (ingredient.name.lower(), ingredient.unit.lower() if ingredient.unit else "")
            ingredient_totals[key]["amounts"].append(ingredient.amount)
            if ingredient.note:
                ingredient_totals[key]["notes"].add(ingredient.note)
            ingredient_totals[key]["recipes"].add(entry.recipe.title)

    # Convert to list format
    shopping_items = []
    for (name, unit), data in sorted(ingredient_totals.items()):
        shopping_items.append(
            {
                "name": name.title(),
                "unit": unit,
                "amounts": ", ".join(data["amounts"]),
                "notes": ", ".join(sorted(data["notes"])),
                "recipes": sorted(data["recipes"]),
            }
        )

    return render(
        request,
        "recipes/shopping_list.html",
        {"meal_plan": meal_plan, "shopping_items": shopping_items, "total_items": len(shopping_items)},
    )


def job_list_test_view(request: HttpRequest, count: int) -> HttpResponse:
    """Display job list with specific number of items."""
    jobs = AIJob.objects.filter(input_content__startswith="[TEST]")[:count] if count > 0 else AIJob.objects.none()
    return render(request, "recipes/jobs_list.html", {"jobs": jobs})


def job_detail_test_view(request: HttpRequest, status: str | None = None) -> HttpResponse:
    """Display job detail view for a specific status."""
    if status:
        # Find a job with the specified status
        job = AIJob.objects.filter(input_content__startswith="[TEST]", status=status).first()
    else:
        # Default to completed status
        job = AIJob.objects.filter(input_content__startswith="[TEST]", status="completed").first()

    if not job:
        message = f"No test jobs found with status '{status}'. Run testviews command first."
        return render(request, "testviews/no_data.html", {"message": message})

    return render(request, "recipes/job_detail.html", {"job": job})
