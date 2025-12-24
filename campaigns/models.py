from django.db import models
from django.utils import timezone
from django.conf import settings
import uuid

from account.models import Company, CompanyGroup


# Email Template (Platform Admin)
class EmailTemplate(models.Model):
    VISIBILITY_CHOICES = (
        ('private', 'Draft'),
        ('global', 'All Companies'),
        ('specific', 'Specific Companies'),
    )

    name = models.CharField(max_length=255)
    subject = models.CharField(max_length=255)
    html_content = models.TextField()

    preview_image = models.ImageField(
        upload_to='email_templates/',
        blank=True,
        null=True
    )

    # Publishing
    is_published = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    visibility = models.CharField(
        max_length=20,
        choices=VISIBILITY_CHOICES,
        default='private'
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name


# Company ↔ EmailTemplate (Publish mapping)
class CompanyEmailTemplate(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='email_templates'
    )

    template = models.ForeignKey(
        EmailTemplate,
        on_delete=models.CASCADE,
        related_name='company_assignments'
    )

    assigned_at = models.DateTimeField(auto_now_add=True)

    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        unique_together = ('company', 'template')

    def __str__(self):
        return f"{self.company.name} → {self.template.name}"


from django.db import models
from django.utils import timezone

class PhishingCampaign(models.Model):
    STATUS_CHOICES = (
        ("draft", "Draft"),
        ("published", "Published"),
        ("completed", "Completed"),
    )

    title = models.CharField(max_length=150)

    user_group = models.ForeignKey(
        CompanyGroup,
        on_delete=models.PROTECT,
        related_name="phishing_campaigns",
        null=True,
        blank=True
    )

    sender = models.EmailField()

    # تاريخ بدء الحملة (اختياري)
    scheduled_date = models.DateField(null=True, blank=True)

    # ✅ تاريخ انتهاء الحملة (مدة الفيشنق)
    ends_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Phishing campaign expiry date & time"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft"
    )

    template = models.ForeignKey(
        EmailTemplate,
        on_delete=models.PROTECT,
        related_name="campaigns",
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(default=timezone.now)

    def is_expired(self):
        """
        ترجع True إذا انتهت مدة الحملة
        """
        return self.ends_at and timezone.now() >= self.ends_at

    def __str__(self):
        return self.title


# Campaign Recipient
class CampaignRecipient(models.Model):
    campaign = models.ForeignKey(
        PhishingCampaign,
        on_delete=models.CASCADE,
        related_name="recipients"
    )

    email = models.EmailField()
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    sent_at = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    fallen_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("campaign", "email")

    def __str__(self):
        return f"{self.email} ({self.campaign.title})"

    @property
    def opened(self):
        return self.opened_at is not None

    @property
    def clicked(self):
        return self.clicked_at is not None

    @property
    def fallen(self):
        return self.fallen_at is not None


# Phishing Events (Open / Click / Fall)
class PhishingEvent(models.Model):
    class EventType(models.TextChoices):
        OPEN = "open", "Open"
        CLICK = "click", "Click"
        FALL = "fall", "Fall"

    id = models.BigAutoField(primary_key=True)

    campaign = models.ForeignKey(
        PhishingCampaign,
        on_delete=models.CASCADE,
        related_name="events"
    )

    recipient = models.ForeignKey(
        CampaignRecipient,
        on_delete=models.CASCADE,
        related_name="events"
    )

    event_type = models.CharField(max_length=10, choices=EventType.choices)

    target_url = models.URLField(max_length=1000, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [
            models.Index(fields=["campaign", "event_type", "created_at"]),
            models.Index(fields=["recipient", "created_at"]),
        ]

    def __str__(self):
        return f"{self.campaign.title} | {self.recipient.email} | {self.event_type}"
