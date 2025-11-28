"""Management command to seed the database with sample recipes."""

from __future__ import annotations

import logging
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from recipes.models import Ingredient, MealPlan, MealPlanEntry, Recipe, RecipeCollection, Step

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Seed the database with sample recipes."""

    help = "Seeds the database with sample recipes for testing"

    def add_arguments(self, parser):  # type: ignore
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing recipes before seeding",
        )

    def handle(self, *args, **kwargs):  # type: ignore
        logger.info("Database seeding command started")

        if kwargs["clear"]:
            self.stdout.write("Clearing existing data...")
            logger.info("Clearing all existing data from database")
            recipe_count = Recipe.objects.count()
            collection_count = RecipeCollection.objects.count()
            meal_plan_count = MealPlan.objects.count()
            Recipe.objects.all().delete()
            RecipeCollection.objects.all().delete()
            MealPlan.objects.all().delete()
            logger.info(
                f"Deleted {recipe_count} recipes, {collection_count} collections, "
                f"and {meal_plan_count} meal plans from database"
            )
            self.stdout.write(self.style.SUCCESS("Cleared all recipes, collections, and meal plans"))

        self.stdout.write("Seeding database with sample recipes...")
        logger.info("Starting to seed database with sample recipes")

        # Recipe 1: Classic Chocolate Chip Cookies
        recipe1 = Recipe.objects.create(
            title="Classic Chocolate Chip Cookies",
            description="Soft and chewy chocolate chip cookies with crispy edges. A timeless favorite that's perfect for any occasion.",
            servings=24,
            prep_time=timedelta(minutes=15),
            wait_time=timedelta(minutes=12),
            keywords="dessert, cookies, chocolate, baking, comfort food",
            url="https://example.com/chocolate-chip-cookies",
            notes="For extra flavor, let the dough chill in the refrigerator for at least 2 hours before baking. This helps develop deeper flavors and prevents excessive spreading.",
        )

        # Ingredients
        ingredients1 = [
            ("2 1/4", "cups", "all-purpose flour", ""),
            ("1", "tsp", "baking soda", ""),
            ("1", "tsp", "salt", ""),
            ("1", "cup", "butter", "softened"),
            ("3/4", "cup", "granulated sugar", ""),
            ("3/4", "cup", "brown sugar", "packed"),
            ("2", "", "large eggs", ""),
            ("2", "tsp", "vanilla extract", ""),
            ("2", "cups", "chocolate chips", "semi-sweet"),
        ]
        for i, (amount, unit, name, note) in enumerate(ingredients1, 1):
            Ingredient.objects.create(recipe=recipe1, amount=amount, unit=unit, name=name, note=note, order=i)

        # Steps
        steps1 = [
            "Preheat oven to 375°F (190°C).",
            "In a medium bowl, whisk together flour, baking soda, and salt. Set aside.",
            "In a large bowl, cream together softened butter, granulated sugar, and brown sugar until light and fluffy (about 3 minutes).",
            "Beat in eggs one at a time, then add vanilla extract.",
            "Gradually stir in the flour mixture until just combined. Do not overmix.",
            "Fold in chocolate chips until evenly distributed.",
            "Drop rounded tablespoons of dough onto ungreased baking sheets, spacing them 2 inches apart.",
            "Bake for 10-12 minutes, or until edges are golden brown but centers still look slightly underdone.",
            "Cool on baking sheet for 5 minutes, then transfer to a wire rack to cool completely.",
        ]
        for i, content in enumerate(steps1, 1):
            Step.objects.create(recipe=recipe1, order=i, content=content)

        # Recipe 2: Creamy Tomato Basil Soup
        recipe2 = Recipe.objects.create(
            title="Creamy Tomato Basil Soup",
            description="A rich and velvety tomato soup with fresh basil. Perfect for a cozy lunch paired with grilled cheese.",
            servings=6,
            prep_time=timedelta(minutes=10),
            wait_time=timedelta(minutes=30),
            keywords="soup, tomato, basil, vegetarian, comfort food, lunch",
            special_equipment="Immersion blender or regular blender",
            notes="For a vegan version, substitute heavy cream with coconut cream or cashew cream.",
        )

        ingredients2 = [
            ("2", "tbsp", "olive oil", ""),
            ("1", "", "onion", "diced"),
            ("4", "cloves", "garlic", "minced"),
            ("2", "cans", "crushed tomatoes", "28 oz each"),
            ("2", "cups", "vegetable broth", ""),
            ("1", "tbsp", "sugar", "to balance acidity"),
            ("1", "cup", "heavy cream", ""),
            ("1/2", "cup", "fresh basil", "chopped"),
            ("", "", "salt", "to taste"),
            ("", "", "black pepper", "to taste"),
        ]
        for i, (amount, unit, name, note) in enumerate(ingredients2, 1):
            Ingredient.objects.create(recipe=recipe2, amount=amount, unit=unit, name=name, note=note, order=i)

        steps2 = [
            "Heat olive oil in a large pot over medium heat.",
            "Add diced onion and sauté until softened and translucent, about 5 minutes.",
            "Add minced garlic and cook for 1 minute until fragrant.",
            "Pour in crushed tomatoes and vegetable broth. Stir to combine.",
            "Add sugar and bring to a simmer. Cook for 20 minutes, stirring occasionally.",
            "Remove from heat and use an immersion blender to puree until smooth. Alternatively, carefully transfer to a blender in batches.",
            "Return to low heat and stir in heavy cream and fresh basil.",
            "Season with salt and pepper to taste.",
            "Simmer for 5 more minutes. Serve hot with crusty bread or grilled cheese.",
        ]
        for i, content in enumerate(steps2, 1):
            Step.objects.create(recipe=recipe2, order=i, content=content)

        # Recipe 3: Spicy Thai Basil Chicken
        recipe3 = Recipe.objects.create(
            title="Spicy Thai Basil Chicken (Pad Krapow Gai)",
            description="A quick and fiery Thai stir-fry with ground chicken, holy basil, and chilies. Traditionally served over rice with a fried egg on top.",
            servings=4,
            prep_time=timedelta(minutes=10),
            wait_time=timedelta(minutes=10),
            keywords="thai, chicken, spicy, stir-fry, asian, quick, dinner",
            url="https://example.com/thai-basil-chicken",
        )

        ingredients3 = [
            ("2", "tbsp", "vegetable oil", ""),
            ("4", "cloves", "garlic", "minced"),
            ("2-4", "", "Thai chilies", "finely chopped, adjust to taste"),
            ("1", "lb", "ground chicken", ""),
            ("1", "tbsp", "soy sauce", ""),
            ("1", "tbsp", "fish sauce", ""),
            ("1", "tbsp", "oyster sauce", ""),
            ("1", "tsp", "sugar", ""),
            ("1/4", "cup", "water", "or chicken broth"),
            ("1", "cup", "Thai basil leaves", "holy basil if available"),
            ("", "", "cooked rice", "for serving"),
            ("4", "", "fried eggs", "optional, for serving"),
        ]
        for i, (amount, unit, name, note) in enumerate(ingredients3, 1):
            Ingredient.objects.create(recipe=recipe3, amount=amount, unit=unit, name=name, note=note, order=i)

        steps3 = [
            "Heat oil in a large wok or skillet over high heat.",
            "Add garlic and chilies, stir-fry for 30 seconds until fragrant.",
            "Add ground chicken and break it up with a spatula. Cook until no longer pink.",
            "Add soy sauce, fish sauce, oyster sauce, and sugar. Stir well to combine.",
            "Add water or broth and cook for 2-3 minutes until sauce thickens slightly.",
            "Turn off heat and stir in Thai basil leaves. Let them wilt in the residual heat.",
            "Serve immediately over steamed rice, topped with a fried egg if desired.",
        ]
        for i, content in enumerate(steps3, 1):
            Step.objects.create(recipe=recipe3, order=i, content=content)

        # Recipe 4: Overnight Oats (Simple & Healthy)
        recipe4 = Recipe.objects.create(
            title="Perfect Overnight Oats",
            description="Make-ahead breakfast oats that are creamy, nutritious, and endlessly customizable. Prep the night before for an easy grab-and-go breakfast.",
            servings=1,
            prep_time=timedelta(minutes=5),
            wait_time=timedelta(hours=8),
            keywords="breakfast, healthy, meal prep, oats, vegetarian, quick",
            notes="This is a base recipe - customize with your favorite toppings like nuts, seeds, nut butter, or fresh fruit!",
        )

        ingredients4 = [
            ("1/2", "cup", "rolled oats", "old-fashioned, not instant"),
            ("1/2", "cup", "milk", "any kind"),
            ("1/4", "cup", "Greek yogurt", ""),
            ("1", "tbsp", "chia seeds", "optional"),
            ("1", "tbsp", "maple syrup", "or honey"),
            ("1/4", "tsp", "vanilla extract", ""),
            ("", "", "pinch of salt", ""),
            ("", "", "toppings", "berries, banana, nuts, etc."),
        ]
        for i, (amount, unit, name, note) in enumerate(ingredients4, 1):
            Ingredient.objects.create(recipe=recipe4, amount=amount, unit=unit, name=name, note=note, order=i)

        steps4 = [
            "In a jar or container, combine rolled oats, milk, Greek yogurt, chia seeds, maple syrup, vanilla, and salt.",
            "Stir well to ensure everything is evenly mixed.",
            "Cover and refrigerate for at least 8 hours or overnight.",
            "In the morning, give it a good stir. Add a splash of milk if too thick.",
            "Top with your favorite toppings: fresh berries, sliced banana, nuts, nut butter, granola, etc.",
            "Enjoy cold or heat in the microwave for 1-2 minutes if you prefer it warm.",
        ]
        for i, content in enumerate(steps4, 1):
            Step.objects.create(recipe=recipe4, order=i, content=content)

        # Recipe 5: Homemade Pizza Dough
        recipe5 = Recipe.objects.create(
            title="Easy Homemade Pizza Dough",
            description="Simple, foolproof pizza dough that yields a crispy crust with a chewy interior. Makes enough for two 12-inch pizzas.",
            servings=8,
            prep_time=timedelta(minutes=15),
            wait_time=timedelta(hours=1, minutes=30),
            keywords="pizza, dough, italian, bread, homemade, dinner",
            special_equipment="Stand mixer with dough hook (optional but helpful)",
            notes="The dough can be refrigerated for up to 3 days or frozen for up to 3 months. Bring to room temperature before rolling out.",
        )

        ingredients5 = [
            ("2 1/4", "tsp", "active dry yeast", "1 packet"),
            ("1 1/2", "cups", "warm water", "110°F"),
            ("1", "tbsp", "sugar", ""),
            ("3 1/2", "cups", "all-purpose flour", "plus more for dusting"),
            ("2", "tbsp", "olive oil", "plus more for bowl"),
            ("2", "tsp", "salt", ""),
        ]
        for i, (amount, unit, name, note) in enumerate(ingredients5, 1):
            Ingredient.objects.create(recipe=recipe5, amount=amount, unit=unit, name=name, note=note, order=i)

        steps5 = [
            "In a large bowl, combine warm water, yeast, and sugar. Let sit for 5 minutes until foamy.",
            "Add olive oil, salt, and 2 cups of flour. Stir to combine.",
            "Gradually add remaining flour, 1/2 cup at a time, until dough comes together.",
            "Knead on a floured surface for 8-10 minutes until smooth and elastic. Alternatively, use a stand mixer with dough hook for 5 minutes.",
            "Place dough in an oiled bowl, turning to coat. Cover with a damp towel.",
            "Let rise in a warm place for 1-1.5 hours until doubled in size.",
            "Punch down dough and divide into 2 equal portions for two pizzas.",
            "Roll out on a floured surface to desired thickness. Top with your favorite toppings and bake at 475°F for 12-15 minutes.",
        ]
        for i, content in enumerate(steps5, 1):
            Step.objects.create(recipe=recipe5, order=i, content=content)

        # Create Recipe Collections
        self.stdout.write("\nCreating recipe collections...")
        logger.info("Creating recipe collections")

        collection1 = RecipeCollection.objects.create(
            name="Quick & Easy Weeknight Dinners",
            description="Fast recipes perfect for busy weeknights when you need dinner on the table quickly.",
        )
        collection1.recipes.add(recipe3)  # Thai Basil Chicken

        collection2 = RecipeCollection.objects.create(
            name="Comfort Food Favorites",
            description="Classic comfort food recipes that warm the soul and bring back happy memories.",
        )
        collection2.recipes.add(recipe1, recipe2)  # Cookies and Tomato Soup

        collection3 = RecipeCollection.objects.create(
            name="Meal Prep Essentials",
            description="Recipes that are perfect for preparing in advance to save time during the week.",
        )
        collection3.recipes.add(recipe4, recipe5)  # Overnight Oats and Pizza Dough

        collection4 = RecipeCollection.objects.create(
            name="Vegetarian Delights",
            description="Delicious meat-free recipes that even non-vegetarians will love.",
        )
        collection4.recipes.add(recipe2, recipe4)  # Tomato Soup and Overnight Oats

        # Create Meal Plans
        self.stdout.write("\nCreating meal plans...")
        logger.info("Creating meal plans")

        # Meal Plan 1: This Week's Meals
        today = date.today()
        meal_plan1 = MealPlan.objects.create(
            name="This Week's Meals",
            description="A balanced week of delicious and varied meals",
            start_date=today,
            end_date=today + timedelta(days=6),
        )

        # Add entries to meal plan 1
        MealPlanEntry.objects.create(
            meal_plan=meal_plan1,
            recipe=recipe4,
            date=today,
            meal_type="breakfast",
            servings=2,
            notes="Prep Sunday night for Monday morning",
        )
        MealPlanEntry.objects.create(
            meal_plan=meal_plan1,
            recipe=recipe3,
            date=today,
            meal_type="dinner",
            servings=4,
        )
        MealPlanEntry.objects.create(
            meal_plan=meal_plan1,
            recipe=recipe4,
            date=today + timedelta(days=1),
            meal_type="breakfast",
            servings=2,
        )
        MealPlanEntry.objects.create(
            meal_plan=meal_plan1,
            recipe=recipe2,
            date=today + timedelta(days=1),
            meal_type="lunch",
            servings=4,
            notes="Great with grilled cheese",
        )
        MealPlanEntry.objects.create(
            meal_plan=meal_plan1,
            recipe=recipe3,
            date=today + timedelta(days=2),
            meal_type="dinner",
            servings=4,
        )
        MealPlanEntry.objects.create(
            meal_plan=meal_plan1,
            recipe=recipe4,
            date=today + timedelta(days=3),
            meal_type="breakfast",
            servings=1,
        )

        # Meal Plan 2: Weekend Baking & Comfort Food
        meal_plan2 = MealPlan.objects.create(
            name="Weekend Baking & Comfort Food",
            description="A cozy weekend plan focused on homemade baking and comfort foods",
            start_date=today + timedelta(days=5),
            end_date=today + timedelta(days=6),
        )

        # Add entries to meal plan 2
        MealPlanEntry.objects.create(
            meal_plan=meal_plan2,
            recipe=recipe1,
            date=today + timedelta(days=5),
            meal_type="snack",
            servings=24,
            notes="Bake in the afternoon for the whole week",
        )
        MealPlanEntry.objects.create(
            meal_plan=meal_plan2,
            recipe=recipe2,
            date=today + timedelta(days=5),
            meal_type="lunch",
            servings=6,
        )
        MealPlanEntry.objects.create(
            meal_plan=meal_plan2,
            recipe=recipe5,
            date=today + timedelta(days=6),
            meal_type="dinner",
            servings=8,
            notes="Pizza night! Use dough for two 12-inch pizzas",
        )

        # Meal Plan 3: Next Month Preview
        next_month_start = today + timedelta(days=30)
        meal_plan3 = MealPlan.objects.create(
            name="Next Month's Quick Meals",
            description="Planning ahead with quick and easy recipes",
            start_date=next_month_start,
            end_date=next_month_start + timedelta(days=4),
        )

        # Add entries to meal plan 3
        MealPlanEntry.objects.create(
            meal_plan=meal_plan3,
            recipe=recipe4,
            date=next_month_start,
            meal_type="breakfast",
            servings=1,
        )
        MealPlanEntry.objects.create(
            meal_plan=meal_plan3,
            recipe=recipe3,
            date=next_month_start,
            meal_type="dinner",
            servings=2,
        )
        MealPlanEntry.objects.create(
            meal_plan=meal_plan3,
            recipe=recipe2,
            date=next_month_start + timedelta(days=1),
            meal_type="lunch",
            servings=3,
        )

        # Summary
        total_recipes = Recipe.objects.count()
        total_collections = RecipeCollection.objects.count()
        total_meal_plans = MealPlan.objects.count()
        total_meal_plan_entries = MealPlanEntry.objects.count()

        logger.info(
            f"Database seeding completed successfully. "
            f"Total recipes: {total_recipes}, Collections: {total_collections}, "
            f"Meal Plans: {total_meal_plans}, Meal Plan Entries: {total_meal_plan_entries}"
        )
        logger.debug(
            f"Created recipes: {recipe1.title}, {recipe2.title}, {recipe3.title}, {recipe4.title}, {recipe5.title}"
        )

        self.stdout.write(self.style.SUCCESS("\n✓ Successfully created sample data!"))
        self.stdout.write(
            "\nRecipes:"
            f"\n  • {recipe1.title}"
            f"\n  • {recipe2.title}"
            f"\n  • {recipe3.title}"
            f"\n  • {recipe4.title}"
            f"\n  • {recipe5.title}"
        )
        self.stdout.write(
            "\nCollections:"
            f"\n  • {collection1.name} ({collection1.recipes.count()} recipes)"
            f"\n  • {collection2.name} ({collection2.recipes.count()} recipes)"
            f"\n  • {collection3.name} ({collection3.recipes.count()} recipes)"
            f"\n  • {collection4.name} ({collection4.recipes.count()} recipes)"
        )
        self.stdout.write(
            "\nMeal Plans:"
            f"\n  • {meal_plan1.name} ({meal_plan1.entries.count()} entries)"
            f"\n  • {meal_plan2.name} ({meal_plan2.entries.count()} entries)"
            f"\n  • {meal_plan3.name} ({meal_plan3.entries.count()} entries)"
        )
