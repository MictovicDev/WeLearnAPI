# chat/views.py
#
# REST side of chat: list threads, start/get a thread with someone, and
# load message history. The live exchange of new messages happens over
# the WebSocket consumer, not here.

from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets, mixins
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import ChatThread, Message
from .serializers import ChatThreadSerializer, MessageSerializer
from django.conf import settings
from users.models import User

class ChatThreadViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ChatThreadSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return ChatThread.objects.filter(Q(student=user) | Q(tutor=user))

    @action(methods=['POST'], detail=False, url_path='start')
    def start(self, request):
        """POST {"tutor_id": 5} (called by a student) or {"student_id": 9}
        (called by a tutor). Returns the existing thread if one already
        exists between the pair, otherwise creates it."""
        other_id = request.data.get('tutor_id')
        message = request.data.get('message')
        receiver = get_object_or_404(User, id=int(other_id))
        if not other_id:
            return Response({'detail': 'tutor_id or student_id is required.'}, status=400)

        if 'tutor_id' in request.data:
            student, tutor_id = request.user, other_id
            thread, _ = ChatThread.objects.get_or_create(student=student, tutor_id=tutor_id)
        else:
            return Response({'detail': 'Only student can start the conversation'}, status=400)

        if message:
            Message.objects.create(thread=thread, sender=request.user, content=message)
            
        return Response(ChatThreadSerializer(thread, context={'request': request}).data)

    @action(methods=['GET'], detail=True, url_path='messages')
    def messages(self, request, pk=None):
        """Paginated message history for a thread, oldest first. Also marks
        the other participant's messages as read."""
        thread = self.get_object()
        Message.objects.filter(thread=thread, read_at__isnull=True).exclude(
            sender=request.user
        ).update(read_at=timezone.now())

        qs = thread.messages.all()
        page = self.paginate_queryset(qs)
        serializer = MessageSerializer(page if page is not None else qs, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)