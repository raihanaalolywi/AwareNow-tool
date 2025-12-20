from django.core.mail import send_mail
from django.conf import settings

def send_activation_email(user):

    print("🔥 send_activation_email called for:", user.email)

    activation_link = f"{settings.SITE_DOMAIN}/activate/{user.activation_token}/"
    print("🔗 Activation link:", activation_link)

    send_mail(
        subject="Activate your AwareNow account",
        message=f"Click the link to activate your account:\n{activation_link}",
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[user.email],
    )

# ====== Create staff group ======
def get_or_create_staff_group(company):
    from .models import CompanyGroup
    staff_group, _ = CompanyGroup.objects.get_or_create(
        company=company,
        name="Staff",
        defaults={"is_system": True}
    )
    return staff_group

