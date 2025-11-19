from __future__ import annotations

from django import forms

from .models import Recipe


class RecipeForm(forms.ModelForm):
    """Form for creating and editing recipes."""

    class Meta:
        model = Recipe
        fields = [
            "title",
            "description",
            "servings",
            "prep_time",
            "wait_time",
            "keywords",
            "url",
            "notes",
            "special_equipment",
        ]
        widgets = {
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Recipe title"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Brief description",
                }
            ),
            "servings": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "prep_time": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g., 00:30:00 for 30 minutes",
                    "help_text": "Format: HH:MM:SS",
                }
            ),
            "wait_time": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g., 01:00:00 for 1 hour",
                    "help_text": "Format: HH:MM:SS",
                }
            ),
            "keywords": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "italian, pasta, vegetarian",
                }
            ),
            "url": forms.URLInput(
                attrs={"class": "form-control", "placeholder": "https://..."}
            ),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "special_equipment": forms.Textarea(
                attrs={"class": "form-control", "rows": 2}
            ),
        }
