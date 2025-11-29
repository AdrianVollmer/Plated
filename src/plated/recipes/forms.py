from __future__ import annotations

from django import forms
from django.utils.translation import gettext_lazy as _

from .models import AISettings, Recipe, UserSettings


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
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": _("Recipe title")}),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": _("Brief description"),
                }
            ),
            "servings": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "prep_time": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": _("e.g., 00:30:00 for 30 minutes"),
                    "help_text": _("Format: HH:MM:SS"),
                }
            ),
            "wait_time": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": _("e.g., 01:00:00 for 1 hour"),
                    "help_text": _("Format: HH:MM:SS"),
                }
            ),
            "keywords": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": _("italian, pasta, vegetarian"),
                }
            ),
            "url": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://..."}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "special_equipment": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }


class AISettingsForm(forms.ModelForm):
    """Form for managing AI/LLM settings."""

    class Meta:
        model = AISettings
        fields = ["api_url", "api_key", "model", "max_tokens", "temperature", "timeout"]
        widgets = {
            "api_url": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "https://api.openai.com/v1/chat/completions",
                }
            ),
            "api_key": forms.PasswordInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "sk-...",
                }
            ),
            "model": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": _("gpt-4 or claude-3-sonnet-20240229"),
                }
            ),
            "max_tokens": forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 100000}),
            "temperature": forms.NumberInput(attrs={"class": "form-control", "min": 0.0, "max": 2.0, "step": 0.1}),
            "timeout": forms.NumberInput(attrs={"class": "form-control", "min": 10, "max": 600}),
        }


class AIRecipeExtractionForm(forms.Form):
    """Form for extracting recipes using AI."""

    INPUT_TYPES = [
        ("text", _("Plain Text")),
        ("html", _("HTML")),
        ("url", _("URL")),
    ]

    input_type = forms.ChoiceField(
        choices=INPUT_TYPES,
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
        initial="text",
        label=_("Input Type"),
    )
    input_content = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 10,
                "placeholder": _("Paste recipe text, HTML, or URL here..."),
            }
        ),
        label=_("Recipe Content"),
    )
    prompt = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": _("e.g., 'translate to German and use metric units'"),
            }
        ),
        label=_("Instructions (Optional)"),
        required=False,
        help_text=_("Additional instructions for the AI model"),
    )


class UserSettingsForm(forms.ModelForm):
    """Form for managing user settings including language preference."""

    class Meta:
        model = UserSettings
        fields = ["language"]
        widgets = {
            "language": forms.Select(attrs={"class": "form-select"}),
        }
        labels = {
            "language": _("Interface Language"),
        }
