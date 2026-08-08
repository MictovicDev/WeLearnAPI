# chat/routing.py

from django.urls import re_path
from .consumers import ChatConsumer

websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<thread_id>\d+)/$', ChatConsumer.as_asgi()),
]


# chat/urls.py (regular REST urls, separate from the websocket routing above)

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ChatThreadViewSet

router = DefaultRouter()
router.register('threads', ChatThreadViewSet, basename='chat-thread')

urlpatterns = [
    path('', include(router.urls)),
]

# Resulting REST endpoints (mounted at /api/chat/ below):
#   GET  /api/chat/threads/                 list my threads
#   GET  /api/chat/threads/<id>/            thread detail
#   POST /api/chat/threads/start/           get-or-create a thread
#   GET  /api/chat/threads/<id>/messages/   paginated history, marks as read
#
# WebSocket endpoint (routed via asgi.py, not this file):
#   wss://yourapp.com/ws/chat/<thread_id>/?token=<auth_token>
#
# In your project's root urls.py:
# path('api/chat/', include('chat.urls')),