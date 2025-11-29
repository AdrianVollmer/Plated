# Internationalization (i18n)

Plated supports multiple languages through Django's internationalization
framework based on gettext.

## User Guide

### Changing Language

Users can select their preferred language from the settings:

1.  Navigate to **Settings**
2.  Select your language from the dropdown
3.  Click **Save Language**

The interface will immediately switch to the selected language.

### Supported Languages

Currently supported languages:

- English (en)
- German (de)

## Developer Guide

### Prerequisites

Translation management requires GNU gettext tools:

**Ubuntu/Debian:**

``` bash
sudo apt-get install gettext
```

**macOS:**

``` bash
brew install gettext
brew link gettext --force
```

**Windows:** Download from [GNU gettext
website](https://www.gnu.org/software/gettext/) or use WSL.

### Adding a New Language

To add support for a new language:

1.  **Add to settings**

    Edit `src/config/settings.py` and add the language to the
    `LANGUAGES` list:

    ``` python
    LANGUAGES = [
        ("en", "English"),
        ("es", "Español"),
        ("fr", "Français"),
        ("de", "Deutsch"),
        ("it", "Italiano"),
        ("pt", "Português"),
        ("ja", "日本語"),  # Adding Japanese
    ]
    ```

2.  **Generate message files**

    From the `src/` directory, run:

    ``` bash
    uv run python src/plated/manage.py makemessages -l ja
    ```

    This creates `src/locale/ja/LC_MESSAGES/django.po`

3.  **Translate strings**

    Edit the generated `.po` file and translate the strings:

    ``` po
    msgid "Recipes"
    msgstr "レシピ"

    msgid "Settings"
    msgstr "設定"
    ```

4.  **Compile translations**

    ``` bash
    uv run python src/plated/manage.py compilemessages
    ```

    This creates `django.mo` binary files that Django uses.

5.  **Test**

    Restart the development server and select the new language in
    settings.

### Modifying Existing Translations

To update translations for an existing language:

1.  **Update message files**

    If you've added new translatable strings to the code, extract them:

    ``` bash
    uv run python src/plated/manage.py makemessages -l es
    ```

    This updates `src/locale/es/LC_MESSAGES/django.po` with new strings.

2.  **Edit translations**

    Open the `.po` file and add/modify translations:

    ``` po
    #: templates/base.html:40
    msgid "Recipes"
    msgstr "Recetas"

    #: recipes/views/settings.py:41
    msgid "Language settings saved successfully!"
    msgstr "¡Configuración de idioma guardada exitosamente!"
    ```

3.  **Compile**

    ``` bash
    uv run python src/plated/manage.py compilemessages
    ```

4.  **Test**

    Refresh the browser to see changes (in production, restart may be
    needed).

### Updating All Languages

To update all language files at once:

``` bash
uv run python src/plated/manage.py makemessages -a
```

Then edit each `.po` file and compile:

``` bash
uv run python src/plated/manage.py compilemessages
```

### Marking New Strings for Translation

#### In Templates

Use the `{% trans %}` tag for simple strings:

``` django
{% load i18n %}
<h1>{% trans "Welcome to Plated" %}</h1>
```

For strings with variables, use `{% blocktrans %}`:

``` django
{% blocktrans count counter=list|length %}
There is {{ counter }} recipe
{% plural %}
There are {{ counter }} recipes
{% endblocktrans %}
```

#### In Python Code

Use `gettext()` or its shortcuts:

``` python
from django.utils.translation import gettext as _

messages.success(request, _("Recipe saved successfully!"))
```

For lazy evaluation (in models, forms):

``` python
from django.utils.translation import gettext_lazy as _

class Recipe(models.Model):
    title = models.CharField(_("Title"), max_length=200)
```

### Best Practices

1.  **Context matters**: Add context for ambiguous strings

    ``` python
    from django.utils.translation import pgettext

    # "May" as month vs "may" as auxiliary verb
    month = pgettext("month name", "May")
    ```

2.  **Avoid concatenation**: Don't split sentences

    ❌ Bad:

    ``` python
    _("Welcome") + " " + username
    ```

    ✅ Good:

    ``` python
    _("Welcome %(username)s") % {"username": username}
    ```

3.  **Comments for translators**: Add context when needed

    ``` python
    # Translators: This is shown when a recipe is successfully deleted
    messages.success(request, _("Recipe deleted"))
    ```

4.  **Test all languages**: Verify translations display correctly

5.  **Keep .po files in git**: Track translation files in version
    control

### Translation Workflow

Recommended workflow for contributors:

1.  **Developer adds translatable strings**

    - Mark strings with `{% trans %}` or `_()`
    - Run `makemessages` to update `.po` files
    - Commit code and updated `.po` files

2.  **Translator adds translations**

    - Edit `.po` files
    - Run `compilemessages` to test locally
    - Commit translated `.po` files

3.  **Deployment**

    - Run `compilemessages` as part of deployment
    - `.mo` files should NOT be in git (generated files)

### Troubleshooting

**Translations not showing:**

- Did you run `compilemessages`?
- Did you restart the development server?
- Is the language selected in settings?
- Check browser language preferences don't override

**Encoding errors:**

Ensure `.po` files use UTF-8 encoding:

``` bash
file -i locale/es/LC_MESSAGES/django.po
# Should show: charset=utf-8
```

**Missing strings:**

If a string isn't being picked up:

1.  Verify the string is wrapped with `{% trans %}` or `_()`
2.  Run `makemessages` again
3.  Check the `.po` file was updated
4.  Recompile with `compilemessages`

### Advanced: JavaScript Translations

For translating strings in JavaScript files:

1.  **Mark strings in JS**

    Create a JavaScript catalog view in `urls.py`:

    ``` python
    from django.views.i18n import JavaScriptCatalog

    urlpatterns = [
        path('jsi18n/', JavaScriptCatalog.as_view(), name='javascript-catalog'),
    ]
    ```

2.  **Include in template**

    ``` django
    <script src="{% url 'javascript-catalog' %}"></script>
    ```

3.  **Use in JavaScript**

    ``` javascript
    const message = gettext("Recipe saved!");
    ```

4.  **Extract and compile**

    JavaScript strings are extracted with `makemessages -d djangojs`

### File Structure

Translation files are organized as:

    src/
    ├── locale/
    │   ├── es/
    │   │   └── LC_MESSAGES/
    │   │       ├── django.po      # Editable translation file
    │   │       └── django.mo      # Compiled (generated)
    │   ├── fr/
    │   │   └── LC_MESSAGES/
    │   │       ├── django.po
    │   │       └── django.mo
    │   └── ...

## Contributing Translations

Contributions of new translations are welcome!

1.  Fork the repository
2.  Add or update translations following the guide above
3.  Test locally
4.  Submit a pull request with:
    - Updated `.po` files
    - Updated `LANGUAGES` in `settings.py` (if new language)
    - DO NOT include `.mo` files (these are generated)

Native speakers are especially encouraged to contribute!
