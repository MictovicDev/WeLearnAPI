import django_filters
from .models import TutorProfile, Subject


class TutorProfileFilter(django_filters.FilterSet):
    subject = django_filters.ModelMultipleChoiceFilter(
        field_name='subjects',
        queryset=Subject.objects.all(),
        label='Filter by subject(s)',
    )
    min_rate = django_filters.NumberFilter(field_name='hourly_rate', lookup_expr='gte')
    max_rate = django_filters.NumberFilter(field_name='hourly_rate', lookup_expr='lte')
    min_rating = django_filters.NumberFilter(field_name='average_rating', lookup_expr='gte')
    session_status = django_filters.ChoiceFilter(
    field_name="session_status",
    choices=TutorProfile.TeachingMode.choices,
)
    location = django_filters.CharFilter(field_name='location', lookup_expr='icontains')
    min_experience = django_filters.NumberFilter(field_name='years_of_experience', lookup_expr='gte')

    class Meta:
        model = TutorProfile
        fields = ['subject', 'min_rate', 'max_rate', 'min_rating', 'session_status', 'location', 'min_experience']
