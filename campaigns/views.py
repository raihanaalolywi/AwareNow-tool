from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from django.template import Template, Context

import base64

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.urls import reverse

from .models import PhishingCampaign, EmailTemplate, CampaignRecipient, PhishingEvent
from .forms import PhishingCampaignForm


# =========================
# Phishing List
# =========================
@login_required
def phishing_list(request):
    q = request.GET.get("q", "").strip()

    campaigns = PhishingCampaign.objects.all().order_by("-created_at")

    if q:
        campaigns = campaigns.filter(
            Q(title__icontains=q) |
            Q(sender__icontains=q) |
            Q(user_group__name__icontains=q)
        )

    draft_campaigns = campaigns.filter(status="draft")
    active_campaigns = campaigns.filter(status="published")
    completed_campaigns = campaigns.filter(status="completed")

    context = {
        "q": q,
        "draft_campaigns": draft_campaigns,
        "active_campaigns": active_campaigns,
        "completed_campaigns": completed_campaigns,
    }
    return render(request, "campaigns/phishing/phishing_list.html", context)


# =========================
# Create Phishing
# =========================
@login_required
def phishing_create(request):
    templates = EmailTemplate.objects.filter(is_active=True).order_by("-created_at")

    company = getattr(request.user, "company", None)

    if request.method == "POST":
        form = PhishingCampaignForm(request.POST, company=company)
        if form.is_valid():
            campaign = form.save(commit=False)

            # ✅ التيمبلت لازم يكون موجود وصالح
            if campaign.template_id:
                is_ok = EmailTemplate.objects.filter(
                    id=campaign.template_id,
                    is_active=True
                ).exists()
                if not is_ok:
                    form.add_error("template", "Selected template is invalid.")
                    return render(request, "campaigns/phishing/phishing_create.html", {
                        "form": form,
                        "templates": templates,
                    })
            else:
                form.add_error("template", "Please select a template.")
                return render(request, "campaigns/phishing/phishing_create.html", {
                    "form": form,
                    "templates": templates,
                })

            # ✅ الافتراضي Draft (حتى لو أحد حاول يمرر status)
            campaign.status = "draft"

            campaign.save()
            return redirect("campaigns:phishing")
    else:
        form = PhishingCampaignForm(company=company)

    return render(request, "campaigns/phishing/phishing_create.html", {
        "form": form,
        "templates": templates,
    })


# =========================
# Template Preview
# =========================
@login_required
def template_preview(request, pk):
    t = get_object_or_404(EmailTemplate, pk=pk, is_active=True)

    ctx = Context({
        "first_name": "John",
        "company": "@ContosoCorp",
        "invoice_id": "10492",
        "decision_date": "Mon Dec 22 2025 09:17:41 GMT+0300 (Arabian Standard Time)",
        "tracking_url": "#",
    })

    rendered_html = Template(t.html_content).render(ctx)
    return HttpResponse(rendered_html, content_type="text/html; charset=utf-8")


# =========================
# Tracking Views
# =========================
def track_open(request, token):
    recipient = get_object_or_404(CampaignRecipient, token=token)

    if recipient.opened_at is None:
        recipient.opened_at = timezone.now()
        recipient.save(update_fields=["opened_at"])

    PhishingEvent.objects.create(
        campaign=recipient.campaign,
        recipient=recipient,
        event_type=PhishingEvent.EventType.OPEN,
        ip_address=request.META.get("REMOTE_ADDR"),
        user_agent=(request.META.get("HTTP_USER_AGENT", "") or "")[:512],
    )

    pixel = (
        b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00"
        b"\x00\x00\x00\xff\xff\xff\x21\xf9\x04\x01\x00\x00\x00"
        b"\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02"
        b"\x44\x01\x00\x3b"
    )
    return HttpResponse(pixel, content_type="image/gif")


def track_click(request, token):
    recipient = get_object_or_404(CampaignRecipient, token=token)

    encoded_url = request.GET.get("u", "").strip()
    if not encoded_url:
        return HttpResponse("Missing target url", status=400)

    try:
        target_url = base64.urlsafe_b64decode(encoded_url.encode()).decode()
    except Exception:
        return HttpResponse("Invalid target url", status=400)

    if recipient.clicked_at is None:
        recipient.clicked_at = timezone.now()
        recipient.save(update_fields=["clicked_at"])

    PhishingEvent.objects.create(
        campaign=recipient.campaign,
        recipient=recipient,
        event_type=PhishingEvent.EventType.CLICK,
        target_url=target_url,
        ip_address=request.META.get("REMOTE_ADDR"),
        user_agent=(request.META.get("HTTP_USER_AGENT", "") or "")[:512],
    )

    return redirect(target_url)


