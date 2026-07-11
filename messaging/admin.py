from django.contrib import admin
from .models import Conversation, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ['sender', 'content', 'is_read', 'created_at']


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['student', 'tutor_profile', 'updated_at']
    search_fields = ['student__email', 'tutor_profile__user__email']
    inlines = [MessageInline]
