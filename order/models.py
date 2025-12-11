from django.db import models
import uuid
from decimal import Decimal
from django.conf import settings
from django.db import models, transaction
from django.utils import timezone
from address.models import Address
from offers.models import Coupon


# ===================== ORDER =====================
def generate_order_id():
    """
    Generate a stable, human-readable order id
    Example: ORD-20250912-8CHAR
    """
    return f"ORD-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"


class Order(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("shipped", "Shipped"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
        ("returned", "Returned"),
        ("out for delivery", "Out for Delivery"),
        
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_id = models.CharField(max_length=50, unique=True, default=generate_order_id, db_index=True)

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders")
    address = models.ForeignKey(Address, null=True, on_delete=models.SET_NULL, related_name="orders", blank=True)

    # Copy fields (to preserve address info even after deletion)
    full_name = models.CharField(max_length=100, null=True, blank=True)
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    district = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    pincode = models.CharField(max_length=10, null=True, blank=True)
    street = models.CharField(max_length=200, null=True, blank=True)
    full_address = models.TextField(null=True, blank=True)


    order_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    coupon = models.ForeignKey(Coupon, null=True, blank=True, on_delete=models.SET_NULL,default = None)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    final_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    payment_method = models.CharField(max_length=30, blank=True, null=True)  # COD, Razorpay, etc.
    delivered_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-order_date"]

    def __str__(self):
        return f"{self.order_id} - {self.user}"

    def recalc_totals(self):
        total = sum(item.total_price for item in self.items.all())
        self.total_amount = total
        self.final_amount = total - self.discount_amount
        self.save(update_fields=["total_amount", "final_amount"])

    # Cancel order
    @transaction.atomic
    def cancel_order(self, reason=None):
        if self.status in ["cancelled", "returned"]:
            return False
        for item in self.items.filter(is_cancelled=False):
            item.cancel_item(reason=reason)
        self.status = "cancelled"
        self.cancelled_at = timezone.now()
        print("Order cancelled:", self.order_id)
        self.save()
        OrderTracking.objects.create(order=self, status="cancelled", note=reason or "Cancelled")
        return True
    
    # Return order
    @transaction.atomic
    def return_order(self, reason=None):
        """
        Returns the remaining (non-returned, non-cancelled) items
        and refunds only their amount. Already returned items will be skipped.
        """

        total_refund = Decimal("0.00")

        # Get items eligible for refund
        items_to_return = self.items.filter(is_returned=False, is_cancelled=False)

        if not items_to_return.exists():
            return Decimal("0.00")  # nothing to return

        # -------- Coupon Redistribution Fix --------
        all_items = self.items.all()
        total_original = sum(i.total_price for i in all_items)

        coupon = self.coupon
        if coupon:
            if coupon.discount_type == "amount":
                total_discount = Decimal(coupon.discount_value)
            elif coupon.discount_type == "percentage":
                total_discount = (Decimal(coupon.discount_value) / 100) * total_original
            else:
                total_discount = Decimal("0.00")
        else:
            total_discount = Decimal("0.00")

        # Loop through items being returned now
        for item in items_to_return:

            # Proportional discount share
            item_discount_share = (item.total_price / total_original) * total_discount
            refund = item.total_price - item_discount_share
            refund = max(Decimal("0.00"), refund)

            total_refund += refund

            # Mark returned
            item.is_returned = True
            item.return_reason = reason
            item.returned_at = timezone.now()
            item.save()

            # Restock item
            variant = item.product_variant
            product = variant.product
            product.stock = models.F("stock") + item.quantity
            product.save(update_fields=["stock"])

        # Update totals
        self.recalc_totals()

        # Update order status
        self.status = "returned"
        self.returned_at = timezone.now()
        self.save()

        return total_refund


   # ===================== CALCULATED TOTAL WITH COUPON =====================
    @property
    def calculated_total(self):
        total = self.total_amount
        if self.coupon:
            if self.coupon.discount_type == 'amount':
                total -= self.coupon.discount_value
            elif self.coupon.discount_type == 'percentage':
                total -= total * (self.coupon.discount_value / 100)
        return max(total,0)  # Ensure total doesn't go negative

# ===================== ORDER ITEM =====================


class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product_variant = models.ForeignKey("product.ProductVariant", on_delete=models.PROTECT)

    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)  # snapshot unit price
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    

    is_cancelled = models.BooleanField(default=False)
    cancel_reason = models.TextField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    is_returned_requested = models.BooleanField(default=False)

    is_returned = models.BooleanField(default=False)
    return_reason = models.TextField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)

    admin_refunded = models.BooleanField(default=False)

    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.total_price = self.price * self.quantity
        super().save(*args, **kwargs)

    @transaction.atomic
    def cancel_item(self, reason=None):
        if self.is_cancelled:
            return False
        self.is_cancelled = True
        self.cancel_reason = reason
        self.cancelled_at = timezone.now()
        self.save()

        # Restock
        product = self.product_variant.product
        product.stock = models.F("stock") + self.quantity
        product.save(update_fields=["stock"])

        OrderTracking.objects.create(order=self.order, status="cancelled", note=reason or "Item cancelled")
        self.order.recalc_totals()
        return True

    @transaction.atomic
    def return_item(self, reason):
        if not reason:
            raise ValueError("Return reason required")
        if self.is_returned:
            return False
        self.is_returned = True
        self.return_reason = reason
        self.returned_at = timezone.now()
        self.save()
        print("Product stock before return:", self.product_variant.product.stock)
        product = self.product_variant.product
        product.stock = models.F("stock") + self.quantity
        product.save(update_fields=["stock"])
        product.refresh_from_db(fields=["stock"])  # ensures updated value in memory
        print("Product stock after return:", product.stock)

        OrderTracking.objects.create(order=self.order, status="returned", note=reason)
        self.order.recalc_totals()
        return True
    @property
    def variant(self):
        return self.product_variant
#====================order return request=====================

class ReturnRequest(models.Model):
    REQUEST_TYPE_CHOICES = [
        ("item", "Item"),
        ("order", "Order"),
    ]
    STATUS_CHOICES = [
        ("requested", "Requested"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("cancelled", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="return_requests")
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE, related_name="return_requests" , null=True, blank=True)
    request_type = models.CharField(max_length=10, choices=REQUEST_TYPE_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="requested")
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    reason = models.TextField()
    requested_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    note = models.TextField(null=True, blank=True, default="")

    class Meta:
        ordering = ["-requested_at"]

    def __str__(self):
        return f"ReturnRequest {self.id} - {self.request_type} - {self.status}"
# ===================== ORDER TRACKING =====================
class OrderTracking(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="trackings")

    status = models.CharField(max_length=30)
    location = models.CharField(max_length=255, blank=True)
    note = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


# ===================== TRANSACTION =====================
class Transaction(models.Model):
    TYPE_CHOICES = [
        ("debit", "Debit"),
        ("credit", "Credit"),
        ("refund", "Refund"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="transactions")

    transaction_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    transaction_status = models.CharField(max_length=30, default="pending")
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    reference = models.CharField(max_length=255, null=True, blank=True)  # Razorpay ID etc.
    processed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)


