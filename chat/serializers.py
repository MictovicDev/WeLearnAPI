# chat/serializers.py

from rest_framework import serializers
from .models import ChatThread, Message


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'thread', 'sender', 'sender_name', 'content', 'created_at', 'read_at']
        read_only_fields = ['id', 'sender', 'sender_name', 'created_at', 'read_at']


class ChatThreadSerializer(serializers.ModelSerializer):
    other_participant_name = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = ChatThread
        fields = [
            'id', 'student', 'tutor', 'created_at',
            'other_participant_name', 'last_message', 'unread_count',
        ]
        read_only_fields = fields

    def get_other_participant_name(self, obj):
        user = self.context['request'].user
        other = obj.other_participant(user)
        return other.get_full_name() or other.username

    def get_last_message(self, obj):
        last = obj.messages.last()
        return MessageSerializer(last).data if last else None

    def get_unread_count(self, obj):
        user = self.context['request'].user
        return obj.messages.filter(read_at__isnull=True).exclude(sender=user).count()