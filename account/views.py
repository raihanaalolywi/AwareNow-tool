from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from .forms import CompanyForm, SuperAdminForm, CompanyGroupCreateForm, AddUsersToGroupForm
from django.contrib.auth.decorators import login_required
import uuid
from .models import Company, User, CompanyGroup, EmployeeProfile
from .services import send_activation_email
from django.shortcuts import get_object_or_404
from .models import SubscriptionPlan
from django.utils import timezone
from django.db import transaction
from django.contrib import messages
from django.db.models import Count, Q, Avg
from django.http import JsonResponse
import json
from courses.models import CompanyCourseAssignment, Course, EmployeeCourseAssignment, EmployeeCourseProgress, QuizAttempt, CompanyCourseGroup

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
    
    company = request.user.company
    
    # ========== PROGRESS STATISTICS ==========
    total_employees = User.objects.filter(company=company, is_disabled=False, role='EMPLOYEE').count()
    
    # Get assigned courses for this company
    assigned_courses = CompanyCourseAssignment.objects.filter(company=company).select_related('course')
    total_assigned_courses = assigned_courses.count()
    
    # Employee progress statistics
    employee_assignments = EmployeeCourseAssignment.objects.filter(
        employee__user__company=company
    )
    
    completed_count = employee_assignments.filter(status='completed').count()
    in_progress_count = employee_assignments.filter(status='in_progress').count()
    assigned_count = employee_assignments.filter(status='assigned').count()
    total_assignments = employee_assignments.count()
    
    completion_rate = (completed_count / total_assignments * 100) if total_assignments > 0 else 0
    
    # Get user groups for this company
    user_groups = CompanyGroup.objects.filter(company=company, is_system=False)
    
    # ========== COURSES WITH ASSIGNMENT INFO ==========
    courses_with_groups = []
    for assignment in assigned_courses:
        course = assignment.course
        
        # Find which groups have this course assigned
        assigned_groups = []
        for group in user_groups:
            # Check if any user in this group is assigned to this course
            users_in_group = group.users.filter(is_disabled=False, role='EMPLOYEE')
            if users_in_group.exists():
                # Check if any of these users have this course assigned
                for user in users_in_group:
                    try:
                        if hasattr(user, 'employee_profile'):
                            if EmployeeCourseAssignment.objects.filter(
                                employee=user.employee_profile,
                                course=course
                            ).exists():
                                assigned_groups.append(group)
                                break
                    except EmployeeProfile.DoesNotExist:
                        continue
        
        # Get employee assignment stats for this course
        course_assignments = EmployeeCourseAssignment.objects.filter(
            employee__user__company=company,
            course=course
        )
        
        courses_with_groups.append({
            'assignment': assignment,
            'course': course,
            'assigned_groups': assigned_groups,
            'total_employees_assigned': course_assignments.count(),
            'completed_count': course_assignments.filter(status='completed').count(),
        })
    
    context = {
        'company': company,
        'total_employees': total_employees,
        'total_assigned_courses': total_assigned_courses,
        'completed_count': completed_count,
        'in_progress_count': in_progress_count,
        'assigned_count': assigned_count,
        'total_assignments': total_assignments,
        'completion_rate': round(completion_rate, 1),
        'courses_with_groups': courses_with_groups,
        'user_groups': user_groups,
    }
    
    return render(request, "account/company_dashboard.html", context)


