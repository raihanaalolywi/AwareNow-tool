from django.core.mail import send_mail
from django.conf import settings

def send_activation_email(user):
    # activation_link = f"http://127.0.0.1:8000/account/activate/{user.activation_token}/"
    # activation_link = f"{settings.SITE_DOMAIN}/activate/{user.activation_token}/"

    # send_mail(
    #     subject="Activate your AwareNow account",
    #     message=f"Click the link to activate your account:\n{activation_link}",
    #     from_email=settings.DEFAULT_FROM_EMAIL,
    #     recipient_list=[user.email],
    #     fail_silently=False,
    # )
    print("🔥 send_activation_email called for:", user.email)

    activation_link = f"{settings.SITE_DOMAIN}/activate/{user.activation_token}/"
    print("🔗 Activation link:", activation_link)

    send_mail(
        subject="Activate your AwareNow account",
        message=f"Click the link to activate your account:\n{activation_link}",
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[user.email],
    )