import logging
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)
DEFAULT_FROM = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@example.com")

def send_safe_mail(subject: str, message: str, to_email: str) -> bool:
    """
    Sends a single email.
    :param subject: subject
    :param message: message
    :param to_email: email address
    :return: Returns True on success. Otherwise, log errors and return False.
    """
    if not to_email:
        return False
    try:
        sent = send_mail(
            subject=subject,
            message=message,
            from_email=DEFAULT_FROM,
            recipient_list=[to_email],
            fail_silently=True,
        )
        if not sent:
            logger.warning("Email not sent (send_mail returned 0). to=%s subject=%r", to_email, subject)
            return False
        return True
    except Exception as exc:
        logger.exception("Failed to send email. to=%s subject=%r error=%s", to_email, subject, exc)
        return False