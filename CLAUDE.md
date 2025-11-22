# Instructions for Claude

This is a Python app for managing recipes.

## Principles

- Open Source
- Open Data
- Simple
- Thoughtful UI/UX
- Minimal JavaScript

We prefer server-side render pages.

We focus on exporting and importing data to several formats.

Aesthetics is important, but even more important is usability.

## Tech Stack

- Django 5
- Bootstrap 5
- Sqlite
- Vanilla JS

## Python conventions

- We use ruff for formatting and linting
- We use mypy for type checking
- Always use type hints
- We make heavy use of `uv`. Always run python programs with
  `uv run ...`.

## Coding convetions

- Try to keep code readable and maintainable
- Apply the DRY principle as much as possible (but not more)
- When a file approaches 1000 lines, split it up into sub modules
- When a function approaches 100 lines or nested for-if-statements of
  the fourth level, consider splitting the function into several

## Development

Issues are in `issues/`. When you are told to solve one issue, delete
the issue file and commit your changes with git.

When commiting, supply author information on the command line.
