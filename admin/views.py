from django.utils import timezone
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser

from tutors.models import TutorProfile
from wallets.models import Withdrawal
from .serializers import (
    TutorAdminListSerializer,
    TutorAdminDetailSerializer,
    StudentAdminSerializer,
    WithdrawalAdminListSerializer,
    WithdrawalAdminDetailSerializer,
    AdminActionSerializer,
     WithdrawalAdminListSerializer,
        WithdrawalAdminDetailSerializer,
        WithdrawalActionSerializer,
)
from django.core.exceptions import ValidationError as DjangoValidationError


User = get_user_model()


class AdminViewSet(viewsets.GenericViewSet):
    """
    Single ViewSet for all admin-panel features.
    URL wiring lives in admin/urls.py (not a router) so each
    resource keeps its own clean path under one class.
    """
    permission_classes = [IsAdminUser]

    # ---------------------------------------------------------- Tutors ----

    def tutors_list(self, request):
        qs = TutorProfile.objects.select_related('user').all()

        status_filter = request.query_params.get('verification_status')
        if status_filter:
            qs = qs.filter(verification_status=status_filter)

        search = request.query_params.get('search')
        if search:
            qs = qs.filter(
                Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
                | Q(user__email__icontains=search)
            )

        page = self.paginate_queryset(qs)
        serializer = TutorAdminListSerializer(page if page is not None else qs, many=True)
        return self.get_paginated_response(serializer.data) if page is not None else Response(serializer.data)

    def tutors_detail(self, request, pk=None):
        tutor = get_object_or_404(TutorProfile.objects.select_related('user'), pk=pk)
        return Response(TutorAdminDetailSerializer(tutor).data)

    def tutors_approve(self, request, pk=None):
        tutor = get_object_or_404(TutorProfile, pk=pk)
        serializer = AdminActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tutor.verification_status = TutorProfile.VerificationStatus.APPROVED
        tutor.is_verified = True
        tutor.save(update_fields=['verification_status', 'is_verified', 'updated_at'])

        return Response(TutorAdminDetailSerializer(tutor).data)

    def tutors_reject(self, request, pk=None):
        tutor = get_object_or_404(TutorProfile, pk=pk)
        serializer = AdminActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tutor.verification_status = TutorProfile.VerificationStatus.REJECTED
        tutor.is_verified = False
        tutor.save(update_fields=['verification_status', 'is_verified', 'updated_at'])

        return Response(TutorAdminDetailSerializer(tutor).data)

    # -------------------------------------------------------- Students ----

    def students_list(self, request):
        qs = User.objects.filter(tutor_profile__isnull=True)

        search = request.query_params.get('search')
        if search:
            qs = qs.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(email__icontains=search)
            )

        page = self.paginate_queryset(qs)
        serializer = StudentAdminSerializer(page if page is not None else qs, many=True)
        return self.get_paginated_response(serializer.data) if page is not None else Response(serializer.data)

    def students_detail(self, request, pk=None):
        student = get_object_or_404(User, pk=pk, tutor_profile__isnull=True)
        return Response(StudentAdminSerializer(student).data)

    # ------------------------------------------------------ Withdrawals ---

       # ------------------------------------------------------ Withdrawals ---

    def withdrawals_list(self, request):
        qs = Withdrawal.objects.select_related('wallet__user').prefetch_related('sessions')

        status_filter = request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        page = self.paginate_queryset(qs)
        serializer = WithdrawalAdminListSerializer(page if page is not None else qs, many=True)
        return self.get_paginated_response(serializer.data) if page is not None else Response(serializer.data)

    def withdrawals_detail(self, request, pk=None):
        withdrawal = get_object_or_404(
            Withdrawal.objects.select_related('wallet__user').prefetch_related('sessions', 'session'),
            pk=pk,
        )
        return Response(WithdrawalAdminDetailSerializer(withdrawal).data)

    def withdrawals_approve(self, request, pk=None):
        withdrawal = get_object_or_404(Withdrawal, pk=pk)
        serializer = WithdrawalActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            withdrawal.approve(
                admin_user=request.user,
                payout_reference=serializer.validated_data.get('payout_reference') or None,
                note=serializer.validated_data.get('note') or None,
            )
        except DjangoValidationError as e:
            return Response({'detail': e.message}, status=status.HTTP_400_BAD_REQUEST)

        return Response(WithdrawalAdminDetailSerializer(withdrawal).data)

    def withdrawals_reject(self, request, pk=None):
        withdrawal = get_object_or_404(Withdrawal, pk=pk)
        serializer = WithdrawalActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reason = serializer.validated_data.get('note') or 'Rejected by admin'
        try:
            withdrawal.reject(admin_user=request.user, reason=reason)
        except DjangoValidationError as e:
            return Response({'detail': e.message}, status=status.HTTP_400_BAD_REQUEST)

        return Response(WithdrawalAdminDetailSerializer(withdrawal).data)