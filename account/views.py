from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from .forms import CompanyForm, SuperAdminForm
from django.contrib.auth.decorators import login_required
import uuid
from .models import Company, User
from .services import send_activation_email
from django.shortcuts import get_object_or_404
# from django.contrib.auth import logout
from .models import SubscriptionPlan
from django.utils import timezone
from django.db import transaction
from django.contrib import messages

# ==== admin platform Dashboard ====
@login_required
def platform_dashboard(request):
    if not request.user.is_superuser:
        return redirect("account:platform-login")
    
    plans = SubscriptionPlan.objects.all()
    companies = Company.objects.all()

     # Filters
    status_filter = request.GET.get("status")
    plan_filter = request.GET.get("plan")

    if plan_filter:
        companies = companies.filter(subscription_plan_id=plan_filter)

    if status_filter:
        today = timezone.now().date()
        if status_filter == "ACTIVE":
            companies = companies.filter(license_end_date__gte=today)
        elif status_filter == "EXPIRED":
            companies = companies.filter(license_end_date__lt=today)

    context = {
        "plans": plans,
        "companies": companies
    }

    return render(request, "account/platform_dashboard.html", context)

# ==== Company platform Dashboard ====
@login_required
def company_dashboard(request):
    if request.user.role != "COMPANY_ADMIN":
        return redirect("account:platform-login")

    return render(request, "account/company_dashboard.html")


# ==== Employee platform Dashboard ====
@login_required
def employee_dashboard(request):
    if request.user.role != "EMPLOYEE":
        return redirect("account:platform-login")

    return render(request, "account/employee_dashboard.html")


# ==== login method ====
def platform_login(request):
    # اذا مسجل دخول ينقله لصفحة الدشبورد للبلاتفورم 
    # if request.user.is_authenticated and request.user.is_superuser:
    #     return redirect("account:platform-dashboard")
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)

            # Platform Admin
            if user.is_superuser:
                return redirect("account:platform-dashboard")

            # Company Admin
            if user.role == "COMPANY_ADMIN":
                return redirect("account:company-dashboard")

            # Employee 
            if user.role == "EMPLOYEE":
                return redirect("account:employee-dashboard")

        return render(request, "account/login.html", {
            "error": "Invalid email or password"
        })

    return render(request, "account/login.html")

    #     if user and user.is_superuser:
    #         login(request, user)
    #         return redirect("account:platform-dashboard")

    #     return render(request, "account/login.html", {
    #         "error": "Invalid email or password"
    #     })

    # return render(request, "account/login.html")

# ==== admin platform create company ====
@login_required
def create_company(request):
    if not request.user.is_superuser:
        return redirect("account:platform-login")

    if request.method == "POST":
        company_form = CompanyForm(request.POST)
        admin_form = SuperAdminForm(request.POST)

        if company_form.is_valid() and admin_form.is_valid():

            company_domain = company_form.cleaned_data["email_domain"]
            admin_email = admin_form.cleaned_data["email"]

            if not admin_email.endswith("@" + company_domain):
                admin_form.add_error(
                    "email",
                    "Admin email must belong to the company domain."
                )

            else:
                with transaction.atomic():
                    # 1) Create company
                    company = company_form.save()

                    # 2) Create company super admin
                    user = admin_form.save(commit=False)
                    user.role = "COMPANY_ADMIN"
                    user.company = company
                    user.is_active = False
                    user.set_unusable_password()
                    user.activation_token = str(uuid.uuid4())
                    user.save()

                    # 3) Send activation email
                    send_activation_email(user)

                messages.success(
                    request,
                    f"Company created successfully. Activation email sent to {user.email}."
                )
                return redirect("account:create-company")

    else:
        company_form = CompanyForm()
        admin_form = SuperAdminForm()

    return render(request, "account/create_company.html", {
        "company_form": company_form,
        "admin_form": admin_form,
    })

# ==== Logout =====
def logout_view(request):
    logout(request)
    return redirect("account:platform-login")

# ====== activate account =====
def activate_account(request, token):
    try:
        user = User.objects.get(activation_token=token)
    except User.DoesNotExist:
        return render(request, "account/activation_invalid.html")

    if request.method == "POST":
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            return render(request, "account/activate_account.html", {
                "error": "Passwords do not match"
            })

        user.set_password(password)
        user.is_active = True
        user.activation_token = None
        user.save()

        return redirect("account:platform-login")

    return render(request, "account/activate_account.html")