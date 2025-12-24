from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponseForbidden
from django.db.models import Avg, Count, Q

import json
from django.utils import timezone
from django.db.models import Max

# Remove: from datetime import datetime, timedelta  # Don't need datetime anymore
from account.models import Company, EmployeeProfile
from .models import Course, CourseCategory, CompanyCourseAssignment, EmployeeCourseAssignment, QuizAttempt
from .forms import CourseForm, CourseCategoryForm
from django.http import JsonResponse





# ==================== PERMISSION CHECK ====================
def platform_admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('account:platform-login')
        
        # if not (request.user.is_platform_admin or request.user.is_superuser):
        #     return HttpResponseForbidden("Access denied. Platform admin privileges required.")
        if not request.user.is_superuser:
            return HttpResponseForbidden("Platform admin only.")

        return view_func(request, *args, **kwargs)
    return wrapper

# ==================== SIMPLIFIED DASHBOARD ====================
@login_required
@platform_admin_required
def platform_admin_dashboard(request):
    # ========== BASIC COURSE STATS ==========
    total_courses = Course.objects.count()
    published_courses = Course.objects.filter(is_published=True).count()
    total_companies = Company.objects.filter(status='ACTIVE').count()
    
    recent_courses = Course.objects.filter(created_by=request.user).order_by('-created_at')[:5]
    
    # ========== SIMPLE EMPLOYEE PROGRESS ==========
    assigned_count = EmployeeCourseAssignment.objects.filter(status='assigned').count()
    in_progress_count = EmployeeCourseAssignment.objects.filter(status='in_progress').count()
    completed_count = EmployeeCourseAssignment.objects.filter(status='completed').count()
    total_assignments = EmployeeCourseAssignment.objects.count()
    
    completion_rate = (completed_count / total_assignments * 100) if total_assignments > 0 else 0
    
    # FIXED: Use timezone.now() instead of datetime.now()
    overdue_count = EmployeeCourseAssignment.objects.filter(
        due_date__lt=timezone.now().date(),  # FIXED HERE
        status__in=['assigned', 'in_progress']
    ).count()
    
    # ========== COMPANY SUMMARY ==========
    companies = Company.objects.filter(status='ACTIVE')[:5]
    company_summary = []
    
    for company in companies:
        # employees_count = EmployeeProfile.objects.filter(company=company).count()
        employees_count = EmployeeProfile.objects.filter( user__company=company).count()
        # completed_in_company = EmployeeCourseAssignment.objects.filter(
        #     employee__company=company,
        #     status='completed'
        # ).count()
        completed_in_company = EmployeeCourseAssignment.objects.filter(
            employee__user__company=company,
            status='completed'
        ).count()

        
        company_summary.append({
            'name': company.name,
            'employee_count': employees_count,
            'completed_courses': completed_in_company,
        })
    
    # ========== RECENT COMPLETIONS ==========
    recent_completions = EmployeeCourseAssignment.objects.filter(
        status='completed'
    ).select_related(
        # 'employee__user',
        # 'employee__company',
        # 'course'

        # 'employee__user__company',
        # 'course'
        'employee',
        'employee__user',
        'course'
    ).order_by('-completed_at')[:10]
    
    simple_completions = []
    for assignment in recent_completions:
        simple_completions.append({
            'employee_email': assignment.employee.user.email,
            'company': assignment.employee.company.name if assignment.employee.company else 'N/A',
            'course': assignment.course.title,
            'completed_date': assignment.completed_at.date() if assignment.completed_at else 'N/A',
        })
    
    # ========== OVERDUE LIST (SIMPLE) ==========
    # FIXED: Use timezone.now() here too
    overdue_list = EmployeeCourseAssignment.objects.filter(
        due_date__lt=timezone.now().date(),  # FIXED HERE
        status__in=['assigned', 'in_progress']
    ).select_related(
        # 'employee__user',
        # 'employee__company',
        # 'course'
        'employee',
        'employee__user',
        'course'
    )[:5]
    
    # ========== QUIZ PERFORMANCE ==========
    quiz_stats = QuizAttempt.objects.aggregate(
        avg_score=Avg('score'),
        total_attempts=Count('id')
    )
    
    return render(request, 'courses/dashboard.html', {
        # Basic stats
        'total_courses': total_courses,
        'published_courses': published_courses,
        'total_companies': total_companies,
        'recent_courses': recent_courses,
        # REMOVED: 'user': request.user,  # Not needed
        
        # Simple progress stats
        'assigned_count': assigned_count,
        'in_progress_count': in_progress_count,
        'completed_count': completed_count,
        'total_assignments': total_assignments,
        'completion_rate': round(completion_rate, 1),
        'overdue_count': overdue_count,
        
        # Company summary
        'company_summary': company_summary,
        
        # Recent completions
        'recent_completions': simple_completions,
        
        # Overdue list
        'overdue_list': overdue_list,
        
        # Quiz stats - IMPROVED: Use .get() for safety
        'avg_quiz_score': round(quiz_stats.get('avg_score') or 0, 1),
        'total_quiz_attempts': quiz_stats.get('total_attempts') or 0,
    })

