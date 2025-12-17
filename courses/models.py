from django.db import models
from account.models import Company, User
from django.utils import timezone

# Create your models here.

class CourseCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    
      # Font Awesome icon class name (without the 'fa-' prefix)
    icon = models.CharField(
        max_length=50, 
        blank=True,
        default='book',
        help_text="Font Awesome icon name (e.g., 'shield-alt', 'user-secret', 'lock')"
    )
    
    # Optional: Color for the category
    color = models.CharField(
        max_length=7,  # Hex color code
        default='#3498db',
        help_text="Hex color code for this category"
    )
    
    def __str__(self):
        return self.name
    
    def get_icon_html(self):
        """Generate HTML for the icon"""
        return f'<i class="fas fa-{self.icon}"></i>'
    
    def __str__(self):
        return self.name
    
def course_thumbnail_path(instance, filename):
    """
    Generate upload path for course thumbnails.
    Uses UUID for guaranteed unique filenames.
    """
    import os
    import uuid
    
    # Get file extension
    ext = os.path.splitext(filename)[1]
    if not ext:
        ext = '.jpg'  # Default extension
    
    # Create unique filename using UUID
    unique_name = f"{uuid.uuid4().hex}{ext}"
    
    # Return path relative to MEDIA_ROOT
    return os.path.join('courses', 'thumbnails', unique_name)

class Course(models.Model):
    title = models.CharField(max_length=200)
    brief_description = models.CharField(max_length=2048)

    category = models.ForeignKey(CourseCategory, on_delete=models.SET_NULL, null=True)

    thumbnail = models.ImageField(
        upload_to=course_thumbnail_path,
        default='courses/defaults/default_thumbnail.jpg',  # Path relative to MEDIA_ROOT
        blank=True,  # ADD THIS - allows empty field
        null=True,
        verbose_name="Course Thumbnail",
        help_text="Upload a thumbnail image for this course (400x300px). Leave empty for default."
    )
    
    video_url = models.URLField(blank=True)
    video_duration_minutes = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_courses')
    visibility = models.CharField(
        max_length=20,
        choices=[
            ('global', 'Global - All Companies'),
            ('specific', 'Specific Companies Only'),
            ('private', 'Private - Draft')
        ],
        default='private'
    )
    
    # Status and publishing
    is_active = models.BooleanField(default=True)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    points_reward = models.IntegerField(default=100)
    companies = models.ManyToManyField(Company, through='CompanyCourseAssignment', related_name='assigned_courses')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        """
        Custom save to handle thumbnail updates properly.
        """
        # If this is an UPDATE (course already exists)
        if self.pk:
            try:
                # Get the existing course from database
                old_course = Course.objects.get(pk=self.pk)
                
                # If user cleared the thumbnail (empty), use default
                if not self.thumbnail and old_course.thumbnail:
                    # User removed the custom thumbnail, use default
                    self.thumbnail = 'courses/defaults/default_thumbnail.jpg'
                
                # If user uploaded new thumbnail, it will automatically replace old one
                # Django handles file deletion of old thumbnails automatically
                
            except Course.DoesNotExist:
                pass  # Course doesn't exist yet (shouldn't happen)
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.title
    
    class Meta:
        ordering = ['-created_at']
    

class CompanyCourseAssignment(models.Model):
    """
    Tracks which courses are assigned to which companies
    """
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    assigned_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['company', 'course']
    
    def __str__(self):
        return f"{self.company.name} - {self.course.title}"
    
class CompanyCourseGroup(models.Model):  # Fixed typo from "CompayCourseGroup"
    """
    Groups of courses assigned to specific employee groups within a company
    """
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='course_groups')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    courses = models.ManyToManyField(Course, related_name='assigned_groups', blank=True)
    assigned_to_employees = models.ManyToManyField('account.EmployeeProfile', 
                                                   related_name='course_groups')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} - {self.company.name}"
    
class EmployeeCourseAssignment(models.Model):
    """Only for direct course assignments"""
    employee = models.ForeignKey('account.EmployeeProfile', on_delete=models.CASCADE, 
                                 related_name='assigned_courses')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, 
                               related_name='employee_assignments')
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, 
                                    related_name='assigned_employee_courses')
    assigned_at = models.DateTimeField(auto_now_add=True)
    
    # Status tracking
    STATUS_CHOICES = [
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='assigned')
    
    # Completion tracking
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    
    # Progress tracking
    progress_percentage = models.FloatField(default=0.0)  # 0.0 to 100.0
    last_accessed = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['employee', 'course']
        ordering = ['-assigned_at']
    
    def __str__(self):
        return f"{self.employee.user.email} - {self.course.title}"
    
