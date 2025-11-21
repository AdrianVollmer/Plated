# Instructions

Let's build a recipe app!

## Design stage

- Use Django with bootstrap, sqlite, minimal vanilla JavaScript on the
  frontend
- No user management yet
- Mobile-friendly
- Recipes have:
  - a title
  - a description
  - number of servings
  - ingredients
  - steps
  - zero or more pictures
  - keywords
  - prep time
  - wait time
- An ingredient has:
  - amount
  - unit
  - name
  - note
- A step can be in markdown
- We need a mechanism that encourages consistent ingredient names and
  units (like a dropdown suggesting existing names)
- Recipes must have an import/export function, we need a JSON schema for
  that
- There can be recipe collections
- Recipes can be rendered server-side in PDF using Typst (assumed to be
  installed)
- Layout should be modern, friendly, usable

Let's keep it simple at first, but we may want to add more features
later.

*Python specifics*:

- Use `uv run ...` for everything
- We'll use type hints
- We'll use mypy with the Django plugin
- We'll use pytest for the test suite
- Formatting with ruff

## Planning

### Phase 1: Project Setup

1.  Initialize Django project with uv (Already done!)
2.  Create recipes app
3.  Configure settings (database, static files, media files)
4.  Set up Bootstrap integration

### Phase 2: Data Models

1.  Create Recipe model (title, description, servings, keywords,
    prep_time, wait_time, url, notes, special_equipment)
2.  Create Ingredient model (recipe FK, amount, unit, name, note)
3.  Create Step model (recipe FK, order, content with markdown support)
4.  Create RecipeImage model (recipe FK, image file, order)
5.  Create RecipeCollection model (name, description, recipes FK)
6.  Run migrations

### Phase 3: Admin Interface

1.  Register models in admin
2.  Configure inline editing for ingredients, steps, and images
3.  Add admin customizations for better UX

### Phase 4: Core Views & Templates

1.  Recipe list view (homepage)
2.  Recipe detail view
3.  Recipe create/edit forms with formsets for ingredients and steps
4.  Recipe delete view
5.  Base template with Bootstrap layout
6.  Make all templates mobile-friendly

### Phase 5: Smart Ingredient/Unit Input

1.  Create API endpoint to get existing ingredient names
2.  Create API endpoint to get existing units
3.  Add JavaScript autocomplete/datalist for ingredient name field
4.  Add JavaScript autocomplete/datalist for unit field

### Phase 6: Import/Export

1.  Define JSON schema for recipe data
2.  Create export view (download recipe as JSON)
3.  Create import view (upload JSON file)
4.  Add validation for imported data

### Phase 7: PDF Generation

1.  Add PDF download view
2.  Call Typst with a given Typst file (`src/recipe.typ`) which reads a
    JSON recipe (schema: `src/recipeformat.txt`)

### Phase 8: Polish & Testing

1.  Refine Bootstrap styling
2.  Test mobile responsiveness
3.  Add basic validation and error handling
4.  Manual testing of all features

## Expanding

### Issue: Meal planner

Add meal planner and shopping list generator.
