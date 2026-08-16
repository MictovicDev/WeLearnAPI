"""
Email service layer for Welearn.

Each function below builds the template context for one event and fires
`send_templated_email_task.delay(...)`. Call these from your views,
serializers, or signal handlers, e.g.:

    from emails_app.services import notify_booking_created

    booking.save()
    notify_booking_created(booking)

Adjust the field names (booking.tutor.user.email, etc.) to match your
actual models — these assume the shapes implied by your User /
TutorProfile / Booking / PaymentInfo / Message models.
"""

from django.conf import settings

from users.tasks import send_templated_email_task

FRONTEND_URL = getattr(settings, "FRONTEND_URL", "https://app.welearn.com")


# ---------------------------------------------------------------------------
# 1. Verification email
# ---------------------------------------------------------------------------
def notify_verification_email(user, verification_token: str, expiry_hours: int = 24):
    verification_url = f"{'https://welearnglobal.vercel.app'}/verify-email?token={verification_token}"
    send_templated_email_task.delay(
        subject="Verify your Welearn email address",
        template_name="verification_email.html",
        context={
            "user_first_name": user.first_name,
            "verification_url": verification_url,
            "expiry_hours": expiry_hours,
        },
        to_email=user.email,
    )


# ---------------------------------------------------------------------------
# 2. Booking created
# ---------------------------------------------------------------------------
def notify_booking_created(booking):
    """Fires two emails: one to the student, one to the tutor."""
    common = {
        "subject": booking.subject,
        "session_datetime": booking.session_datetime.strftime("%A, %d %b %Y &middot; %I:%M %p"),
    }

    send_templated_email_task.delay(
        subject="Your session was successfully booked",
        template_name="booking_created_student.html",
        context={
            **common,
            "student_first_name": booking.student.first_name,
            "tutor_name": booking.tutor.get_full_name(),
            "booking_url": f"{FRONTEND_URL}/bookings/{booking.id}",
        },
        to_email=booking.student.email,
    )

    send_templated_email_task.delay(
        subject="You have a new booking request",
        template_name="booking_created_tutor.html",
        context={
            **common,
            "tutor_first_name": booking.tutor.first_name,
            "student_name": booking.student.get_full_name(),
            "dashboard_url": f"{FRONTEND_URL}/bookings/{booking.id}",
        },
        to_email=booking.tutor.email,
    )


# ---------------------------------------------------------------------------
# 3. Booking accepted / declined
# ---------------------------------------------------------------------------
def notify_booking_status(booking, status: str):
    """
    status: "accepted" or "declined"
    Always emails the student. Only emails the tutor on acceptance,
    since decline is an action the tutor already took themselves.
    """
    common = {
        "subject": booking.subject,
        "session_datetime": booking.session_datetime.strftime("%A, %d %b %Y &middot; %I:%M %p"),
        "tutor_name": booking.tutor.get_full_name(),
    }

    send_templated_email_task.delay(
        subject="Your booking has been accepted" if status == "accepted" else "Update on your booking",
        template_name="booking_status_student.html",
        context={
            **common,
            "status": status,
            "student_first_name": booking.student.first_name,
            "payment_url": f"{FRONTEND_URL}/bookings/{booking.id}/pay",
            "find_tutor_url": f"{FRONTEND_URL}/tutors",
        },
        to_email=booking.student.email,
    )

    if status == "accepted":
        send_templated_email_task.delay(
            subject="You've accepted a booking",
            template_name="booking_accepted_tutor.html",
            context={
                **common,
                "tutor_first_name": booking.tutor.first_name,
                "student_name": booking.student.get_full_name(),
                "dashboard_url": f"{FRONTEND_URL}/bookings/{booking.id}",
            },
            to_email=booking.tutor.email,
        )


# ---------------------------------------------------------------------------
# 4. Payment made
# ---------------------------------------------------------------------------
def notify_payment_success(booking, payment):
    common = {
        "subject": booking.subject,
        "session_datetime": booking.session_datetime.strftime("%A, %d %b %Y &middot; %I:%M %p"),
        "amount_paid": f"₦{payment.amount:,.2f}",
    }

    send_templated_email_task.delay(
        subject="Payment successful, you're all set",
        template_name="payment_success_student.html",
        context={
            **common,
            "student_first_name": booking.student.first_name,
            "tutor_name": booking.tutor.get_full_name(),
            "payment_reference": payment.reference,
            "dashboard_url": f"{FRONTEND_URL}/bookings/{booking.id}",
        },
        to_email=booking.student.email,
    )

    send_templated_email_task.delay(
        subject="Payment received for your session",
        template_name="payment_success_tutor.html",
        context={
            **common,
            "tutor_first_name": booking.tutor.first_name,
            "student_name": booking.student.get_full_name(),
            "dashboard_url": f"{FRONTEND_URL}/bookings/{booking.id}",
        },
        to_email=booking.tutor.email,
    )


# ---------------------------------------------------------------------------
# 5. Tutor profile approved
# ---------------------------------------------------------------------------
def notify_tutor_approved(tutor_profile):
    send_templated_email_task.delay(
        subject="You're approved as a Welearn tutor",
        template_name="tutor_approved.html",
        context={
            "tutor_first_name": tutor_profile.user.first_name,
            "dashboard_url": f"{FRONTEND_URL}/dashboard",
        },
        to_email=tutor_profile.user.email,
    )


# ---------------------------------------------------------------------------
# 6. New message
# ---------------------------------------------------------------------------
def notify_new_message(message):
    """
    message is expected to expose: sender, recipient, content,
    and sender.get_role_display() or similar for "Student"/"Tutor".
    """
    preview = (message.content[:140] + "...") if len(message.content) > 140 else message.content

    send_templated_email_task.delay(
        subject=f"New message from {message.sender.get_full_name()}",
        template_name="new_message.html",
        context={
            "recipient_first_name": message.recipient.first_name,
            "sender_name": message.sender.get_full_name(),
            "sender_role": message.sender.role,  # e.g. "Student" or "Tutor"
            "message_preview": preview,
            "conversation_url": f"{FRONTEND_URL}/messages/{message.conversation_id}",
        },
        to_email=message.recipient.email,
    )