# ==================== COURSE CREATION ====================
@login_required
@platform_admin_required
def create_course(request):
    courses = Course.objects.all().order_by('-created_at')

    today = timezone.now().date()
    all_companies = Company.objects.filter(
        license_end_date__gte=today
    ).order_by('name')

    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES)

        if form.is_valid():
            course = form.save(commit=False)
            course.created_by = request.user
            visibility = request.POST.get('visibility')

            # Draft
            if visibility == 'private':
                course.is_published = False
                course.is_active = True
                course.published_at = None

            # Published
            elif visibility in ['global', 'specific']:
                course.is_published = True
                course.is_active = True
                course.published_at = timezone.now()

            course.points_reward = 100
            course.visibility = visibility
            course.save()

            # ✅ NEW: assignment logic
            today = timezone.now().date()
            if visibility == 'global':
                companies = Company.objects.filter(status='ACTIVE', license_end_date__gte=today)
                for company in companies:
                    CompanyCourseAssignment.objects.get_or_create(
                        company=company,
                        course=course,
                        defaults={'assigned_by': request.user}
                    )

            elif visibility == 'specific':
                company_ids = request.POST.getlist('companies')  
                companies = Company.objects.filter(
                    id__in=company_ids,
                    status='ACTIVE',
                    license_end_date__gte=today
                )
                for company in companies:
                    CompanyCourseAssignment.objects.get_or_create(
                        company=company,
                        course=course,
                        defaults={'assigned_by': request.user}
                    )

            messages.success(request, f'✅ Course "{course.title}" created!')

            # ➜ Specific companies → assign step
            # if visibility == 'specific':
            #     return redirect(
            #         'courses:assign_course_to_companies',
            #         course_id=course.id
            #     )

            return redirect('courses:courses_dashboard')

    else:
        form = CourseForm()

    return render(request, 'courses/create_course.html', {
        'form': form,
        'is_edit': False,
        'all_companies': all_companies,
    })

# ==================== COURSE EDITING ====================
@login_required
@platform_admin_required
def edit_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    
    today = timezone.now().date()

    all_companies = Company.objects.filter(
        license_end_date__gte=today
    ).order_by('name')

    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES, instance=course)

        if form.is_valid():
            updated_course = form.save(commit=False)

            visibility = request.POST.get('visibility')

            # 🚫 ممنوع الرجوع Draft إذا كان Published
            if course.is_published and visibility == 'private':
                messages.error(request, "❌ You cannot move a published course back to draft.")
                return redirect('courses:courses_dashboard')

            if visibility == 'private':
                updated_course.is_published = False
                updated_course.published_at = None

            elif visibility in ['global', 'specific']:
                updated_course.is_published = True
                if not updated_course.published_at:
                    updated_course.published_at = timezone.now()

            updated_course.save()

            messages.success(request, f'✅ Course "{updated_course.title}" updated!')
            return redirect('courses:courses_dashboard')

    else:
        form = CourseForm(instance=course)

    return render(request, 'courses/create_course.html', {
        'form': form,
        'course': course,
        'is_edit': True,
        'all_companies': all_companies,
    })

@login_required
@platform_admin_required
def deactivate_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    course.is_active = False
    course.save()

    messages.success(request, f'Course "{course.title}" deactivated.')
    return redirect('courses:courses_dashboard')


@login_required
@platform_admin_required
def activate_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    course.is_active = True
    course.save()

    messages.success(request, f'Course "{course.title}" activated.')
    return redirect('courses:courses_dashboard')

