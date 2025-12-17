from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator

# ==== Contract Model => 3 contract saved in DB ====
class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=50)
    max_users = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    has_platform_support = models.BooleanField(default=False)

    def __str__(self):
        return self.name

# ==== Company Model ====
class Company(models.Model):
    name = models.CharField(max_length=255)
    email_domain = models.CharField(max_length=255)

    subscription_plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT
    )

    license_start_date = models.DateField()
    license_end_date = models.DateField()

    status = models.CharField(
        max_length=20,
        choices=(
            ('ACTIVE', 'Active'),
            ('EXPIRED', 'Expired'),
            ('SUSPENDED', 'Suspended'),
        ),
        default='ACTIVE'
    )

    def __str__(self):
        return self.name

# ==== User Model ====
class User(AbstractUser):
    ROLE_CHOICES = (
        ('PLATFORM_ADMIN', 'Platform Admin'),
        ('COMPANY_ADMIN', 'Company Admin'),
        ('EMPLOYEE', 'Employee'),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    company = models.ForeignKey(
        Company,
        null=True,
        blank=True,
        on_delete=models.CASCADE
    )

    department = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )

    activation_token = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

     # Quick access properties
    @property
    def is_platform_admin(self):
        return self.role == 'PLATFORM_ADMIN'
    
    @property
    def is_company_admin(self):
        return self.role == 'COMPANY_ADMIN'
    
    @property
    def is_employee(self):
        return self.role == 'EMPLOYEE'
    
    def __str__(self):
        role_display = dict(self.ROLE_CHOICES).get(self.role, self.role)
        return f"{self.get_full_name()} ({role_display})"



# ==== Employee Profile Model (Simplified) ====
class EmployeeProfile(models.Model):
    """
    Extended profile for employees with training metrics.
    """
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='employee_profile'
    )
    
    employee_id = models.CharField(
        max_length=50, 
        unique=True,
        help_text="Company-specific employee ID"
    )
    
    # Awareness metrics
    awareness_score = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    total_points = models.IntegerField(default=0)
    streak_days = models.IntegerField(default=0)
    last_activity_date = models.DateField(null=True, blank=True)
    
    # Training statistics
    completed_courses_count = models.IntegerField(default=0)
    average_quiz_score = models.FloatField(default=0.0)
    
    # Phishing performance
    phishing_tests_taken = models.IntegerField(default=0)
    phishing_tests_passed = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.employee_id}"
    
    @property
    def company(self):
        return self.user.company
    
    @property
    def department(self):
        return self.user.department
    
    def calculate_awareness_score(self):
        """Simple score calculation"""
        score = 0
        
        # Course completion
        if self.completed_courses_count > 0:
            score += min(30, self.completed_courses_count * 5)
        
        # Quiz performance
        score += min(30, self.average_quiz_score * 0.3)
        
        # Phishing performance
        if self.phishing_tests_taken > 0:
            pass_rate = (self.phishing_tests_passed / self.phishing_tests_taken) * 100
            score += min(40, pass_rate * 0.4)
        
        self.awareness_score = int(score)
        return self.awareness_score
    
    def save(self, *args, **kwargs):
        self.calculate_awareness_score()
        super().save(*args, **kwargs)