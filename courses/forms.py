from django import forms
from django.core.exceptions import ValidationError
from django.forms import formset_factory

from .models import Course, CourseCategory, Quiz, QuizQuestion


class CourseForm(forms.ModelForm):
    """Form for creating/editing courses"""
    class Meta:
        model = Course
        fields = [
            'title', 'brief_description', 'category', 'thumbnail',
            'video_url', 'video_duration_minutes', 'visibility',
            'points_reward', 'is_published'
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

            'visibility': forms.Select(attrs={'class': 'form-select'}),

            'points_reward': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'placeholder': 'Points for completion'
            }),

            'is_published': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_title(self):
        title = self.cleaned_data.get('title')
        if title and len(title) < 5:
            raise ValidationError('Title must be at least 5 characters long.')
        return title

    def clean_video_duration_minutes(self):
        duration = self.cleaned_data.get('video_duration_minutes')
        if duration and duration > 600:
            raise ValidationError('Video duration cannot exceed 10 hours.')
        return duration


class CourseCategoryForm(forms.ModelForm):
    class Meta:
        model = CourseCategory
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class QuizForm(forms.ModelForm):
    class Meta:
        model = Quiz
        fields = ["passing_score", "time_limit_minutes", "max_attempts", "is_active"]
        widgets = {
            "passing_score": forms.NumberInput(attrs={"class": "form-control", "min": 0, "max": 100}),
            "time_limit_minutes": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "max_attempts": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["passing_score"].initial = 70
        self.fields["time_limit_minutes"].initial = 30
        self.fields["max_attempts"].initial = 3
        self.fields["is_active"].initial = True


class QuizQuestionForm(forms.ModelForm):
    class Meta:
        model = QuizQuestion
        fields = [
            "order",
            "question_text",
            "question_type",
            "points",
            "explanation",
            "option_a",
            "option_b",
            "option_c",
            "option_d",
            "correct_answers",
        ]
        widgets = {
            "order": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "question_text": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Write the question..."}),
            "question_type": forms.Select(attrs={"class": "form-select"}),
            "points": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "explanation": forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "Optional explanation"}),
            "option_a": forms.TextInput(attrs={"class": "form-control", "placeholder": "Option A"}),
            "option_b": forms.TextInput(attrs={"class": "form-control", "placeholder": "Option B"}),
            "option_c": forms.TextInput(attrs={"class": "form-control", "placeholder": "Option C"}),
            "option_d": forms.TextInput(attrs={"class": "form-control", "placeholder": "Option D"}),
            "correct_answers": forms.TextInput(attrs={"class": "form-control", "placeholder": "Example: A or A,C or True"}),
        }

    def clean(self):
        cleaned = super().clean()
        question_text = (cleaned.get("question_text") or "").strip()

        # إذا فاضي: نتجاوز بدون ما نزعج المستخدم (لأننا عندنا 4 فورمز ثابتة)
        if not question_text:
            return cleaned

        qt = cleaned.get("question_type")
        correct = (cleaned.get("correct_answers") or "").strip()

        if qt == "true_false":
            if correct not in ["True", "False"]:
                self.add_error("correct_answers", "For True/False, write: True or False.")
            if not cleaned.get("option_a"):
                cleaned["option_a"] = "True"
            if not cleaned.get("option_b"):
                cleaned["option_b"] = "False"
        else:
            if not cleaned.get("option_a") or not cleaned.get("option_b"):
                self.add_error("option_a", "Option A is required.")
                self.add_error("option_b", "Option B is required.")
            if not correct:
                self.add_error("correct_answers", "Correct answer is required (e.g., A or A,C).")

        return cleaned


QuizQuestionFormSet = formset_factory(QuizQuestionForm, extra=4, max_num=4)
