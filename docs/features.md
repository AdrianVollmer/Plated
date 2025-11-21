# Features

Comprehensive guide to Plated's features.

## Recipe Management

### Creating Recipes

1.  Click **"Add Recipe"** from the homepage

2.  Fill in recipe details:

    - Title (required)
    - Description
    - Number of servings
    - Prep time and wait time
    - Keywords (comma-separated)
    - Optional: URL, notes, special equipment

3.  Add ingredients with autocomplete suggestions

4.  Add preparation steps (supports Markdown)

5.  Upload recipe images

6.  Save

### Editing Recipes

Click the **Edit** button on any recipe card or detail page.

### Smart Ingredient Input

As you type ingredient names and units, autocomplete suggestions appear
based on existing data. This helps maintain consistency across recipes.

### Markdown in Steps

Steps support Markdown formatting:

``` markdown
**Bold text** for emphasis
*Italic text* for notes
- Bullet lists
1. Numbered lists
[Links](https://example.com)
```

## Collections

Group related recipes together.

### Creating Collections

1.  Navigate to **Collections**
2.  Click **"Create Collection"**
3.  Add name, description, and recipes
4.  Save

Collections can contain any number of recipes.

## Import & Export

### Exporting Recipes

Click **Export JSON** on any recipe to download a JSON file containing
all recipe data.

### Importing Recipes

1.  Click **Import Recipe** from the homepage
2.  Upload a JSON file (previously exported)
3.  Review and confirm

## PDF Generation

Generate beautifully formatted PDFs of your recipes.

### Export to PDF

Click **Download PDF** on any recipe detail page. Requires Typst to be
installed.

### PDF Format

PDFs include:

- Recipe title and description
- Ingredient list
- Step-by-step instructions
- Servings, prep time, wait time
- Keywords and notes

## AI Recipe Extraction

Extract recipe data from URLs using AI.

### Using AI Extraction

1.  Navigate to **Settings**
2.  Configure AI settings (API key, model)
3.  Click **AI Extract** from homepage
4.  Enter a recipe URL
5.  Review extracted data
6.  Save as new recipe

Supported sources: Most recipe websites.

## Data Management

### Managing Ingredient Names

Keep ingredient names consistent:

1.  Navigate to **Manage → Ingredient Names**
2.  View all used ingredient names
3.  Rename to standardize (e.g., "tomatos" → "tomatoes")
4.  Changes apply to all recipes using that ingredient

### Managing Units

Standardize measurement units:

1.  Navigate to **Manage → Units**
2.  View all used units
3.  Rename to standardize (e.g., "tsp" → "teaspoon")
4.  Changes apply to all recipes using that unit

## Themes

### Changing Theme

1.  Navigate to **Settings**
2.  Select from available themes:
    - Light (default pink)
    - Dark
    - Warm (amber/orange)
    - Cool (blue)
    - Forest (green)

Theme preference is saved in browser.

## Mobile Features

Plated is fully responsive and mobile-friendly:

- Touch-optimized navigation
- Readable text on small screens
- Easy-to-tap buttons
- PWA support (can be installed on mobile home screen)

### Scale Servings

On any recipe detail page:

1.  Click the **servings adjuster**
2.  Enter new serving count
3.  All ingredient amounts update automatically

## Admin Interface

Django admin provides advanced management:

1.  Navigate to `/admin`
2.  Log in with superuser credentials
3.  Access all models directly
4.  Bulk operations
5.  Advanced filtering

Useful for:

- Bulk recipe imports
- Data cleanup
- User management (if enabled)
- Viewing logs

## API Access

For developers: Plated provides JSON export/import that can be
automated.

### JSON Schema

See `src/recipeformat.txt` for the complete schema specification.

### Programmatic Import

``` bash
curl -X POST http://localhost:8000/import/ \
  -F "json_file=@recipe.json" \
  -H "X-CSRFToken: <token>"
```

CSRF token required for POST requests.

## Data Privacy

- All data stored locally in your SQLite database
- No external services required (except optional AI extraction)
- Full control over your recipe data
- Export anytime in JSON format
