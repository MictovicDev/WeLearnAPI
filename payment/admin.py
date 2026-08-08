from django.contrib import admin
from .models import Transaction, PayoutMethod


# Register your models here.
admin.site.register(Transaction)
admin.site.register(PayoutMethod)