@login_required
@platform_admin_required
def courses_dashboard(request):
    # Get all courses
    courses = Course.objects.all().order_by('-created_at')
    total_courses = courses.count()
    
    # Get categories with course counts
    categories = CourseCategory.objects.annotate(
        course_count=Count('course')
    )
    
    # Apply filters if provided
    status_filter = request.GET.get('status')
    category_filter = request.GET.get('category')
    
    if status_filter:
        if status_filter == 'published':
            courses = courses.filter(is_published=True)
        elif status_filter == 'draft':
            courses = courses.filter(is_published=False)
    
    if category_filter:
        courses = courses.filter(category_id=category_filter)
    
    return render(request, 'courses/courses_dashboard.html', {
        'courses': courses,
        'categories': categories,
        'total_courses': total_courses
    })

# ==================== COURSE ASSIGNMENT ====================
# @login_required
# @platform_admin_required
# def assign_course_to_companies(request, course_id):
#     course = get_object_or_404(Course, id=course_id)
    
#     if request.method == 'POST':
#         company_ids = request.POST.getlist('companies')
#         assigned_count = 0
        
#         for company_id in company_ids:
#             try:
#                 company = Company.objects.get(id=company_id, status='ACTIVE')
                
#                 if not CompanyCourseAssignment.objects.filter(
#                     company=company, course=course
#                 ).exists():
#                     CompanyCourseAssignment.objects.create(
#                         company=company,
#                         course=course,
#                         assigned_by=request.user
#                     )
#                     assigned_count += 1
                    
#             except Company.DoesNotExist:
#                 continue
        
#         if assigned_count > 0:
#             messages.success(request, f'✅ Course assigned to {assigned_count} company(s)')
#         else:
#             messages.info(request, 'No new companies assigned.')
        
#         return redirect('courses:platform_admin_dashboard')
    
#     all_companies = Company.objects.filter(status='ACTIVE').order_by('name')
#     already_assigned = course.companies.values_list('id', flat=True)
    
#     return render(request, 'courses/assign_course.html', {
#         'course': course,
#         'all_companies': all_companies,
#         'already_assigned': list(already_assigned),
#         # REMOVED: 'user': request.user,  # Not needed
#     })

# from django.http import JsonResponse

@login_required
@platform_admin_required
def course_companies_view(request, course_id):
    course = get_object_or_404(Course, id=course_id)


    today = timezone.now().date()

    companies = list(
        course.companies.filter(
            license_end_date__gte=today
        ).values_list('name', flat=True)
    )

    return JsonResponse({
        'companies': companies
    })


# views.py
@login_required
def create_category(request):
    """Create a new category - admin only"""
    if not request.user.is_platform_admin:
        messages.error(request, "Access denied. Platform admin privileges required.")
        return redirect('home')
    
    if request.method == 'POST':
        form = CourseCategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Category "{category.name}" created successfully!')
            return redirect('courses:categories_list')
    else:
        form = CourseCategoryForm()
    
    # Get all existing categories for the sidebar
    categories = CourseCategory.objects.all()
    
    context = {
        'form': form,
        'categories': categories,
    }
    
    return render(request, 'courses/category_form.html', context)

@login_required
def update_category(request, pk):
    """Update a category - admin only"""
    if not request.user.is_platform_admin:
        messages.error(request, "Access denied. Platform admin privileges required.")
        return redirect('home')
    
    category = get_object_or_404(CourseCategory, pk=pk)
    
    if request.method == 'POST':
        form = CourseCategoryForm(request.POST, instance=category)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Category "{category.name}" updated successfully!')
            return redirect('courses:categories_list')
    else:
        form = CourseCategoryForm(instance=category)
    
    # Get all existing categories for the sidebar
    categories = CourseCategory.objects.all()
    
    context = {
        'form': form,
        'category': category,
        'categories': categories,
    }
    
    return render(request, 'courses/category_form.html', context)

# views.py
@login_required
def delete_category(request, pk):
    """Delete a category - admin only"""
    if not request.user.is_platform_admin:
        messages.error(request, "Access denied. Platform admin privileges required.")
        return redirect('home')
    
    category = get_object_or_404(CourseCategory, pk=pk)
    
    # Get course count for warning message
    course_count = category.course_set.count()
    
    if request.method == 'POST':
        name = category.name
        category.delete()
        messages.success(request, f'Category "{name}" deleted successfully!')
        return redirect('courses:categories_list')
    
    context = {
        'category': category,
        'course_count': course_count,  # Pass to template
    }
    
    return render(request, 'courses/category_confirm_delete.html', context)

@login_required
def category_list(request):
    # Check if user is platform admin
    if not request.user.is_platform_admin:
        messages.error(request, "Access denied. Platform admin privileges required.")
        return redirect('account:platform-login')
    
    categories = CourseCategory.objects.all()
    return render(request, 'courses/categories_list.html', {'categories': categories})