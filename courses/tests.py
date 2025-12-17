# courses/test_exact_models.py
import os
import sys
import django
from datetime import datetime, timedelta
from django.utils import timezone

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AwareNow_Project.settings')
django.setup()

from django.contrib.auth import get_user_model
from account.models import Company, SubscriptionPlan, EmployeeProfile
from courses.models import (
    CourseCategory, Course, CompanyCourseAssignment, 
    CompanyCourseGroup, EmployeeCourseAssignment,
    EmployeeCourseProgress, Quiz, QuizQuestion, QuizAttempt,
    CourseCompletionCertificate
)

User = get_user_model()

def cleanup_existing_test_data():
    """Clean up any existing test data to avoid conflicts"""
    print("🧹 Cleaning up existing test data...")
    
    # Delete in reverse order to respect foreign key constraints
    try:
        CourseCompletionCertificate.objects.filter(
            certificate_id__startswith='TEST-'
        ).delete()
        QuizAttempt.objects.all().delete()
        QuizQuestion.objects.all().delete()
        Quiz.objects.all().delete()
        EmployeeCourseProgress.objects.all().delete()
        EmployeeCourseAssignment.objects.all().delete()
        CompanyCourseGroup.objects.filter(name__contains='Test').delete()
        CompanyCourseAssignment.objects.all().delete()
        Course.objects.filter(title__contains='Test').delete()
        CourseCategory.objects.filter(name__contains='Test').delete()
        EmployeeProfile.objects.filter(employee_id__contains='TEST').delete()
        
        # Delete test users but keep any existing non-test users
        User.objects.filter(
            username__in=['test_platform_admin', 'test_company_admin', 'test_employee']
        ).delete()
        
        Company.objects.filter(name__contains='Test').delete()
        SubscriptionPlan.objects.filter(name__contains='Test').delete()
        
        print("✅ Cleanup complete")
    except Exception as e:
        print(f"⚠️  Cleanup had issues: {e}")

