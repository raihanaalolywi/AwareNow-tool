from django import forms
from .models import PhishingCampaign
from account.models import CompanyGroup


class PhishingCampaignForm(forms.ModelForm):
    class Meta:
        model = PhishingCampaign
        fields = [
            "title",
            "user_group",
            "sender",
            "scheduled_date",
            "template",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Campaign title"}),
            "user_group": forms.Select(attrs={"class": "form-select"}),  # إذا صار FK
            "sender": forms.EmailInput(attrs={"class": "form-control", "placeholder": "sender@example.com"}),
            "scheduled_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "template": forms.HiddenInput(),
        }


    def __init__(self, *args, **kwargs):
        company = kwargs.pop("company", None)
        super().__init__(*args, **kwargs)

        qs = CompanyGroup.objects.all().order_by("-id")

        if company:
            qs = qs.filter(company=company, is_system=False)

        self.fields["user_group"].queryset = qs
        self.fields["user_group"].empty_label = "Select user group"
