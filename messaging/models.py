from django.db import models
from django.conf import settings


class Conversation(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='conversations_as_student'
    )
    tutor_profile = models.ForeignKey(
        'tutors.TutorProfile',
        on_delete=models.CASCADE,
        related_name='conversations'
    )
    booking = models.ForeignKey(
        'bookings.Booking',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conversations'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['student', 'tutor_profile']
        ordering = ['-updated_at']

    def __str__(self):
        return f'Conversation: {self.student.get_full_name()} <-> {self.tutor_profile.user.get_full_name()}'


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'Message from {self.sender.get_full_name()} in Conversation #{self.conversation.pk}'
