from django import forms
from django.utils import timezone
from datetime import datetime, time

from .models import PhishingCampaign,EmailTemplate
from account.models import CompanyGroup  



class PhishingCampaignForm(forms.ModelForm):
    class Meta:
        model = PhishingCampaign
        fields = [
            "title",
            "user_group",
            "sender",
            "scheduled_date",
            "ends_at",
            "template",
        ]
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Campaign title"
            }),
            "user_group": forms.Select(attrs={
                "class": "form-select"
            }),
            "sender": forms.EmailInput(attrs={
                "class": "form-control",
                "placeholder": "sender@example.com"
            }),
            "scheduled_date": forms.DateInput(attrs={
                "type": "date",
                "class": "form-control"
            }),
            "ends_at": forms.DateTimeInput(attrs={
                "type": "datetime-local",
                "class": "form-control"
            }),
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
        self.fields["ends_at"].label = "Phishing end date & time"

    def clean(self):
        cleaned = super().clean()
        scheduled_date = cleaned.get("scheduled_date")
        ends_at = cleaned.get("ends_at")

        if not ends_at:
            self.add_error("ends_at", "Please set an end date & time for the campaign.")
            return cleaned

        if ends_at <= timezone.now():
            self.add_error("ends_at", "End date/time must be in the future.")
            return cleaned

        if scheduled_date:
            start_dt = timezone.make_aware(datetime.combine(scheduled_date, time.min))
            if ends_at <= start_dt:
                self.add_error("ends_at", "End date/time must be after the scheduled date.")

        return cleaned

# Email Template Form 

class EmailTemplateForm(forms.ModelForm):
    class Meta:
        model = EmailTemplate
        fields = [
            "name",
            "subject",
            "preview_image",
            "html_content",
        ]

        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Template name"
            }),
            "subject": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Email subject"
            }),
            "preview_image": forms.ClearableFileInput(attrs={
                "class": "form-control"
            }),
            "html_content": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 12,
                "placeholder": "Paste HTML email content here"
            }),
        }
