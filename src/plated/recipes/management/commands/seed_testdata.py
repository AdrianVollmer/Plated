"""Standalone script to seed test data into a database."""

from __future__ import annotations

import os
import sys
from datetime import date, timedelta
from pathlib import Path

# Add the project to the path
src_dir = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(src_dir))

# Configure Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

# Import Django models after setup
from recipes.management.commands.testviews import (  # noqa: E402
    LOREM_DESCRIPTIONS,
    LOREM_INGREDIENTS,
    LOREM_STEPS,
    LOREM_TITLES,
)
from recipes.models import (  # noqa: E402
    AISettings,
    Ingredient,
    MealPlan,
    MealPlanEntry,
    Recipe,
    RecipeCollection,
    Step,
)


def seed_test_data() -> None:
    """Create test data with lorem ipsum content."""
    # Clear existing test data
    Recipe.objects.filter(title__startswith="[TEST]").delete()
    RecipeCollection.objects.filter(name__startswith="[TEST]").delete()
    MealPlan.objects.filter(name__startswith="[TEST]").delete()

    # Create 30 recipes
    recipes = []
    for i in range(30):
        recipe = Recipe.objects.create(
            title=f"[TEST] {LOREM_TITLES[i]}",
            description=LOREM_DESCRIPTIONS[i % len(LOREM_DESCRIPTIONS)],
            servings=(i % 6) + 2,
            keywords=f"test, cuisine{(i % 5) + 1}, course{(i % 3) + 1}",
            prep_time=timedelta(minutes=((i % 4) + 1) * 15),
            wait_time=timedelta(minutes=((i % 6) + 1) * 10),
            notes=f"Lorem ipsum note for recipe {i + 1}. " + LOREM_DESCRIPTIONS[(i + 1) % len(LOREM_DESCRIPTIONS)],
        )

        # Add ingredients
        num_ingredients = (i % 5) + 3
        for j in range(num_ingredients):
            Ingredient.objects.create(
                recipe=recipe,
                amount=f"{(j % 3) + 1}" if j % 2 == 0 else f"{(j % 4) + 1}/{(j % 3) + 2}",
                unit=["cup", "tbsp", "tsp", "oz", "lb", "g", "ml"][j % 7],
                name=LOREM_INGREDIENTS[(i + j) % len(LOREM_INGREDIENTS)],
                note=["chopped", "diced", "minced", "sliced", ""][j % 5],
                order=j + 1,
            )

        # Add steps
        num_steps = (i % 4) + 3
        for j in range(num_steps):
            Step.objects.create(
                recipe=recipe,
                order=j + 1,
                content=LOREM_STEPS[(i + j) % len(LOREM_STEPS)],
            )

        recipes.append(recipe)

    # Create collections
    collection_names = [
        "Quick Weeknight Dinners",
        "Comfort Food Classics",
        "Healthy & Light",
        "International Flavors",
        "Meal Prep Favorites",
    ]
    collection_descs = [
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Fast and easy recipes for busy nights.",
        "Ut enim ad minim veniam. Classic dishes that warm the soul and bring comfort.",
        "Duis aute irure dolor. Nutritious recipes that don't compromise on flavor.",
        "Excepteur sint occaecat. Explore cuisines from around the world.",
        "Sed ut perspiciatis. Make-ahead meals for efficient weekly planning.",
    ]

    for i in range(5):
        collection = RecipeCollection.objects.create(
            name=f"[TEST] {collection_names[i]}",
            description=collection_descs[i],
        )
        start_idx = i * 3
        end_idx = min(start_idx + ((i + 1) * 2), len(recipes))
        collection.recipes.add(*recipes[start_idx:end_idx])

    # Create meal plans
    today = date.today()
    meal_types = ["breakfast", "lunch", "dinner", "snack"]
    meal_plan_names = [
        "This Week's Meals",
        "Weekend Cooking",
        "Next Week Preview",
        "Monthly Plan",
        "Special Occasions",
    ]
    meal_plan_descs = [
        "Lorem ipsum dolor sit amet. Balanced meals for the entire week.",
        "Consectetur adipiscing elit. Weekend cooking and meal prep session.",
        "Sed do eiusmod tempor. Planning ahead for next week's dinners.",
        "Incididunt ut labore. Monthly meal rotation for variety.",
        "Et dolore magna aliqua. Special recipes for celebrations and gatherings.",
    ]

    for i in range(5):
        meal_plan = MealPlan.objects.create(
            name=f"[TEST] {meal_plan_names[i]}",
            description=meal_plan_descs[i],
            start_date=today + timedelta(days=i * 7),
            end_date=today + timedelta(days=i * 7 + 6),
        )

        num_entries = (i + 1) * 3
        for j in range(min(num_entries, len(recipes))):
            MealPlanEntry.objects.create(
                meal_plan=meal_plan,
                recipe=recipes[j],
                date=today + timedelta(days=i * 7 + (j % 7)),
                meal_type=meal_types[j % 4],
                servings=(j % 4) + 1,
                notes=f"Lorem ipsum note {j + 1}" if j % 3 == 0 else "",
            )

    # Create AI jobs with different statuses
    from django.utils import timezone
    from recipes.models import AIJob

    AIJob.objects.filter(input_content__startswith="[TEST]").delete()

    job_statuses = ["pending", "running", "completed", "failed", "cancelled"]
    job_input_types = ["text", "html", "url"]
    job_descriptions = [
        "Extract recipe from blog post about Italian pasta",
        "Parse recipe from cooking website HTML",
        "Get recipe details from recipe URL",
        "Convert text recipe to structured format",
        "Extract ingredients from recipe description",
    ]

    for i in range(10):
        status = job_statuses[i % len(job_statuses)]
        input_type = job_input_types[i % len(job_input_types)]

        job = AIJob.objects.create(
            status=status,
            input_type=input_type,
            input_content=f"[TEST] {job_descriptions[i % len(job_descriptions)]} - Sample input content for testing",
            instructions=f"Test instruction {i + 1}" if i % 2 == 0 else "",
            timeout=60,
            seen=i % 3 == 0,
        )

        # Set timestamps based on status
        if status in ["running", "completed", "failed", "cancelled"]:
            job.started_at = timezone.now()

        if status in ["completed", "failed", "cancelled"]:
            job.completed_at = timezone.now()

        # Add result data for completed jobs
        if status == "completed":
            job.result_data = {
                "title": f"[TEST] Recipe {i + 1}",
                "servings": (i % 6) + 2,
                "ingredients": [
                    {"name": "flour", "amount": "2", "unit": "cups"},
                    {"name": "sugar", "amount": "1", "unit": "cup"},
                ],
                "steps": [{"order": 1, "content": "Mix ingredients"}, {"order": 2, "content": "Bake at 350F"}],
            }

        # Add error message for failed jobs
        if status == "failed":
            job.error_message = f"[TEST] Sample error message for job {i + 1}: API timeout or parsing error"

        job.save()

    # Create AI settings
    if not AISettings.objects.exists():
        AISettings.objects.create(
            api_url="https://api.example.com/v1/chat/completions",
            api_key="test-api-key-placeholder",
            model="gpt-4-test",
            max_tokens=4096,
            temperature=0.7,
        )

    print("Test data created successfully")


if __name__ == "__main__":
    seed_test_data()
