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
                return redirect("courses:platform_admin_dashboard")

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

    # ⛔️ منع تفعيل حساب Disabled
    if user.is_disabled:
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

# ======= Company User ========
@login_required
def company_users(request):
    if request.user.role != "COMPANY_ADMIN":
        return redirect("account:platform-login")

    company = request.user.company

    users = User.objects.filter(
        company=company
    ).exclude(role="PLATFORM_ADMIN")

    # ===== Filters (GET only) =====
    status_filter = request.GET.get("status")
    role_filter = request.GET.get("role")

    if status_filter == "ACTIVE":
        users = users.filter(is_active=True, is_disabled=False)

    elif status_filter == "PENDING":
        users = users.filter(is_active=False, is_disabled=False)

    elif status_filter == "DISABLED":
        users = users.filter(is_disabled=True)

    if role_filter in ["COMPANY_ADMIN", "EMPLOYEE"]:
        users = users.filter(role=role_filter)

    from .forms import CompanyUserCreateForm
    from .services import get_or_create_staff_group
    import uuid

    if request.method == "POST":
        form = CompanyUserCreateForm(request.POST, company=company)
        if form.is_valid():
            user = form.save(commit=False)
            user.company = company
            user.username = user.email
            user.is_active = False
            user.set_unusable_password()
            user.activation_token = str(uuid.uuid4())
            user.save()

            staff_group = get_or_create_staff_group(company)
            user.company_groups.add(staff_group)

            for group in form.cleaned_data["company_groups"]:
                user.company_groups.add(group)

            send_activation_email(user)
            messages.success(request, "User created successfully.")
            return redirect("account:company-users")
    else:
        form = CompanyUserCreateForm(company=company)

    return render(request, "account/company_users.html", {
        "users": users,
        "form": form,
    })

@login_required
def toggle_user_active(request, user_id):
    if request.user.role != "COMPANY_ADMIN":
        return redirect("account:platform-login")

    user = get_object_or_404(
        User,
        id=user_id,
        company=request.user.company
    )

    if user == request.user:
        messages.error(request, "You cannot disable yourself.")
        return redirect("account:company-users")

    # 🔴 Soft Disable
    if user.is_active and not user.is_disabled:
        user.original_email = user.email
        user.email = f"disabled_{user.id}_{user.email}"
        user.is_active = False
        user.is_disabled = True
        user.save()

    return redirect("account:company-users")
