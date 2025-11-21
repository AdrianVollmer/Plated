## Issue: Refactor views

Make views.py into a directory with several files.

## Issue: Meal planner

Add meal planner and shopping list generator.

## Issue: I18n

Add support for internationalization

## Issue: User support

A environment variable should decide whether the app runs in single user
mode or multi isuer mode.

### Single user mode

In single user mode, the anonymous user is automatically the admin user.

### Multi user mode

In multi user mode, the anonymous user can browse, but make no
modifications whatsoever. Read only.

Logged on users can create recipes. They can change user-specific
settings, but not site-wide settings. We may have to start
differentiating such settings.

Recipes and collections should belong to a user. Modify the model for
that (add a "owner"). Properties (ingredients, units, keywords) do not
belong to a user.

Users can only change or delete recipes or collections that they own.

## Issue: Environment settings

Read from env the settings regarding time zone, secret key, etc.
