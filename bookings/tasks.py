from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

import logging

logger = logging.getLogger('tutor_platform')


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_booking_notification_email(self, booking_id):
    from .models import Booking  # local import avoids app-loading issues

    try:
        booking = Booking.objects.select_related(
            'student', 'tutor_profile__user'
        ).get(id=booking_id)
    except Booking.DoesNotExist:
        logger.error(f'Booking {booking_id} not found for email notification.')
        return

    tutor_email = booking.tutor_profile.user.email
    if not tutor_email:
        logger.warning(f'Tutor for booking {booking_id} has no email on file.')
        return

    subject = f'New booking request from {booking.student.get_full_name() or booking.student.username}'
    message = (
        f'You have a new booking request.\n\n'
        f'Student: {booking.student.get_full_name() or booking.student.username}\n'
        f'Session type: {booking.session_type}\n'
        f'Scheduled date: {booking.scheduled_date}\n\n'
        f'Log in to your dashboard to accept or decline.'
    )

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [tutor_email],
            fail_silently=False,
        )
    except Exception as exc:
        logger.exception(f'Failed to send booking email for booking {booking_id}')
        raise self.retry(exc=exc)