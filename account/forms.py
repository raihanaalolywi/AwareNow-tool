from django import forms
from .models  import Company, SubscriptionPlan, User

class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = [
            "name",
            "email_domain",
            "subscription_plan",
            "license_start_date",
            "license_end_date",
        ]

        widgets = {
            "license_start_date": forms.DateInput(attrs={"type": "date"}),
            "license_end_date": forms.DateInput(attrs={"type": "date"}),
        }
    
    def clean_email_domain(self):
        domain = self.cleaned_data.get("email_domain")

        if not domain:
            return domain  # Django بيتكفل بـ required

        domain = domain.strip().lower()

        if "@" in domain or " " in domain:
            raise forms.ValidationError(
                "Enter a valid domain (example: company.com)"
            )

        if "." not in domain:
            raise forms.ValidationError(
                "Enter a valid domain (example: company.com)"
            )

        return domain



class SuperAdminForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username", "email"]
    def clean_email(self):
        email = self.cleaned_data.get("email")

        if not email:
            raise forms.ValidationError("Email is required.")

        return email.strip().lower()