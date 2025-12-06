"""Management command to run a test view server for UI/UX development."""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from django.core.management.base import BaseCommand
from recipes.models import AISettings, Ingredient, MealPlan, MealPlanEntry, Recipe, RecipeCollection, Step

logger = logging.getLogger(__name__)


# Lorem ipsum data for realistic test content
LOREM_TITLES = [
    "Creamy Tuscan Garlic Chicken",
    "Spicy Korean Beef Bowl",
    "Mediterranean Quinoa Salad",
    "Classic Margherita Pizza",
    "Thai Green Curry",
    "Honey Glazed Salmon",
    "Vegetarian Pad Thai",
    "French Onion Soup",
    "Chicken Tikka Masala",
    "Mushroom Risotto",
    "BBQ Pulled Pork Sandwiches",
    "Greek Lemon Chicken",
    "Beef Stroganoff",
    "Caprese Pasta Salad",
    "Teriyaki Chicken Stir-Fry",
    "Butternut Squash Soup",
    "Shrimp Scampi",
    "Vegetable Lasagna",
    "Miso Ramen",
    "Chocolate Lava Cake",
    "Apple Cinnamon Pancakes",
    "Caesar Salad with Grilled Chicken",
    "Moroccan Chickpea Stew",
    "Lemon Herb Roasted Potatoes",
    "Beef Tacos with Guacamole",
    "Spinach and Feta Stuffed Chicken",
    "Coconut Curry Shrimp",
    "Italian Meatballs",
    "Sweet Potato Black Bean Burgers",
    "Garlic Butter Lobster Tail",
]

LOREM_DESCRIPTIONS = [
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore.",
    "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo.",
    "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla.",
    "Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim.",
    "Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium.",
    "Totam rem aperiam, eaque ipsa quae ab illo inventore veritatis et quasi architecto beatae vitae.",
    "Nemo enim ipsam voluptatem quia voluptas sit aspernatur aut odit aut fugit, sed quia consequuntur.",
    "Neque porro quisquam est, qui dolorem ipsum quia dolor sit amet, consectetur, adipisci velit.",
    "At vero eos et accusamus et iusto odio dignissimos ducimus qui blanditiis praesentium voluptatum.",
    "Et harum quidem rerum facilis est et expedita distinctio. Nam libero tempore, cum soluta nobis.",
]

LOREM_INGREDIENTS = [
    "all-purpose flour",
    "butter",
    "olive oil",
    "garlic",
    "onion",
    "chicken breast",
    "beef",
    "tomatoes",
    "basil",
    "salt",
    "black pepper",
    "sugar",
    "eggs",
    "milk",
    "cheese",
    "bell peppers",
    "carrots",
    "celery",
    "chicken broth",
    "soy sauce",
]

LOREM_STEPS = [
    "Preheat oven to 375°F (190°C) and prepare baking sheet.",
    "In a large bowl, mix together the dry ingredients until well combined.",
    "In another bowl, whisk together wet ingredients until smooth.",
    "Gradually fold the wet ingredients into the dry mixture, stirring gently.",
    "Heat oil in a large skillet over medium-high heat.",
    "Add aromatics and sauté until fragrant, about 2-3 minutes.",
    "Season with salt and pepper to taste, adjusting as needed.",
    "Transfer to prepared pan and spread evenly.",
    "Bake for 25-30 minutes until golden brown and cooked through.",
    "Remove from heat and let rest for 5 minutes before serving.",
    "Garnish with fresh herbs and serve immediately.",
]


class Command(BaseCommand):
    """Run a test view server that displays all views with various data states."""

    help = "Runs a web server displaying all views with test data for UI/UX development"

    def add_arguments(self, parser):  # type: ignore
        parser.add_argument(
            "--port",
            type=int,
            default=8001,
            help="Port to run the test server on (default: 8001)",
        )

    def handle(self, *args: Any, **kwargs: Any) -> None:
        """Set up test data and instructions."""
        port = kwargs["port"]

        self.stdout.write(self.style.WARNING("\n" + "=" * 70))
        self.stdout.write(self.style.WARNING("  TEST VIEW SERVER"))
        self.stdout.write(self.style.WARNING("=" * 70))
        self.stdout.write("\nThis command will create test data in your database.")
        self.stdout.write("Make sure you're using a development database!\n")

        response = input("Continue? (yes/no): ")
        if response.lower() not in ["yes", "y"]:
            self.stdout.write(self.style.ERROR("Aborted."))
            return

        # Create test data
        self.stdout.write("\nCreating test data...")
        self._create_test_data()

        self.stdout.write(self.style.SUCCESS("\n✓ Test data created successfully!\n"))
        self.stdout.write(self.style.WARNING("=" * 70))
        self.stdout.write("To view the test views:")
        self.stdout.write(f"1. Run: uv run python src/plated/manage.py runserver {port}")
        self.stdout.write(f"2. Visit: http://127.0.0.1:{port}/testviews/")
        self.stdout.write(self.style.WARNING("=" * 70))
        self.stdout.write("\nThe test view index will show all available test scenarios.")
        self.stdout.write("Use the sidebar to navigate between different views and data states.\n")

    def _create_test_data(self) -> None:
        """Create test data with lorem ipsum content."""
        # Clear existing test data
        Recipe.objects.filter(title__startswith="[TEST]").delete()
        RecipeCollection.objects.filter(name__startswith="[TEST]").delete()
        MealPlan.objects.filter(name__startswith="[TEST]").delete()

        # Create 30 recipes with lorem ipsum data
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

            # Add ingredients (3-7 per recipe)
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

            # Add steps (3-6 per recipe)
            num_steps = (i % 4) + 3
            for j in range(num_steps):
                Step.objects.create(
                    recipe=recipe,
                    order=j + 1,
                    content=LOREM_STEPS[(i + j) % len(LOREM_STEPS)],
                )

            recipes.append(recipe)

        # Create collections with lorem ipsum
        collections = []
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
            # Add varying numbers of recipes
            start_idx = i * 3
            end_idx = min(start_idx + ((i + 1) * 2), len(recipes))
            collection.recipes.add(*recipes[start_idx:end_idx])
            collections.append(collection)

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

            # Add entries (varying amounts)
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

        # Create AI settings if not exists
        if not AISettings.objects.exists():
            AISettings.objects.create(
                api_url="https://api.example.com/v1/chat/completions",
                api_key="test-api-key-placeholder",
                model="gpt-4-test",
                max_tokens=4096,
                temperature=0.7,
            )

        self.stdout.write(f"  Created {len(recipes)} recipes with lorem ipsum content")
        self.stdout.write(f"  Created {len(collections)} collections")
        self.stdout.write("  Created 5 meal plans with entries")