# ====== ASSIGN COURSE TO GROUP ======
@login_required
def assign_course_to_group(request, course_id):
    if request.user.role != "COMPANY_ADMIN":
        return redirect("account:platform-login")
    
    company = request.user.company
    course = get_object_or_404(Course, id=course_id)
    
    # Check if course is assigned to this company
    if not CompanyCourseAssignment.objects.filter(company=company, course=course).exists():
        messages.error(request, "This course is not assigned to your company.")
        return redirect("account:company-dashboard")
    
    if request.method == 'POST':
        group_ids = request.POST.getlist('groups')
        assigned_count = 0
        
        for group_id in group_ids:
            try:
                group = CompanyGroup.objects.get(id=group_id, company=company)
                
                # IMPORTANT: Create or get the CompanyCourseGroup first
                company_course_group, created = CompanyCourseGroup.objects.get_or_create(
                    company=company,
                    name=f"{course.title} - {group.name}",
                    defaults={
                        'description': f"Course '{course.title}' assigned to group '{group.name}'",
                        'created_by': request.user
                    }
                )
                
                # Add course to the group's courses
                company_course_group.courses.add(course)
                
                # Get all employees in this group
                users_in_group = group.users.filter(is_disabled=False, role='EMPLOYEE')
                
                for user in users_in_group:
                    # Check if employee profile exists, create if not
                    employee_profile, created = EmployeeProfile.objects.get_or_create(
                        user=user,
                        defaults={
                            'employee_id': f"EMP{user.id:04d}",
                            'awareness_score': 0,
                            'total_points': 0
                        }
                    )
                    
                    # Add employee to the group's assigned employees
                    company_course_group.assigned_to_employees.add(employee_profile)
                    
                    # Create assignment WITH company_course_group
                    if not EmployeeCourseAssignment.objects.filter(
                        employee=employee_profile,
                        course=course,
                        company_course_group=company_course_group
                    ).exists():
                        EmployeeCourseAssignment.objects.create(
                            employee=employee_profile,
                            course=course,
                            company_course_group=company_course_group,  # This was missing!
                            assigned_by=request.user,
                            status='assigned'
                        )
                        assigned_count += 1
                        
            except CompanyGroup.DoesNotExist:
                continue
        
        if assigned_count > 0:
            messages.success(request, f"✅ Course assigned to {assigned_count} employees in selected groups.")
        else:
            messages.info(request, "No new assignments were created.")
        
        return redirect("account:company-dashboard")
    
    messages.error(request, "Invalid request method.")
    return redirect("account:company-dashboard")

# ====== COURSE EMPLOYEE PROGRESS ======
@login_required
def course_employee_progress(request, course_id):
    if request.user.role != "COMPANY_ADMIN":
        return redirect("account:platform-login")
    
    company = request.user.company
    course = get_object_or_404(Course, id=course_id)
    
    # Check if course is assigned to this company
    if not CompanyCourseAssignment.objects.filter(company=company, course=course).exists():
        messages.error(request, "This course is not assigned to your company.")
        return redirect("account:company-dashboard")
    
    # Get all employee assignments for this course
    employee_assignments = EmployeeCourseAssignment.objects.filter(
        employee__user__company=company,
        course=course
    ).select_related(
        'employee',
        'employee__user'
    ).order_by('employee__user__last_name', 'employee__user__first_name')
    
    # Get quiz attempts for this course
    quiz_attempts = QuizAttempt.objects.filter(
        quiz__course=course,
        employee__user__company=company
    ).select_related('employee', 'employee__user')
    
    # Organize data by employee
    employees_progress = []
    for assignment in employee_assignments:
        employee = assignment.employee
        
        # Get latest quiz attempt for this employee
        latest_quiz = quiz_attempts.filter(employee=employee).order_by('-started_at').first()
        
        # Get detailed progress if exists
        try:
            detailed_progress = assignment.detailed_progress
        except EmployeeCourseProgress.DoesNotExist:
            detailed_progress = None
        
        employees_progress.append({
            'assignment': assignment,
            'employee': employee,
            'user': employee.user,
            'latest_quiz': latest_quiz,
            'detailed_progress': detailed_progress,
        })
    
    context = {
        'company': company,
        'course': course,
        'employees_progress': employees_progress,
        'total_employees': employee_assignments.count(),
        'completed_count': employee_assignments.filter(status='completed').count(),
        'in_progress_count': employee_assignments.filter(status='in_progress').count(),
        'assigned_count': employee_assignments.filter(status='assigned').count(),
    }
    
    return render(request, "account/course_employee_progress.html", context)

