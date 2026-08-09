# chat/consumers.py

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.db.models import Q
from .models import ChatThread, Message
from .serializers import MessageSerializer
from tutors.models import TutorProfile


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        self.thread_id = self.scope['url_route']['kwargs']['thread_id']
        self.group_name = f'chat_{self.thread_id}'
 
        print(f'[DEBUG] connecting user={self.user} authenticated={self.user.is_authenticated} thread_id={self.thread_id}')
 
        if isinstance(self.user, AnonymousUser):
            print('[DEBUG] closing: user is anonymous, token was invalid/expired/missing')
            await self.close(code=4001)
            return
 
        is_participant = await self.user_is_participant()
        print(f'[DEBUG] is_participant={is_participant}')
        if not is_participant:
            print(f'[DEBUG] closing: user {self.user.id} is not student/tutor on thread {self.thread_id}')
            await self.close(code=4003)
            return
 
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        print('[DEBUG] connected successfully')

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({'error': 'invalid JSON'}))
            return

        content = data.get('content', '').strip()
        if not content:
            return

        message = await self.save_message(content)

        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'chat_message',
                'message': MessageSerializer(message).data,
            }
        )

    async def chat_message(self, event):
        # keys must be JSON-serializable. MessageSerializer's output already
        # is, except created_at, which is a date object here since this
        # bypasses DRF's normal response rendering, so stringify it.
        payload = dict(event['message'])
        payload['created_at'] = str(payload['created_at'])
        await self.send(text_data=json.dumps(payload))

    @database_sync_to_async
    def user_is_participant(self):
        user = self.user
        tutor = TutorProfile.objects.filter(user=user).first()
        return ChatThread.objects.filter(id=self.thread_id).filter(
            Q(student=user) | Q(tutor=tutor)
        ).exists()

    @database_sync_to_async
    def save_message(self, content):
        return Message.objects.create(thread_id=self.thread_id, sender=self.user, content=content)