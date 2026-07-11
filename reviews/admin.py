from django.contrib import admin
from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['student', 'tutor_profile', 'rating', 'created_at']
    list_filter = ['rating']
    search_fields = ['student__email', 'tutor_profile__user__email']