# ==== Employee platform Dashboard ====
@login_required
def employee_dashboard(request):
    if request.user.role != "EMPLOYEE":
        return redirect("account:platform-login")
    
    try:
        # Get employee profile
        employee_profile = EmployeeProfile.objects.get(user=request.user)
        
        # Get all course assignments for this employee
        assignments = EmployeeCourseAssignment.objects.filter(
            employee=employee_profile
        ).select_related('course', 'course__category').order_by('-assigned_at')
        
        # Calculate statistics
        total_courses = assignments.count()
        assigned_count = assignments.filter(status='assigned').count()
        in_progress_count = assignments.filter(status='in_progress').count()
        completed_count = assignments.filter(status='completed').count()
        
        # Calculate completion rate
        if total_courses > 0:
            completion_rate = int((completed_count / total_courses) * 100)
        else:
            completion_rate = 0
        
        context = {
            'total_courses': total_courses,
            'assigned_count': assigned_count,
            'in_progress_count': in_progress_count,
            'completed_count': completed_count,
            'completion_rate': completion_rate,
            'courses': assignments,
            'employee_profile': employee_profile,
        }
        
        return render(request, 'account/employee_dashboard.html', context)
        
    except EmployeeProfile.DoesNotExist:
        messages.error(request, "Employee profile not found. Please contact administrator.")
        return redirect("account:platform-login")

@login_required
def view_course(request, course_id):
    """View a specific course and track progress"""
    if request.user.role != "EMPLOYEE":
        return redirect("account:platform-login")
    
    try:
        employee_profile = EmployeeProfile.objects.get(user=request.user)
        course = get_object_or_404(Course, id=course_id)
        
        # Get or create assignment
        assignment, created = EmployeeCourseAssignment.objects.get_or_create(
            employee=employee_profile,
            course=course,
            defaults={
                'status': 'assigned',
                'assigned_by': request.user,
                'assigned_at': timezone.now()
            }
        )
        
        # Update last accessed time
        assignment.last_accessed = timezone.now()
        assignment.save()
        
        # Calculate time spent (in minutes)
        time_spent_minutes = 0
        if assignment.started_at:
            time_spent = timezone.now() - assignment.started_at
            time_spent_minutes = int(time_spent.total_seconds() / 60)
        
        context = {
            'course': course,
            'assignment': assignment,
            'time_spent_minutes': time_spent_minutes,
            'employee_profile': employee_profile,
        }
        
        return render(request, 'account/view_course.html', context)
        
    except EmployeeProfile.DoesNotExist:
        messages.error(request, "Employee profile not found.")
        return redirect("account:platform-login")

@login_required
def update_course_progress(request, assignment_id):
    """Update course progress via AJAX"""
    if request.user.role != "EMPLOYEE" or request.method != 'POST':
        return JsonResponse({'success': False})
    
    try:
        assignment = EmployeeCourseAssignment.objects.get(
            id=assignment_id,
            employee__user=request.user
        )
        
        data = json.loads(request.body)
        progress = float(data.get('progress', 0))
        
        # Update progress
        assignment.progress_percentage = min(100, max(0, progress))
        assignment.last_accessed = timezone.now()
        
        # Update status based on progress
        if progress >= 100:
            assignment.status = 'completed'
            assignment.completed_at = timezone.now()
        elif progress > 0 and assignment.status == 'assigned':
            assignment.status = 'in_progress'
            if not assignment.started_at:
                assignment.started_at = timezone.now()
        
        assignment.save()
        
        return JsonResponse({'success': True, 'progress': assignment.progress_percentage})
        
    except (EmployeeCourseAssignment.DoesNotExist, EmployeeProfile.DoesNotExist):
        return JsonResponse({'success': False})

@login_required
def mark_course_complete(request, assignment_id):
    """Mark a course as complete"""
    if request.user.role != "EMPLOYEE" or request.method != 'POST':
        return JsonResponse({'success': False})
    
    try:
        assignment = EmployeeCourseAssignment.objects.get(
            id=assignment_id,
            employee__user=request.user
        )
        
        assignment.status = 'completed'
        assignment.progress_percentage = 100
        assignment.completed_at = timezone.now()
        assignment.save()
        
        return JsonResponse({'success': True})
        
    except (EmployeeCourseAssignment.DoesNotExist, EmployeeProfile.DoesNotExist):
        return JsonResponse({'success': False})


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
                return redirect("account:employee_dashboard")

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



