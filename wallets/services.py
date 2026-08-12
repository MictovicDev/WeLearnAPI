# wallets/services.py
from decimal import Decimal

from django.db import transaction

from wallets.models import Wallet, WalletTransaction


class InsufficientFundsError(Exception):
    pass


class WalletService:
    @transaction.atomic
    def credit(self, wallet: Wallet, amount: Decimal, reference: str = "", description: str = "") -> WalletTransaction:
        wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)
        wallet.balance += amount
        wallet.save(update_fields=["balance", "updated_at"])

        return WalletTransaction.objects.create(
            wallet=wallet,
            type=WalletTransaction.Type.CREDIT,
            amount=amount,
            balance_after=wallet.balance,
            reference=reference,
            description=description,
        )

    @transaction.atomic
    def debit(self, wallet: Wallet, amount: Decimal, reference: str = "", description: str = "") -> WalletTransaction:
        wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)
        if wallet.balance < amount:
            raise InsufficientFundsError(f"Wallet {wallet.pk} has insufficient funds")

        wallet.balance -= amount
        wallet.save(update_fields=["balance", "updated_at"])

        return WalletTransaction.objects.create(
            wallet=wallet,
            type=WalletTransaction.Type.DEBIT,
            amount=amount,
            balance_after=wallet.balance,
            reference=reference,
            description=description,
        )