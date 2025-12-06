# Test View Server

The test view server is a development tool that allows developers to preview all views in the application with different data states. This is particularly useful for UI/UX development, testing visual consistency, and checking how views behave with varying amounts of data.

## Purpose

When developing user interfaces, it's important to test how they look and behave with:

- **Empty states**: No data available
- **Minimal states**: Single item
- **Normal states**: A few items (3)
- **Heavy states**: Many items (30+)

The test view server creates test data and provides a convenient interface to preview all these scenarios without manually creating and deleting data.

## Usage

### Step 1: Create Test Data

Run the management command to create test data in your database:

```bash
uv run python src/plated/manage.py testviews
```

**Important**: Make sure you're using a development database! This command will create test recipes, collections, and meal plans prefixed with `[TEST]`.

The command will:
- Prompt for confirmation
- Create 30 test recipes with lorem ipsum content
- Create 5 test collections
- Create 5 test meal plans with varying numbers of entries
- Display instructions for accessing the test view server

### Step 2: Start the Development Server

If not already running, start the Django development server:

```bash
uv run python src/plated/manage.py runserver 8001
```

You can use any port, but 8001 is recommended to avoid conflicts with the main development server.

### Step 3: Access the Test View Server

Open your browser and navigate to:

```
http://127.0.0.1:8001/testviews/
```

**Note**: The test view server is only available when `DEBUG=True` in your settings.

## Features

### Sidebar Navigation

The test view server features a sidebar on the left with all available test views organized by category:

- **Recipe Views**: List views with 0, 1, 3, and 30 items, detail view, create/edit forms, cooking view
- **Collection Views**: Similar variations for collections
- **Meal Plan Views**: Meal plan lists, detail views, and shopping lists
- **Management Views**: Ingredient names, units, keywords management
- **AI & Jobs Views**: AI extraction and job monitoring
- **Other Views**: Settings and about pages

### Dark Mode Toggle

The test view server includes a theme switcher with three options:

- **Light**: Force light mode
- **Dark**: Force dark mode
- **Auto**: Follow system preference

The theme preference is stored in local storage and persists across sessions.

### Live Preview

Clicking on any view in the sidebar loads it in an iframe in the main content area. This allows you to:

- Quickly switch between different views
- Compare how views look with different data states
- Test responsive behavior
- Check visual consistency across light and dark modes

## Test Data

All test data is created with:

- Realistic recipe names (e.g., "Creamy Tuscan Garlic Chicken", "Thai Green Curry")
- Lorem ipsum descriptions for varied content lengths
- Randomized ingredients with realistic units and amounts
- Step-by-step instructions using lorem ipsum
- Collections with meaningful names
- Meal plans with entries across different dates and meal types

All test data is prefixed with `[TEST]` to make it easy to identify and clean up.

## Cleaning Up

To remove test data, you can filter and delete by the `[TEST]` prefix:

```python
# In Django shell
from recipes.models import Recipe, RecipeCollection, MealPlan

Recipe.objects.filter(title__startswith="[TEST]").delete()
RecipeCollection.objects.filter(name__startswith="[TEST]").delete()
MealPlan.objects.filter(name__startswith="[TEST]").delete()
```

Or simply re-run the `testviews` command, which clears old test data before creating new test data.

## Development Workflow

Typical workflow when using the test view server:

1. Make changes to templates, CSS, or views
2. Reload the test view server in your browser
3. Click through different data states to verify the changes
4. Toggle between light and dark mode to check theme consistency
5. Test responsive behavior by resizing the browser window
6. Verify that empty states, single items, and many items all look correct

## Technical Details

- **URL Pattern**: `/testviews/` (only available in DEBUG mode)
- **Management Command**: `manage.py testviews`
- **Templates**: Located in `templates/testviews/`
- **Views**: Defined in `recipes/views/testviews.py`
- **URL Configuration**: `recipes/testviews_urls.py`
- **Test Data Prefix**: `[TEST]` for easy identification

## Tips

- Use the test view server alongside browser developer tools to inspect CSS and debug layout issues
- Test keyboard navigation and accessibility features across different views
- Verify that forms work correctly with pre-filled data
- Check how pagination appears with exactly 30 items
- Ensure error states and edge cases are handled gracefully