def track_fall(request, token):
    recipient = get_object_or_404(CampaignRecipient, token=token)

    if recipient.fallen_at is None:
        recipient.fallen_at = timezone.now()
        recipient.save(update_fields=["fallen_at"])

    PhishingEvent.objects.create(
        campaign=recipient.campaign,
        recipient=recipient,
        event_type=PhishingEvent.EventType.FALL,
        ip_address=request.META.get("REMOTE_ADDR"),
        user_agent=(request.META.get("HTTP_USER_AGENT", "") or "")[:512],
    )

    # ✅ Auto move campaign to Completed when someone falls
    if recipient.campaign.status != "completed":
        recipient.campaign.status = "completed"
        recipient.campaign.save(update_fields=["status"])

    return HttpResponse(
        """
        <div style="font-family:system-ui;max-width:680px;margin:40px auto;padding:24px;border:1px solid #e5e7eb;border-radius:16px;">
          <h2>Security Awareness</h2>
          <p>This was a phishing simulation. Your action has been logged.</p>
          <p>Please proceed to awareness training.</p>
        </div>
        """,
        content_type="text/html; charset=utf-8"
    )


# =========================
# Publish & Send Emails (Draft -> Active)
# =========================
@login_required
def publish_and_send(request, campaign_id):
    campaign = get_object_or_404(PhishingCampaign, id=campaign_id)

    # ✅ لازم تكون Draft فقط
    if campaign.status != "draft":
        return HttpResponse("Campaign is not in draft.", status=400)

    if not campaign.template_id:
        return HttpResponse("Campaign has no template.", status=400)

    if not campaign.user_group_id:
        return HttpResponse("Campaign has no user group.", status=400)

    group = campaign.user_group
    group_users = (
        group.users
        .filter(is_disabled=False)
        .exclude(email__isnull=True)
        .exclude(email="")
        .distinct()
    )

    if not group_users.exists():
        return HttpResponse("Selected group has no users with emails.", status=400)

    # جهزي recipients
    for u in group_users:
        CampaignRecipient.objects.get_or_create(
            campaign=campaign,
            email=u.email
        )

    recipients = CampaignRecipient.objects.filter(campaign=campaign).order_by("email")
    now = timezone.now()

    for r in recipients:
        # ✅ لا تعيدين إرسال نفس الشخص مرتين
        if r.sent_at is not None:
            continue

        open_url = request.build_absolute_uri(
            reverse("campaigns:track-open", args=[r.token])
        )

        # هذا هو الـ FALL الحقيقي
        fall_url = request.build_absolute_uri(
            reverse("campaigns:track-fall", args=[r.token])
        )

        # ✅ CLICK tracker يودّي للـ fall_url
        encoded_fall = base64.urlsafe_b64encode(fall_url.encode()).decode()
        click_url = request.build_absolute_uri(
            reverse("campaigns:track-click", args=[r.token])
        ) + f"?u={encoded_fall}"

        ctx = Context({
            "first_name": "Hanan",
            "company": "AwareNow",
            # ✅ أهم سطر: خليه يروح للـ CLICK tracking
            "tracking_url": click_url,
            "recipient_email": r.email,
        })

        html_body = Template(campaign.template.html_content).render(ctx)

        # ✅ Open pixel
        html_body += f'<img src="{open_url}" width="1" height="1" style="display:none" alt=""/>'

        msg = EmailMultiAlternatives(
            subject=campaign.template.subject or campaign.title,
            body="",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[r.email],
            reply_to=[campaign.sender] if campaign.sender else None,
        )
        msg.attach_alternative(html_body, "text/html")
        msg.send(fail_silently=False)

        r.sent_at = now
        r.save(update_fields=["sent_at"])

    # ✅ بعد الإرسال: تتحول Published (Active)
    campaign.status = "published"
    campaign.save(update_fields=["status"])

    return redirect("campaigns:phishing")



# Report

@login_required
def phishing_report(request, campaign_id):
    campaign = get_object_or_404(PhishingCampaign, id=campaign_id)

    recipients = CampaignRecipient.objects.filter(campaign=campaign).order_by("email")

    totals = {
        "total": recipients.count(),
        "opened": recipients.filter(opened_at__isnull=False).count(),
        "clicked": recipients.filter(clicked_at__isnull=False).count(),
        "fallen": recipients.filter(fallen_at__isnull=False).count(),
        "no_action": recipients.filter(
            opened_at__isnull=True,
            clicked_at__isnull=True,
            fallen_at__isnull=True
        ).count(),
    }

    return render(request, "campaigns/phishing/phishing_report.html", {
        "campaign": campaign,
        "recipients": recipients,
        "totals": totals,
    })