@login_required
def company_groups(request):
    if request.user.role != "COMPANY_ADMIN":
        return redirect("account:platform-login")

    company = request.user.company
    # groups = CompanyGroup.objects.filter(company=company)
    groups = CompanyGroup.objects.filter(
    company=company,
    is_system=False
    )

    if request.method == "POST":
        form = CompanyGroupCreateForm(request.POST, company=company)
        if form.is_valid():
            group = form.save(commit=False)
            group.company = company
            group.save()

            for user in form.cleaned_data["users"]:
                group.users.add(user)

            messages.success(request, "Group created successfully.")
            return redirect("account:company-groups")
    else:
        form = CompanyGroupCreateForm(company=company)

    return render(request, "account/company_groups.html", {
        "groups": groups,
        "form": form,
    })


@login_required
def group_detail(request, group_id):
    if request.user.role != "COMPANY_ADMIN":
        return redirect("account:platform-login")

    group = get_object_or_404(
        CompanyGroup,
        id=group_id,
        company=request.user.company
    )

    users = group.users.filter(is_disabled=False)

    add_form = AddUsersToGroupForm(
        company=request.user.company,
        group=group
    )

    return render(request, "account/group_detail.html", {
        "group": group,
        "users": users,
        "add_form": add_form
    })


@login_required
def add_users_to_group(request, group_id):
    if request.user.role != "COMPANY_ADMIN":
        return redirect("account:platform-login")

    group = get_object_or_404(
        CompanyGroup,
        id=group_id,
        company=request.user.company
    )

    form = AddUsersToGroupForm(
        request.POST,
        company=request.user.company,
        group=group
    )

    if form.is_valid():
        for user in form.cleaned_data["users"]:
            group.users.add(user)

        messages.success(request, "Users added to group.")

    return redirect("account:group-detail", group_id=group.id)


@login_required
def remove_user_from_group(request, group_id, user_id):
    if request.user.role != "COMPANY_ADMIN":
        return redirect("account:platform-login")

    group = get_object_or_404(
        CompanyGroup,
        id=group_id,
        company=request.user.company
    )

    if group.is_system:
        messages.error(request, "You cannot modify this group.")
        return redirect("account:group-detail", group_id=group.id)

    user = get_object_or_404(
        User,
        id=user_id,
        company=request.user.company
    )

    group.users.remove(user)
    messages.success(request, "User removed from group.")

    return redirect("account:group-detail", group_id=group.id)



@login_required
def delete_group(request, group_id):
    if request.user.role != "COMPANY_ADMIN":
        return redirect("account:platform-login")

    group = get_object_or_404(
        CompanyGroup,
        id=group_id,
        company=request.user.company
    )

    if group.is_system:
        messages.error(request, "System groups cannot be deleted.")
        return redirect("account:company-groups")

    group.delete()
    messages.success(request, "Group deleted.")

    return redirect("account:company-groups")


@login_required
def group_detail(request, group_id):
    if request.user.role != "COMPANY_ADMIN":
        return redirect("account:platform-login")

    company = request.user.company

    group = get_object_or_404(
        CompanyGroup,
        id=group_id,
        company=company
    )

    # اليوزرز داخل القروب
    group_users = group.users.all()

    # فورم إضافة يوزرز
    add_users_form = AddUsersToGroupForm(
        request.POST or None,
        company=company,
        group=group
    )

    if request.method == "POST" and add_users_form.is_valid():
        group.users.add(*add_users_form.cleaned_data["users"])
        messages.success(request, "Users added to group.")
        return redirect("account:group-detail", group_id=group.id)

    return render(request, "account/group_detail.html", {
        "group": group,
        "group_users": group_users,
        "add_users_form": add_users_form,
    })


@login_required
def remove_user_from_group(request, group_id, user_id):
    if request.user.role != "COMPANY_ADMIN":
        return redirect("account:platform-login")

    company = request.user.company

    group = get_object_or_404(
        CompanyGroup,
        id=group_id,
        company=company
    )

    user = get_object_or_404(
        User,
        id=user_id,
        company=company
    )

    group.users.remove(user)

    messages.success(request, "User removed from group.")
    return redirect("account:group-detail", group_id=group.id)
