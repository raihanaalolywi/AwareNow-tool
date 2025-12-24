# courses/test_exact_models.py
import os
import sys
import django
from datetime import datetime, timedelta

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
            platform_admin.set_password('123')
            platform_admin.save()
            print(f"   ✅ Created: {platform_admin.get_full_name()}")
        else:
            print(f"   ⚠️  Using existing: {platform_admin.get_full_name()}")
        
        results['created']['platform_admin'] = platform_admin
        
        # Test the properties from your User model
        print(f"   Role checks - Platform Admin: {platform_admin.is_platform_admin}")
        print(f"   Role checks - Company Admin: {platform_admin.is_company_admin}")
        print(f"   Role checks - Employee: {platform_admin.is_employee}")
        
 
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        results['success'] = False
        results['errors'].append(str(e))
        return results

if __name__ == '__main__':
    test_exact_models()