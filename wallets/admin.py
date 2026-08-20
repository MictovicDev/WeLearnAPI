from django.contrib import admin
from .models import Wallet, WalletTransaction, Withdrawal

admin.site.register(Wallet)
admin.site.register(WalletTransaction)
admin.site.register(Withdrawal)
