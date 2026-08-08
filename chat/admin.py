from django.contrib import admin
from .models import ChatThread, Message

# Register your models here.

admin.site.register(ChatThread)
admin.site.register(Message)
