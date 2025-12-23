from django.db import models
from django.utils import timezone
import uuid 

class EmailTemplate(models.Model):
    name = models.CharField(max_length=120)
    subject = models.CharField(max_length=200, blank=True)

    preview_image = models.ImageField(
        upload_to="phishing_templates/",
        blank=True,
        null=True
    )

    html_content = models.TextField()  # HTML email body

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class PhishingCampaign(models.Model):
    STATUS_CHOICES = (
        ("draft", "Draft"),
        ("published", "Published"),
        ("completed", "Completed"),
    )

    title = models.CharField(max_length=150)
    user_group = models.CharField(max_length=100)
    sender = models.EmailField()

    scheduled_date = models.DateField(
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft"
    )

    # ✅ الربط مع التيمبلت
    template = models.ForeignKey(
        EmailTemplate,
        on_delete=models.PROTECT,
        related_name="campaigns",
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.title
class CampaignRecipient(models.Model):
    campaign = models.ForeignKey("PhishingCampaign", on_delete=models.CASCADE, related_name="recipients")
    email = models.EmailField()
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    sent_at = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    fallen_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("campaign", "email")

    def __str__(self):
        return f"{self.email} ({self.campaign_id})"

    @property
    def opened(self): return self.opened_at is not None

    @property
    def clicked(self): return self.clicked_at is not None

    @property
    def fallen(self): return self.fallen_at is not None

class PhishingEvent(models.Model):
    class EventType(models.TextChoices):
        OPEN = "open", "Open"
        CLICK = "click", "Click"
        FALL = "fall", "Fall"

    id = models.BigAutoField(primary_key=True)

    campaign = models.ForeignKey(
        "PhishingCampaign",
        on_delete=models.CASCADE,
        related_name="events"
    )

    recipient = models.ForeignKey(
        "CampaignRecipient",
        on_delete=models.CASCADE,
        related_name="events"
    )

    event_type = models.CharField(max_length=10, choices=EventType.choices)

    target_url = models.URLField(max_length=1000, blank=True)   # للـ click
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
