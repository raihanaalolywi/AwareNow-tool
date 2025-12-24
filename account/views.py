from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from .forms import CompanyForm, SuperAdminForm, CompanyGroupCreateForm, AddUsersToGroupForm
from django.contrib.auth.decorators import login_required
from django.urls import reverse 
import uuid
from .models import Company, User, CompanyGroup, EmployeeProfile
from .services import send_activation_email
from django.shortcuts import get_object_or_404
from .models import SubscriptionPlan
from django.utils import timezone
from django.db import transaction
from django.contrib import messages
from django.db.models import Count, Q, Avg, Max
from django.http import JsonResponse
import json
from courses.models import CompanyCourseAssignment, Course, EmployeeCourseAssignment, EmployeeCourseProgress, QuizAttempt, CompanyCourseGroup, Quiz, QuizQuestion

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
    assigned_courses = CompanyCourseAssignment.objects.filter(company=company, course__is_active=True).select_related('course')
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
        assigned_groups = CompanyCourseGroup.objects.filter(
            company=company,
            courses=course
        )

        # assigned_groups = []
        # for group in user_groups:
        #     # Check if any user in this group is assigned to this course
        #     users_in_group = group.users.filter(is_disabled=False, role='EMPLOYEE')
        #     if users_in_group.exists():
        #         # Check if any of these users have this course assigned
        #         for user in users_in_group:
        #             try:
        #                 if hasattr(user, 'employee_profile'):
        #                     if EmployeeCourseAssignment.objects.filter(
        #                         employee=user.employee_profile,
        #                         course=course
        #                     ).exists():
        #                         assigned_groups.append(group)
        #                         break
        #             except EmployeeProfile.DoesNotExist:
        #                 continue
        
        # Get employee assignment stats for this course
        course_assignments = EmployeeCourseAssignment.objects.filter(
            employee__user__company=company,
            course=course
        )
        assigned_group_names = set(
            CompanyCourseGroup.objects.filter(
                company=company,
                courses=course
            ).values_list('name', flat=True)
        )

        courses_with_groups.append({
            'assignment': assignment,
            'course': course,
            'assigned_groups': assigned_groups,
            'assigned_group_names': assigned_group_names,
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
    course = get_object_or_404(Course, id=course_id, is_active=True)
    
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
                    name=group.name,
                    defaults={
                        # 'description': f"Course '{course.title}' assigned to group '{group.name}'",
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
            employee=employee_profile, course__is_active=True
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
        course = get_object_or_404(Course, id=course_id, is_active=True)
        
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
        # ✅ NEW LOGIC: start course automatically
        if assignment.status == 'assigned':
            assignment.status = 'in_progress'
            if not assignment.started_at:
                assignment.started_at = timezone.now()
            assignment.save()

        # In your view_course function, add this after getting the assignment:

        # Check if quiz is passed and get attempts
        quiz_passed = False
        quiz_attempts = []

        if hasattr(course, 'quiz') and course.quiz:
            quiz = course.quiz
            # Check if any passed quiz attempts exist
            quiz_passed = QuizAttempt.objects.filter(
                employee=employee_profile,
                quiz=quiz,
                passed=True
            ).exists()
            
            # Get all attempts for this quiz
            quiz_attempts = QuizAttempt.objects.filter(
                employee=employee_profile,
                quiz=quiz
            ).order_by('-attempt_number')

        
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
            'quiz_passed': quiz_passed,  # Add this
            'quiz_attempts': quiz_attempts,  # Add this
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

# In your views.py, update the mark_course_complete function

@login_required
def mark_course_complete(request, assignment_id):
    """Mark a course as complete - requires quiz to be passed"""
    if request.user.role != "EMPLOYEE" or request.method != 'POST':
        return JsonResponse({'success': False})
    
    try:
        assignment = EmployeeCourseAssignment.objects.get(
            id=assignment_id,
            employee__user=request.user
        )
        
        # Check if course has a quiz
        if hasattr(assignment.course, 'quiz') and assignment.course.quiz:
            quiz = assignment.course.quiz
            
            # Check if employee has passed the quiz
            passed_attempt = QuizAttempt.objects.filter(
                employee=assignment.employee,
                quiz=quiz,
                passed=True
            ).exists()
            
            if not passed_attempt:
                return JsonResponse({
                    'success': False,
                    'message': 'You must pass the quiz to complete this course.'
                })
        
        # If no quiz or quiz passed, mark as complete
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
        if user.role == "EMPLOYEE":
            EmployeeProfile.objects.get_or_create(
                user=user,
                defaults={
                    "employee_id": f"EMP{user.id:04d}"
                }
            )


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



@login_required
def start_quiz(request, course_id):
    """Start or continue a quiz for a course"""
    if request.user.role != "EMPLOYEE":
        return redirect("account:platform-login")
    
    try:
        print(f"DEBUG: Starting quiz for course_id={course_id}, user={request.user}")


        employee_profile = EmployeeProfile.objects.get(user=request.user)
        course = get_object_or_404(Course, id=course_id)
        quiz = get_object_or_404(Quiz, course=course, is_active=True)
        
        # Check if employee has access to this course
        assignment = get_object_or_404(
            EmployeeCourseAssignment,
            employee=employee_profile,
            course=course
        )

        print(f"DEBUG: Creating QuizAttempt with quiz={quiz.id}, employee={request.user.id}")

        # Get or create quiz attempt
        last_attempt = QuizAttempt.objects.filter(
            employee=employee_profile,
            quiz=quiz
        ).aggregate(Max('attempt_number'))['attempt_number__max'] or 0
        
        if last_attempt >= quiz.max_attempts:
            messages.error(request, "You have used all your quiz attempts.")
            return redirect('account:view_course', course_id=course_id)
        
        # Check for existing incomplete attempt
        incomplete_attempt = QuizAttempt.objects.filter(
            employee=employee_profile,
            quiz=quiz,
            completed_at__isnull=True
        ).first()
        
        if incomplete_attempt:
            # Continue existing attempt
            attempt = incomplete_attempt
        else:
            # Create new attempt
            attempt_number = last_attempt + 1
            attempt = QuizAttempt.objects.create(
                employee=employee_profile,
                quiz=quiz,
                attempt_number=attempt_number
            )

        print(f"DEBUG: QuizAttempt created with id={attempt.id}")

        return redirect('account:take_quiz', attempt_id=attempt.id)
        
    except Exception as e:
        print(f"ERROR in start_quiz: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Prepare questions with options - UPDATED FOR QuizQuestion
        questions = []
        for question in quiz.questions.all():  # This uses the related_name 'questions'
            options = []
            
            # Build options based on question type
            if question.question_type in ['multiple_choice', 'multiple_select']:
                if question.option_a: options.append(('A', question.option_a))
                if question.option_b: options.append(('B', question.option_b))
                if question.option_c: options.append(('C', question.option_c))
                if question.option_d: options.append(('D', question.option_d))
            elif question.question_type == 'true_false':
                options = [('True', 'True'), ('False', 'False')]
            
            questions.append({
                'id': question.id,
                'question_text': question.question_text,
                'question_type': question.question_type,
                'options': options,
                'points': question.points,
                'order': question.order,
                'explanation': question.explanation,
            })
        
        context = {
            'course': course,
            'quiz': quiz,
            'attempt': attempt,
            'attempt_number': attempt.attempt_number,
            'questions': questions,
            'assignment': assignment,
            'time_limit': quiz.time_limit_minutes * 60 if quiz.time_limit_minutes > 0 else 0,
        }
        
        return render(request, 'account/take_quiz.html', context)
        
    except (EmployeeProfile.DoesNotExist, Quiz.DoesNotExist) as e:
        messages.error(request, "Quiz not available.")
        return redirect('account:employee_dashboard')
    

@login_required
def submit_quiz(request, attempt_id):
    """Submit and grade a quiz attempt"""
    if request.user.role != "EMPLOYEE" or request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request'})
    
    try:
        attempt = get_object_or_404(
            QuizAttempt,
            id=attempt_id,
            employee__user=request.user,
            completed_at__isnull=True
        )
        
        # Calculate time taken
        time_taken = (timezone.now() - attempt.started_at).total_seconds()
        
        # Grade the quiz
        total_points = 0
        earned_points = 0
        answers_data = {}
        
        for question in attempt.quiz.questions.all():  # This is QuizQuestion
            total_points += question.points
            
            # Get user's answer
            answer_key = f'question_{question.id}'
            if question.question_type == 'multiple_select':
                # For multiple select, get all checked values
                user_answer = request.POST.getlist(answer_key)
                user_answer_str = ','.join(sorted(user_answer)) if user_answer else ''
            else:
                # For single answer types
                user_answer = request.POST.get(answer_key, '')
                user_answer_str = user_answer
            
            # Store answer in JSON format
            answers_data[str(question.id)] = {
                'question_id': question.id,
                'question_text': question.question_text[:100],
                'user_answer': user_answer_str,
                'correct_answers': question.correct_answers,
                'question_type': question.question_type,
            }
            
            # Check if answer is correct
            correct_answers = [a.strip().upper() for a in question.correct_answers.split(',')]
            user_answers = [a.strip().upper() for a in user_answer_str.split(',') if a.strip()]
            
            if question.question_type == 'multiple_select':
                # For multiple select, all correct answers must be selected, no extra answers
                if set(user_answers) == set(correct_answers):
                    earned_points += question.points
            else:
                # For single answer types
                if user_answers and user_answers[0] in correct_answers:
                    earned_points += question.points
        
        # Calculate score percentage
        score_percentage = (earned_points / total_points * 100) if total_points > 0 else 0
        
        # Update attempt
        attempt.score = score_percentage
        attempt.passed = score_percentage >= attempt.quiz.passing_score
        attempt.completed_at = timezone.now()
        attempt.time_taken_seconds = int(time_taken)
        attempt.answers_data = answers_data
        attempt.save()
        # ✅ Mark course as completed after submitting quiz (regardless of pass/fail)
        assignment = EmployeeCourseAssignment.objects.get(
            employee=attempt.employee,
            course=attempt.quiz.course
        )

        assignment.status = 'completed'
        assignment.progress_percentage = 100
        assignment.completed_at = timezone.now()
        assignment.save()


        return redirect('account:quiz_result', attempt_id=attempt.id)

        # return JsonResponse({
        #     'success': True,
        #     'score': round(score_percentage, 1),
        #     'passed': attempt.passed,
        #     'passing_score': attempt.quiz.passing_score,
        #     'redirect_url': reverse('account:quiz_result', args=[attempt.id])
        # })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
    
@login_required
def quiz_result(request, attempt_id):
    """Show quiz results"""
    if request.user.role != "EMPLOYEE":
        return redirect("account:platform-login")
    
    try:
        attempt = get_object_or_404(
            QuizAttempt,
            id=attempt_id,
            employee__user=request.user
        )
        
        # Get detailed results from answers_data JSON
        results = []
        for question in attempt.quiz.questions.all():
            question_data = attempt.answers_data.get(str(question.id), {})
            user_answer = question_data.get('user_answer', '')
            correct_answers = [a.strip() for a in question.correct_answers.split(',')]
            
            # Check if answer is correct
            user_answers = [a.strip() for a in user_answer.split(',') if a.strip()]
            is_correct = False
            
            if question.question_type == 'multiple_select':
                is_correct = set(user_answers) == set(correct_answers)
            else:
                is_correct = user_answers and user_answers[0] in correct_answers
            
            # Get answer options
            options = []
            if question.question_type in ['multiple_choice', 'multiple_select']:
                if question.option_a: options.append({'label': 'A', 'text': question.option_a})
                if question.option_b: options.append({'label': 'B', 'text': question.option_b})
                if question.option_c: options.append({'label': 'C', 'text': question.option_c})
                if question.option_d: options.append({'label': 'D', 'text': question.option_d})
            
            results.append({
                'question': question,
                'user_answer': user_answer,
                'correct_answers': correct_answers,
                'is_correct': is_correct,
                'points': question.points if is_correct else 0,
                'options': options,
                'explanation': question.explanation,
            })
        
        context = {
            'attempt': attempt,
            'quiz': attempt.quiz,
            'course': attempt.quiz.course,
            'results': results,
            'time_taken_minutes': attempt.time_taken_seconds // 60,
            'time_taken_seconds': attempt.time_taken_seconds % 60,
        }
        
        return render(request, 'account/quiz_result.html', context)
        
    except QuizAttempt.DoesNotExist:
        messages.error(request, "Quiz attempt not found.")
        return redirect('account:employee_dashboard')
    
@login_required
def take_quiz(request, attempt_id):
    """Display the quiz questions"""
    if request.user.role != "EMPLOYEE":
        return redirect("account:platform-login")
    
    try:
        employee_profile = EmployeeProfile.objects.get(user=request.user)
        attempt = get_object_or_404(
            QuizAttempt,
            id=attempt_id,
            employee=employee_profile
        )
        
        # Check if already completed
        if attempt.completed_at is not None:
            messages.info(request, "This quiz has already been completed.")
            return redirect('account:quiz_result', attempt_id=attempt.id)
        
        quiz = attempt.quiz
        course = quiz.course
        
        # Check assignment
        assignment = get_object_or_404(
            EmployeeCourseAssignment,
            employee=employee_profile,
            course=course
        )
        
        # Prepare questions
        questions = []
        for question in quiz.questions.all():
            options = []
            
            if question.question_type in ['multiple_choice', 'multiple_select']:
                if question.option_a: options.append(('A', question.option_a))
                if question.option_b: options.append(('B', question.option_b))
                if question.option_c: options.append(('C', question.option_c))
                if question.option_d: options.append(('D', question.option_d))
            elif question.question_type == 'true_false':
                options = [('True', 'True'), ('False', 'False')]
            
            questions.append({
                'id': question.id,
                'question_text': question.question_text,
                'question_type': question.question_type,
                'options': options,
                'points': question.points,
                'order': question.order,
                'explanation': question.explanation,
            })
        
        context = {
            'course': course,
            'quiz': quiz,
            'attempt': attempt,
            'attempt_number': attempt.attempt_number,
            'questions': questions,
            'assignment': assignment,
            'time_limit': quiz.time_limit_minutes * 60 if quiz.time_limit_minutes > 0 else 0,
        }
        
        return render(request, 'account/take_quiz.html', context)
        
    except Exception as e:
        print(f"Error in take_quiz: {e}")
        messages.error(request, "Error loading quiz.")
        return redirect('account:employee_dashboard')
    
def password_checker(request):
    """Render the password strength checker page"""
    
    return render(request, 'account/password_checker.html')