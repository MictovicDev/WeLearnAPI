from django.contrib import admin
from .models import Subject, TutorProfile, TutorCertification, TutorVerificationDocument, Availability


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name']


class CertificationInline(admin.TabularInline):
    model = TutorCertification
    extra = 0


class VerificationDocInline(admin.TabularInline):
    model = TutorVerificationDocument
    extra = 0


class AvailabilityInline(admin.TabularInline):
    model = Availability
    extra = 0


@admin.register(TutorProfile)
class TutorProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'verification_status', 'is_verified', 'hourly_rate', 'average_rating', 'total_sessions']
    list_filter = ['verification_status', 'is_verified', 'session_status', 'subjects']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    inlines = [CertificationInline, VerificationDocInline, AvailabilityInline]
    actions = ['approve_tutors', 'reject_tutors']

    def approve_tutors(self, request, queryset):
        queryset.update(verification_status='approved', is_verified=True)
    approve_tutors.short_description = 'Approve selected tutors'

    def reject_tutors(self, request, queryset):
        queryset.update(verification_status='rejected', is_verified=False)
    reject_tutors.short_description = 'Reject selected tutors'
