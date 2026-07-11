from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import Conversation, Message
from .serializers import (
    ConversationSerializer,
    ConversationCreateSerializer,
    MessageSerializer,
    MessageCreateSerializer,
)


@extend_schema(tags=['Messaging'])
@extend_schema_view(
    list=extend_schema(
        summary='List my conversations',
        description='Returns all conversations for the authenticated user, ordered by most recent activity.',
    ),
    create=extend_schema(
        summary='Start a conversation',
        description='Student only. Initiate a conversation with a tutor. Returns existing conversation if one already exists.',
        request=ConversationCreateSerializer,
        responses={201: ConversationSerializer},
    ),
    messages=extend_schema(
        summary='List messages in a conversation',
        description='Returns all messages in a conversation. Marks all unread messages from the other party as read.',
    ),
    send_message=extend_schema(
        summary='Send a message',
        description='Send a message in an existing conversation.',
        request=MessageCreateSerializer,
        responses={201: MessageSerializer},
    ),
)
class ConversationViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Conversation.objects.none()
        user = self.request.user
        if user.role == 'tutor':
            return Conversation.objects.filter(tutor_profile__user=user).select_related('student', 'tutor_profile__user')
        return Conversation.objects.filter(student=user).select_related('student', 'tutor_profile__user')

    def get_serializer_class(self):
        if self.action == 'create':
            return ConversationCreateSerializer
        return ConversationSerializer

    def create(self, request, *args, **kwargs):
        serializer = ConversationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tutor_profile = serializer.validated_data['tutor_profile']
        booking = serializer.validated_data.get('booking')
        conversation, created = Conversation.objects.get_or_create(
            student=request.user,
            tutor_profile=tutor_profile,
            defaults={'booking': booking},
        )
        out = ConversationSerializer(conversation, context={'request': request})
        return Response(out.data, status=201 if created else 200)

    @action(methods=['GET'], detail=True, url_path='messages')
    def messages(self, request, pk=None):
        conversation = self.get_object()
        # Mark incoming messages as read
        conversation.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
        msgs = conversation.messages.all()
        return Response(MessageSerializer(msgs, many=True, context={'request': request}).data)

    @action(methods=['POST'], detail=True, url_path='messages/send')
    def send_message(self, request, pk=None):
        conversation = self.get_object()
        serializer = MessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        msg = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            content=serializer.validated_data['content'],
        )
        conversation.save()  # touches updated_at to bubble to top of list
        return Response(MessageSerializer(msg, context={'request': request}).data, status=201)
