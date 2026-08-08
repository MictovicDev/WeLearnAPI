# chat/models.py

from django.conf import settings
from django.db import models
from users.models import User


class ChatThread(models.Model):
    """One standalone thread per student-tutor pair, independent of any
    specific booking."""
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='chat_threads_as_student', on_delete=models.CASCADE
    )
    tutor = models.ForeignKey(
        User, related_name='chat_threads_as_tutor', on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['student', 'tutor'], name='unique_student_tutor_thread')
        ]
        ordering = ['-created_at']

    # def __str__(self):
    #     return f'{self.student} <-> {self.tutor}'

    def other_participant(self, user):
        return self.tutor if user == self.student else self.student


class Message(models.Model):
    thread = models.ForeignKey(ChatThread, related_name='messages', on_delete=models.CASCADE)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='sent_messages', on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.sender}: {self.content[:30]}'