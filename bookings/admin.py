from django.contrib import admin
from .models import Booking, GoogleOAuthToken


admin.site.register(GoogleOAuthToken)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['id', 'student', 'tutor_profile', 'subject', 'scheduled_date', 'status', 'total_amount']
    list_filter = ['status', 'session_type', 'scheduled_date']
    search_fields = ['student__email', 'tutor_profile__user__email']
    date_hierarchy = 'scheduled_date'
