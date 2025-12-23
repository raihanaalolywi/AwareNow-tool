# Update your existing admin.py with these improvements:

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import (
    CourseCategory, Course, CompanyCourseAssignment,
    CompanyCourseGroup, Quiz, QuizQuestion, EmployeeCourseAssignment,
    QuizAttempt  # Add this import
)
from django.db.models import Count

# Add this inline class
class QuizQuestionInline(admin.TabularInline):
    model = QuizQuestion
    extra = 1
    fields = ('order', 'question_text', 'question_type', 'points', 'correct_answers')
    ordering = ('order',)
    show_change_link = True

# Update your existing QuizAdmin
@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ('course', 'title', 'passing_score', 'is_active', 'question_count', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('course__title', 'title', 'description')
    inlines = [QuizQuestionInline]  # Add this line
    fieldsets = (
        ('Basic Information', {
            'fields': ('course', 'title', 'description')
        }),
        ('Quiz Settings', {
            'fields': ('passing_score', 'time_limit_minutes', 'max_attempts', 'is_active')
        }),
    )
    
    def question_count(self, obj):
        return obj.questions.count()
    question_count.short_description = 'Questions'

# Update your existing QuizQuestionAdmin
@admin.register(QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    list_display = ('quiz', 'order', 'question_preview', 'question_type', 'points')
    list_filter = ('quiz__course', 'question_type')
    search_fields = ('question_text',)
    ordering = ('quiz', 'order')
    list_editable = ('order',)
    
    fieldsets = (
        ('Question Details', {
            'fields': ('quiz', 'order', 'question_text', 'question_type', 'points', 'explanation')
        }),
        ('Answer Options', {
            'fields': ('option_a', 'option_b', 'option_c', 'option_d'),
            'description': 'Fill options based on question type. For True/False, use Option A for True and Option B for False.'
        }),
        ('Correct Answer', {
            'fields': ('correct_answers',),
            'description': "Single choice: 'A', Multiple select: 'A,C', True/False: 'True' or 'False'"
        }),
    )
    
    def question_preview(self, obj):
        return obj.question_text[:100] + '...' if len(obj.question_text) > 100 else obj.question_text
    question_preview.short_description = 'Question'

# Add this new admin for QuizAttempt
@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ('employee', 'quiz', 'attempt_number', 'score_display', 'passed', 'started_at', 'completed_at')
    list_filter = ('passed', 'quiz__course', 'started_at')
    search_fields = ('employee__user__email', 'quiz__course__title')
    readonly_fields = ('score_display', 'time_taken_display', 'answers_preview')
    ordering = ('-started_at',)
    
    fieldsets = (
        ('Attempt Information', {
            'fields': ('employee', 'quiz', 'attempt_number')
        }),
        ('Results', {
            'fields': ('score_display', 'passed', 'time_taken_display')
        }),
        ('Timing', {
            'fields': ('started_at', 'completed_at')
        }),
        ('Answers', {
            'fields': ('answers_preview',),
            'classes': ('collapse',)
        }),
    )
    
    def score_display(self, obj):
        return f"{obj.score:.1f}%"
    score_display.short_description = 'Score'
    
    def time_taken_display(self, obj):
        if obj.time_taken_seconds:
            minutes = obj.time_taken_seconds // 60
            seconds = obj.time_taken_seconds % 60
            return f"{minutes}m {seconds}s"
        return "N/A"
    time_taken_display.short_description = 'Time Taken'
    
    def answers_preview(self, obj):
        if obj.answers_data:
            preview = []
            for q_id, answer in obj.answers_data.items():
                preview.append(f"Q{q_id}: {answer}")
            return format_html('<br>'.join(preview))
        return "No answers recorded"
    answers_preview.short_description = 'Answers'

# Add this admin for EmployeeCourseAssignment if not already present
@admin.register(EmployeeCourseAssignment)
class EmployeeCourseAssignmentAdmin(admin.ModelAdmin):
    list_display = ('employee', 'course', 'status', 'progress_percentage', 'started_at', 'completed_at')
    list_filter = ('status', 'course', 'company_course_group__company')
    search_fields = ('employee__user__email', 'course__title')
    readonly_fields = ('assigned_at', 'last_accessed')
    
    fieldsets = (
        ('Assignment', {
            'fields': ('company_course_group', 'employee', 'course', 'assigned_by')
        }),
        ('Progress', {
            'fields': ('status', 'progress_percentage')
        }),
        ('Timing', {
            'fields': ('assigned_at', 'started_at', 'completed_at', 'last_accessed', 'due_date')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # New object
            obj.assigned_by = request.user
        super().save_model(request, obj, form, change)

# You might also want to add admin for CompanyCourseGroup if needed
@admin.register(CompanyCourseGroup)
class CompanyCourseGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'course_count')
    list_filter = ('company',)
    search_fields = ('name', 'company__name')
    
    def course_count(self, obj):
        return obj.courses.count()
    course_count.short_description = 'Courses'