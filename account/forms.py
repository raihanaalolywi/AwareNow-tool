from django import forms
from .models  import Company, SubscriptionPlan, User, CompanyGroup

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



COMPANY_USER_ROLE_CHOICES = (
    ("COMPANY_ADMIN", "Company Admin"),
    ("EMPLOYEE", "Employee"),
)

class CompanyUserCreateForm(forms.ModelForm):
    role = forms.ChoiceField(choices=COMPANY_USER_ROLE_CHOICES)

    company_groups = forms.ModelMultipleChoiceField(
        queryset=CompanyGroup.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "role", "department"]

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.company = company

        if company:
            self.fields["company_groups"].queryset = CompanyGroup.objects.filter(
                company=company,
                is_system=False
            ).order_by("name")

    def clean_email(self):
        email = self.cleaned_data.get("email")

        if not email:
            raise forms.ValidationError("Email is required.")

        email = email.strip().lower()

        if User.objects.filter(
            email=email,
            company=self.company,
            is_disabled=False
        ).exists():
            raise forms.ValidationError(
                "This email already exists in your company."
            )

        return email
