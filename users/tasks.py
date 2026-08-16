import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,  # seconds
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def send_templated_email_task(self, subject: str, template_name: str, context: dict, to_email: str):
    """
    Generic Celery task that renders an email template and sends it.

    Call this via `.delay(...)` from anywhere in the codebase — views,
    signals, serializers, viewsets — instead of calling send_mail directly.
    Keeping SMTP calls in a task means booking/payment endpoints respond
    immediately and don't block on the email provider.
    """
    try:
        html_body = render_to_string(f"emails/{template_name}", context)
        text_body = strip_tags(html_body)

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to_email],
        )
        email.attach_alternative(html_body, "text/html")
        email.send(fail_silently=False)

        logger.info("Email sent: template=%s to=%s subject=%s", template_name, to_email, subject)
    except Exception as exc:
        logger.exception("Email failed: template=%s to=%s", template_name, to_email)
        raise self.retry(exc=exc)