class EmployeeCourseProgress(models.Model):
    """
    Detailed progress tracking for employee course completion
    """
    assignment = models.OneToOneField(EmployeeCourseAssignment, on_delete=models.CASCADE,
                                      related_name='detailed_progress')
    
    # Video progress
    video_watched_seconds = models.IntegerField(default=0)
    video_total_seconds = models.IntegerField(default=0)
    
    # Quiz performance
    quiz_attempts = models.IntegerField(default=0)
    best_quiz_score = models.FloatField(null=True, blank=True)  # 0.0 to 100.0
    passed_quiz = models.BooleanField(default=False)
    
    # Activity tracking
    total_time_spent = models.IntegerField(default=0)  # in seconds
    last_activity = models.DateTimeField(auto_now=True)
    
    # Completion requirements
    required_watch_percentage = models.IntegerField(default=90)  # % of video to watch
    required_quiz_score = models.IntegerField(default=70)  # % to pass quiz
    
    class Meta:
        verbose_name_plural = "Employee Course Progress"
    
    def __str__(self):
        return f"Progress: {self.assignment.employee.user.email} - {self.assignment.course.title}"
    
class Quiz(models.Model):
    """
    Quiz associated with a course
    """
    course = models.OneToOneField(Course, on_delete=models.CASCADE, related_name='quiz')
    title = models.CharField(max_length=200, default="Course Quiz")
    description = models.TextField(blank=True)
    
    # Quiz settings
    passing_score = models.IntegerField(default=70, 
                                        help_text="Minimum percentage required to pass")
    time_limit_minutes = models.IntegerField(default=30, 
                                             help_text="Time limit in minutes (0 for no limit)")
    max_attempts = models.IntegerField(default=3, 
                                       help_text="Maximum number of attempts allowed")
    
    # Metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Quiz: {self.course.title}"

class QuizQuestion(models.Model):
    """
    Questions for course quizzes
    """
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    
    QUESTION_TYPES = [
        ('multiple_choice', 'Multiple Choice (Single Answer)'),
        ('multiple_select', 'Multiple Select'),
        ('true_false', 'True/False'),
    ]
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES, 
                                     default='multiple_choice')
    
    # For multiple choice questions
    option_a = models.CharField(max_length=500, blank=True)
    option_b = models.CharField(max_length=500, blank=True)
    option_c = models.CharField(max_length=500, blank=True)
    option_d = models.CharField(max_length=500, blank=True)
    
    # Correct answer(s) - stored as JSON or comma-separated
    correct_answers = models.CharField(max_length=100, 
                                      help_text="For multiple choice: 'A', for multiple select: 'A,C', for True/False: 'True'")
    
    # Points and explanation
    points = models.IntegerField(default=10)
    explanation = models.TextField(blank=True, 
                                  help_text="Explanation shown after answering")
    
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"Q{self.order}: {self.question_text[:50]}..."

class QuizAttempt(models.Model):
    """
    Records employee quiz attempts
    """
    employee = models.ForeignKey('account.EmployeeProfile', on_delete=models.CASCADE,
                                 related_name='quiz_attempts')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    attempt_number = models.IntegerField(default=1)
    
    # Results
    score = models.FloatField(default=0.0)
    passed = models.BooleanField(default=False)
    
    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    time_taken_seconds = models.IntegerField(default=0)
    
    # Detailed answers (stored as JSON)
    answers_data = models.JSONField(default=dict, blank=True)
    
    class Meta:
        unique_together = ['employee', 'quiz', 'attempt_number']
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.employee.user.email} - {self.quiz.course.title} (Attempt {self.attempt_number})"

class CourseCompletionCertificate(models.Model):
    """
    Certificate issued when employee completes a course
    """
    employee = models.ForeignKey('account.EmployeeProfile', on_delete=models.CASCADE,
                                 related_name='certificates')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, 
                               related_name='certificates')
    assignment = models.OneToOneField(EmployeeCourseAssignment, on_delete=models.CASCADE,
                                      related_name='certificate')
    
    # Certificate details
    certificate_id = models.CharField(max_length=50, unique=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    issued_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    # Verification
    verification_token = models.CharField(max_length=100, unique=True)
    
    # PDF storage
    pdf_file = models.FileField(upload_to='certificates/', blank=True, null=True)
    
    class Meta:
        unique_together = ['employee', 'course']
    
    def __str__(self):
        return f"Certificate {self.certificate_id} - {self.employee.user.email}"