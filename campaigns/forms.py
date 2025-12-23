from django import forms
from .models import PhishingCampaign


class PhishingCampaignForm(forms.ModelForm):
    class Meta:
        model = PhishingCampaign
        fields = [
            "title",
            "user_group",
            "sender",
            "scheduled_date",
            "status",
            "template",
        ]
        widgets = {
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Campaign title"}
            ),
            "user_group": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Group name"}
            ),
            "sender": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "sender@example.com"}
            ),
            "scheduled_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
            "status": forms.Select(attrs={"class": "form-select"}),
            # ✅ أهم سطر
            "template": forms.HiddenInput(),
        }
