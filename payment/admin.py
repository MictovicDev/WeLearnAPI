from django.contrib import admin
from .models import Transaction, PayoutMethod, Payment


# Register your models here.
admin.site.register(Transaction)
admin.site.register(PayoutMethod)
admin.site.register(Payment)
