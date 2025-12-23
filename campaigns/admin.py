from django.contrib import admin
from .models import (
    EmailTemplate,
    PhishingCampaign,
    CampaignRecipient,
    PhishingEvent,
)

@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "subject", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "subject")


@admin.register(PhishingCampaign)
class PhishingCampaignAdmin(admin.ModelAdmin):
    list_display = ("title", "sender", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("title", "sender", "user_group")


@admin.register(CampaignRecipient)
class CampaignRecipientAdmin(admin.ModelAdmin):
    list_display = (
        "email",
        "campaign",
        "token",
        "sent_at",
        "opened_at",
        "clicked_at",
        "fallen_at",
    )
    list_filter = ("campaign",)
    search_fields = ("email", "token")


@admin.register(PhishingEvent)
class PhishingEventAdmin(admin.ModelAdmin):
    list_display = (
        "campaign",
        "recipient",
        "event_type",
        "created_at",
    )
    list_filter = ("event_type", "campaign")
    search_fields = ("recipient__email",)
