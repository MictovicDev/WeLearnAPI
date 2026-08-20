# models.py
from django.db import models, transaction
from django.core.exceptions import ValidationError
from decimal import Decimal
from django.conf import settings
from bookings.models import Booking


class Wallet(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wallet"
    )
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=10, default="usd")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} wallet ({self.balance} {self.currency})"


class WalletTransaction(models.Model):
    class Type(models.TextChoices):
        CREDIT = "credit", "Credit"
        DEBIT = "debit", "Debit"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="transactions")
    type = models.CharField(max_length=10, choices=Type.choices)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.COMPLETED)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    reference = models.CharField(max_length=255, blank=True, null=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.type} {self.amount} → {self.wallet}"


class Withdrawal(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"        # awaiting admin review
        APPROVED = "approved", "Approved"      # approved, payout in progress
        PAID = "paid", "Paid"                  # payout confirmed
        REJECTED = "rejected", "Rejected"      # admin declined, funds refunded
        FAILED = "failed", "Failed"            # approved but payout failed

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, blank=True, null=True,related_name="withdrawals")
    sessions = models.ManyToManyField(
        "bookings.Booking", related_name="withdrawals", blank=True
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    session = models.ForeignKey(Booking, on_delete=models.CASCADE, blank=True, null=True)
    # linked to the WalletTransaction created when funds were reserved
    transaction = models.OneToOneField(
        WalletTransaction, on_delete=models.SET_NULL, null=True, blank=True, related_name="withdrawal"
    )

    # payout destination — adapt to whatever payout method you use
    payout_reference = models.CharField(max_length=255, blank=True, null=True)  # e.g. Stripe transfer id
    admin_note = models.CharField(max_length=500, blank=True, null=True)
    account_name = models.CharField(max_length=250, blank=True, null=True)
    bank_name = models.CharField(max_length=250, blank=True, null=True)
    account_number = models.CharField(max_length=250, blank=True, null=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="processed_withdrawals"
    )

    class Meta:
        ordering = ["-requested_at"]

    def __str__(self):
        return f"Withdrawal {self.amount} ({self.status}) - {self.wallet.user}"

    # ---- core state transitions ----

    @classmethod
    def request(cls, wallet, amount, sessions=None, description="Withdrawal request"):
        if amount <= 0:
            raise ValidationError("Withdrawal amount must be greater than zero.")

        with transaction.atomic():
            wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)

            if amount > wallet.balance:
                raise ValidationError("Insufficient wallet balance.")

            wallet.balance -= amount
            wallet.save(update_fields=["balance", "updated_at"])

            txn = WalletTransaction.objects.create(
                wallet=wallet,
                type=WalletTransaction.Type.DEBIT,
                status=WalletTransaction.Status.PENDING,
                amount=amount,
                balance_after=wallet.balance,
                description=description,
            )

            withdrawal = cls.objects.create(
                wallet=wallet, amount=amount, transaction=txn, status=cls.Status.PENDING
            )
            if sessions:
                withdrawal.sessions.set(sessions)
            return withdrawal

    def approve(self, admin_user, payout_reference=None, note=None):
        """Admin approves — marks approved, ready for payout processing."""
        if self.status != self.Status.PENDING:
            raise ValidationError(f"Cannot approve a withdrawal with status '{self.status}'.")

        with transaction.atomic():
            self.status = self.Status.APPROVED
            self.processed_by = admin_user
            self.processed_at = models.functions.Now()
            if payout_reference:
                self.payout_reference = payout_reference
            if note:
                self.admin_note = note
            self.save()

    def mark_paid(self, payout_reference=None):
        """Call this once the actual payout (bank transfer / Stripe payout / etc) succeeds."""
        if self.status not in (self.Status.APPROVED, self.Status.PENDING):
            raise ValidationError(f"Cannot mark '{self.status}' withdrawal as paid.")

        with transaction.atomic():
            self.status = self.Status.PAID
            if payout_reference:
                self.payout_reference = payout_reference
            self.save()

            if self.transaction:
                self.transaction.status = WalletTransaction.Status.COMPLETED
                self.transaction.save(update_fields=["status"])

    def reject(self, admin_user, reason):
        if self.status != self.Status.PENDING:
            raise ValidationError(f"Cannot reject a withdrawal with status '{self.status}'.")

        with transaction.atomic():
            wallet = Wallet.objects.select_for_update().get(pk=self.wallet_id)
            wallet.balance += self.amount
            wallet.save(update_fields=["balance", "updated_at"])

            WalletTransaction.objects.create(
                wallet=wallet,
                type=WalletTransaction.Type.CREDIT,
                status=WalletTransaction.Status.COMPLETED,
                amount=self.amount,
                balance_after=wallet.balance,
                description=f"Refund for rejected withdrawal #{self.pk}",
            )

            if self.transaction:
                self.transaction.status = WalletTransaction.Status.FAILED
                self.transaction.save(update_fields=["status"])

            self.sessions.clear()  # free these sessions up for another withdrawal request
            self.status = self.Status.REJECTED
            self.processed_by = admin_user
            self.admin_note = reason
            self.save()

    def mark_failed(self, admin_user=None, reason=None):
        """Approved but payout failed on the processor side — refund too."""
        if self.status != self.Status.APPROVED:
            raise ValidationError(f"Cannot fail a withdrawal with status '{self.status}'.")

        with transaction.atomic():
            wallet = Wallet.objects.select_for_update().get(pk=self.wallet_id)
            wallet.balance += self.amount
            wallet.save(update_fields=["balance", "updated_at"])

            WalletTransaction.objects.create(
                wallet=wallet,
                type=WalletTransaction.Type.CREDIT,
                status=WalletTransaction.Status.COMPLETED,
                amount=self.amount,
                balance_after=wallet.balance,
                description=f"Refund for failed withdrawal #{self.pk}",
            )

            self.status = self.Status.FAILED
            if admin_user:
                self.processed_by = admin_user
            if reason:
                self.admin_note = reason
            self.save()