from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import Conversation, Message
from users.serializers import UserSerializer


class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'sender', 'content', 'is_read', 'created_at']
        read_only_fields = ['id', 'sender', 'is_read', 'created_at']


class MessageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['content']


class ConversationSerializer(serializers.ModelSerializer):
    student = UserSerializer(read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['id', 'student', 'tutor_profile', 'booking', 'last_message', 'unread_count', 'updated_at']
        read_only_fields = ['id', 'student', 'updated_at']

    @extend_schema_field(MessageSerializer)
    def get_last_message(self, obj):
        msg = obj.messages.last()
        return MessageSerializer(msg).data if msg else None

    @extend_schema_field(serializers.IntegerField())
    def get_unread_count(self, obj):
        user = self.context['request'].user
        return obj.messages.filter(is_read=False).exclude(sender=user).count()


class ConversationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversation
        fields = ['tutor_profile', 'booking']
