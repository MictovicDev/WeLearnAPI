from decimal import Decimal

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from bookings.models import Booking
from tutors.models import TutorProfile
from users.models import User


@override_settings(DATABASES={
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
})
class ReviewAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.student = User.objects.create_user(
            email='student@example.com',
            password='strongpassword123',
            first_name='Jane',
            last_name='Student',
            role=User.Role.STUDENT,
        )
        self.tutor_user = User.objects.create_user(
            email='tutor@example.com',
            password='strongpassword123',
            first_name='John',
            last_name='Tutor',
            role=User.Role.TUTOR,
        )
        self.tutor_profile = TutorProfile.objects.create(user=self.tutor_user, bio='Experienced tutor')
        self.booking = Booking.objects.create(
            student=self.student,
            tutor_profile=self.tutor_profile,
            status=Booking.Status.COMPLETED,
            subject='Math',
            title='Algebra lesson',
        )

    def test_student_can_create_review_for_completed_booking(self):
        self.client.force_authenticate(self.student)

        response = self.client.post('/api/v1/reviews/', {
            'booking': self.booking.pk,
            'stars': 5,
            'comment': 'Excellent tutor!',
        }, format='json')

        self.assertEqual(response.status_code, 201, response.json())
        self.assertEqual(response.json()['comment'], 'Excellent tutor!')
        self.assertEqual(response.json()['rating'], 5)

        self.tutor_profile.refresh_from_db()
        self.assertEqual(self.tutor_profile.average_rating, Decimal('5.00'))
        self.assertEqual(self.tutor_profile.total_reviews, 1)