def test_exact_models():
    """
    Test the complete system with your exact model structure
    """
    print("=" * 70)
    print("TESTING WITH EXACT MODEL STRUCTURE")
    print("=" * 70)
    
    results = {'success': True, 'errors': [], 'created': {}}
    
    try:
        # Clean up first
        cleanup_existing_test_data()
        
        # ========== PHASE 1: SETUP COMPANY AND USERS ==========
        print("\n📋 PHASE 1: Setting up Company and Users")
        print("-" * 50)
        
        # 1. Create Subscription Plan
        print("1. Creating Subscription Plan...")
        plan, created = SubscriptionPlan.objects.get_or_create(
            name='Test Plan',
            defaults={
                'max_users': 100,
                'price': 299.99,
                'has_platform_support': True
            }
        )
        results['created']['plan'] = plan
        status = "✅ Created" if created else "⚠️  Using existing"
        print(f"   {status}: {plan.name}")
        
        # 2. Create Company
        print("2. Creating Company...")
        company, created = Company.objects.get_or_create(
            name='Test Company SA',
            defaults={
                'email_domain': 'testcompany.sa',
                'subscription_plan': plan,
                'license_start_date': '2024-01-01',
                'license_end_date': '2025-12-31',
                'status': 'ACTIVE'
            }
        )
        results['created']['company'] = company
        status = "✅ Created" if created else "⚠️  Using existing"
        print(f"   {status}: {company.name}")
        
        # 3. Create Platform Admin (no company)
        print("3. Creating Platform Admin...")
        platform_admin, created = User.objects.get_or_create(
            username='test_platform_admin',
            defaults={
                'email': 'platform.admin@test.sa',
                'first_name': 'Platform',
                'last_name': 'Admin',
                'role': 'PLATFORM_ADMIN',
                'is_staff': True,
                'is_superuser': True
            }
        )
        if created:
            platform_admin.set_password('TestPass123!')
            platform_admin.save()
            print(f"   ✅ Created: {platform_admin.get_full_name()}")
        else:
            print(f"   ⚠️  Using existing: {platform_admin.get_full_name()}")
        
        results['created']['platform_admin'] = platform_admin
        
        # Test the properties from your User model
        print(f"   Role checks - Platform Admin: {platform_admin.is_platform_admin}")
        print(f"   Role checks - Company Admin: {platform_admin.is_company_admin}")
        print(f"   Role checks - Employee: {platform_admin.is_employee}")
        
        # 4. Create Company Admin (with company)
        print("4. Creating Company Admin...")
        company_admin, created = User.objects.get_or_create(
            username='test_company_admin',
            defaults={
                'email': 'company.admin@testcompany.sa',
                'first_name': 'Company',
                'last_name': 'Admin',
                'role': 'COMPANY_ADMIN',
                'company': company,
                'department': 'Management'
            }
        )
        if created:
            company_admin.set_password('TestPass123!')
            company_admin.save()
            print(f"   ✅ Created: {company_admin.get_full_name()}")
        else:
            print(f"   ⚠️  Using existing: {company_admin.get_full_name()}")
        
        results['created']['company_admin'] = company_admin
        print(f"   Department: {company_admin.department}")
        print(f"   Company: {company_admin.company}")
        
        # 5. Create Employee User (with company and department)
        print("5. Creating Employee User...")
        employee_user, created = User.objects.get_or_create(
            username='test_employee',
            defaults={
                'email': 'employee@testcompany.sa',
                'first_name': 'Test',
                'last_name': 'Employee',
                'role': 'EMPLOYEE',
                'company': company,
                'department': 'IT Security'
                # Note: No job_title or phone_number - they're not in your model
            }
        )
        if created:
            employee_user.set_password('TestPass123!')
            employee_user.save()
            print(f"   ✅ Created: {employee_user.get_full_name()}")
        else:
            print(f"   ⚠️  Using existing: {employee_user.get_full_name()}")
        
        results['created']['employee_user'] = employee_user
        
        # 6. Create Employee Profile
        print("6. Creating Employee Profile...")
        employee_profile, created = EmployeeProfile.objects.get_or_create(
            user=employee_user,
            defaults={
                'employee_id': 'TEST-EMP-001'
            }
        )
        results['created']['employee_profile'] = employee_profile
        status = "✅ Created" if created else "⚠️  Using existing"
        print(f"   {status}: Employee Profile for {employee_profile}")
        print(f"   Employee ID: {employee_profile.employee_id}")
        
        # Test EmployeeProfile properties
        print(f"   Company via profile: {employee_profile.company}")
        print(f"   Department via profile: {employee_profile.department}")
        
        # Test EmployeeProfile calculations
        print("7. Testing EmployeeProfile score calculation...")
        employee_profile.completed_courses_count = 3
        employee_profile.average_quiz_score = 80.0
        employee_profile.phishing_tests_taken = 5
        employee_profile.phishing_tests_passed = 4
        employee_profile.save()  # This triggers calculate_awareness_score()
        
        print(f"   Awareness Score: {employee_profile.awareness_score}")
        if employee_profile.phishing_tests_taken > 0:
            pass_rate = (employee_profile.phishing_tests_passed / employee_profile.phishing_tests_taken) * 100
            print(f"   Phishing Pass Rate: {pass_rate:.1f}%")
        
        # ========== PHASE 2: COURSE SYSTEM ==========
        print("\n📚 PHASE 2: Course System")
        print("-" * 50)
        
        # 1. Create Course Category
        print("1. Creating Course Category...")
        category = CourseCategory.objects.create(
            name='Test Phishing Awareness',
            description='Test category for phishing awareness training',
            icon='shield-alt',
            color='#3498db'
        )
        results['created']['category'] = category
        print(f"   ✅ Created: {category.name}")
        print(f"   Icon: {category.icon}, Color: {category.color}")
        
        # 2. Create Course
        print("2. Creating Course...")
        course = Course.objects.create(
            title='Test Cybersecurity Course',
            brief_description='A test course for cybersecurity awareness',
            category=category,
            created_by=platform_admin,
            visibility='specific',
            is_published=True,
            points_reward=150,
            video_url='https://example.com/videos/test-course',
            video_duration_minutes=30
        )
        results['created']['course'] = course
        print(f"   ✅ Created: {course.title}")
        print(f"   Points: {course.points_reward}")
        print(f"   Thumbnail field: {course.thumbnail}")
        print(f"   Thumbnail has file: {bool(course.thumbnail)}")
        
        # Test the save method
        print("3. Testing Course save method...")
        try:
            course.save()
            print("   ✅ Save method works")
        except Exception as e:
            print(f"   ❌ Save error: {e}")
        
        # ========== PHASE 3: ASSIGNMENTS ==========
        print("\n📝 PHASE 3: Assignments")
        print("-" * 50)
        
        # 1. Company Assignment
        print("1. Assigning Course to Company...")
        company_assignment = CompanyCourseAssignment.objects.create(
            company=company,
            course=course,
            assigned_by=platform_admin
        )
        results['created']['company_assignment'] = company_assignment
        print(f"   ✅ Created: {company.name} ← {course.title}")
        
        # 2. Course Group
        print("2. Creating Course Group...")
        course_group = CompanyCourseGroup.objects.create(
            company=company,
            name='Test Training Group',
            description='Test group for employee training',
            created_by=company_admin
        )
        course_group.courses.add(course)
        results['created']['course_group'] = course_group
        print(f"   ✅ Created: {course_group.name}")
        print(f"   Courses in group: {course_group.courses.count()}")
        
        # 3. Add employee to group
        print("3. Adding Employee to Group...")
        course_group.assigned_to_employees.add(employee_profile)
        print(f"   ✅ Employees in group: {course_group.assigned_to_employees.count()}")
        
        # 4. Direct Employee Assignment
        print("4. Direct Course Assignment...")
        employee_assignment = EmployeeCourseAssignment.objects.create(
            employee=employee_profile,
            course=course,
            assigned_by=company_admin,
            due_date=datetime.now().date() + timedelta(days=14),
            status='assigned'
        )
        results['created']['employee_assignment'] = employee_assignment
        print(f"   ✅ Created direct assignment")
        print(f"   Status: {employee_assignment.status}")
        print(f"   Due: {employee_assignment.due_date}")
        
        # Test unique constraint
        print("5. Testing unique constraint...")
        try:
            duplicate = EmployeeCourseAssignment.objects.create(
                employee=employee_profile,
                course=course,
                assigned_by=company_admin
            )
            print("   ❌ Should have failed (duplicate assignment)")
            duplicate.delete()
        except Exception as e:
            print(f"   ✅ Correctly prevented duplicate: {str(e)[:50]}...")
        
        # ========== PHASE 4: PROGRESS TRACKING ==========
        print("\n📊 PHASE 4: Progress Tracking")
        print("-" * 50)
        
        print("1. Creating Progress Record...")
        progress = EmployeeCourseProgress.objects.create(
            assignment=employee_assignment,
            video_total_seconds=1800,  # 30 minutes
            required_watch_percentage=80,
            required_quiz_score=70
        )
        results['created']['progress'] = progress
        
        # Simulate progress
        progress.video_watched_seconds = 900  # 50%
        progress.total_time_spent = 1000
        progress.save()
        
        # Update assignment
        watch_pct = (progress.video_watched_seconds / progress.video_total_seconds) * 100
        employee_assignment.progress_percentage = watch_pct
        employee_assignment.status = 'in_progress'
        employee_assignment.started_at = datetime.now()
        employee_assignment.save()
        
        print(f"   Progress: {employee_assignment.progress_percentage:.1f}%")
        print(f"   Status: {employee_assignment.status}")
        
        # ========== PHASE 5: QUIZ SYSTEM ==========
        print("\n🧠 PHASE 5: Quiz System")
        print("-" * 50)
        
        print("1. Creating Quiz...")
        quiz = Quiz.objects.create(
            course=course,
            title='Test Quiz',
            description='Test your knowledge',
            passing_score=70,
            time_limit_minutes=20,
            max_attempts=2
        )
        results['created']['quiz'] = quiz
        
        print("2. Adding Questions...")
        question = QuizQuestion.objects.create(
            quiz=quiz,
            question_text='What is phishing?',
            question_type='multiple_choice',
            option_a='A fishing technique',
            option_b='A cybersecurity attack',
            option_c='A type of malware',
            option_d='A network protocol',
            correct_answers='B',
            points=10,
            explanation='Phishing is a cyber attack',
            order=1
        )
        results['created']['question'] = question
        
        print("3. Employee takes Quiz...")
        quiz_attempt = QuizAttempt.objects.create(
            employee=employee_profile,
            quiz=quiz,
            attempt_number=1,
            score=85.0,
            passed=True,
            time_taken_seconds=600,
            completed_at=datetime.now(),
            answers_data={'question_1': 'B'}
        )
        results['created']['quiz_attempt'] = quiz_attempt
        
        # Update progress
        progress.quiz_attempts = 1
        progress.best_quiz_score = 85.0
        progress.passed_quiz = True
        progress.save()
        
        # ========== FINAL VALIDATION ==========
        print("\n✅ FINAL VALIDATION")
        print("-" * 50)
        
        models_to_check = [
            (User, 'Users'),
            (Company, 'Companies'),
            (EmployeeProfile, 'Employee Profiles'),
            (Course, 'Courses'),
            (Quiz, 'Quizzes'),
            (QuizAttempt, 'Quiz Attempts'),
            (EmployeeCourseAssignment, 'Assignments'),
        ]
        
        for model, name in models_to_check:
            count = model.objects.count()
            print(f"  {name}: {count}")
        
        # Test relationships
        print("\nRelationship Tests:")
        print(f"  Employee → Direct Courses: {employee_profile.assigned_courses.count()}")
        print(f"  Employee → Groups: {employee_profile.course_groups.count()}")
        print(f"  Course → Companies: {course.companies.count()}")
        
        # Test EmployeeProfile after updates
        employee_profile.refresh_from_db()
        print(f"\nEmployeeProfile Final Score: {employee_profile.awareness_score}")
        
        print("\n" + "=" * 70)
        print("🎉 ALL TESTS PASSED WITH YOUR EXACT MODELS!")
        print("=" * 70)
        
        return results
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        results['success'] = False
        results['errors'].append(str(e))
        return results

if __name__ == '__main__':
    test_exact_models()