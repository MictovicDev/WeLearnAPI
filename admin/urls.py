from django.urls import path
from .views import AdminViewSet, AdminLoginView

app_name = 'admin_panel'

urlpatterns = [
    # Tutors
    path('tutors/', AdminViewSet.as_view({'get': 'tutors_list'}), name='tutors-list'),
    path('tutors/<int:pk>/', AdminViewSet.as_view({'get': 'tutors_detail'}), name='tutors-detail'),
    path('tutors/<int:pk>/approve/', AdminViewSet.as_view({'post': 'tutors_approve'}), name='tutors-approve'),
    path('tutors/<int:pk>/reject/', AdminViewSet.as_view({'post': 'tutors_reject'}), name='tutors-reject'),

    # Students
    path('students/', AdminViewSet.as_view({'get': 'students_list'}), name='students-list'),
    path('students/<int:pk>/', AdminViewSet.as_view({'get': 'students_detail'}), name='students-detail'),
    path(
        "login/",
        AdminLoginView.as_view(),
        name="admin-login",
    ),
    # Withdrawals
    path('withdrawals/', AdminViewSet.as_view({'get': 'withdrawals_list'}), name='withdrawals-list'),
    path('withdrawals/<int:pk>/', AdminViewSet.as_view({'get': 'withdrawals_detail'}), name='withdrawals-detail'),
    path('withdrawals/<int:pk>/approve/', AdminViewSet.as_view({'post': 'withdrawals_approve'}), name='withdrawals-approve'),
    path('withdrawals/<int:pk>/reject/', AdminViewSet.as_view({'post': 'withdrawals_reject'}), name='withdrawals-reject'),
]