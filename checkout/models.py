from django.db import models
from order.models import *
import uuid
  # Adjust the import path if Order is in a different module

# Create your models here.
# ===================== PAYMENT =====================
class Payment(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("success", "Success"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="payment")

    payment_method = models.CharField(max_length=30)  # COD, Razorpay etc.
    payment_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    transaction = models.ForeignKey(Transaction, null=True, blank=True, on_delete=models.SET_NULL)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    paid_at = models.DateTimeField(null=True, blank=True)
    payment_gateway = models.CharField(max_length=50, null=True, blank=True)  # e.g. Razorpay
    refund_status = models.CharField(max_length=30, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
