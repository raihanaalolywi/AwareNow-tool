from django import forms
from django.core.exceptions import ValidationError
from .models import Course, CourseCategory

class CourseForm(forms.ModelForm):
    """Form for creating/editing courses"""
    class Meta:
        model = Course
        fields = [
            'title', 'brief_description', 'category', 'thumbnail',
            'video_url', 'video_duration_minutes', 'visibility',
            'is_published'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'brief_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter brief description (max 2048 chars)'
            }),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'thumbnail': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'video_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://example.com/video'
            }),
            'video_duration_minutes': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'placeholder': 'Duration in minutes'
            }),
            'visibility': forms.Select(attrs={'class': 'form-control'}),
            'points_reward': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'placeholder': 'Points for completion'
            }),
            'is_published': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean_title(self):
        title = self.cleaned_data.get('title')
        if len(title) < 5:
            raise ValidationError('Title must be at least 5 characters long.')
        return title
    
    def clean_video_duration_minutes(self):
        duration = self.cleaned_data.get('video_duration_minutes')
        if duration and duration > 600:  # 10 hours max
            raise ValidationError('Video duration cannot exceed 10 hours.')
        return duration

# forms.py
class CourseCategoryForm(forms.ModelForm):
    class Meta:
        model = CourseCategory
        fields = ['name', 'description']  # Only name and description
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add any additional initialization here