from django.db import models


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class Payment(BaseModel):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    GATEWAY_CHOICES = [
        ('stripe', 'Stripe'),
        ('razorpay', 'Razorpay'),
    ]
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    currency = models.CharField(max_length=10, default='INR')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    gateway = models.CharField(max_length=20, choices=GATEWAY_CHOICES)
    order_id = models.CharField(max_length=100)
    metadata = models.JSONField(blank=True, null=True)
    session_id = models.CharField(max_length=255, blank=True, null=True)  # Stripe/Razorpay session/order ID

    def __str__(self):
        return f"{self.gateway} | {self.amount} {self.currency} | {self.status}"

    def latest_transaction(self):
        return self.transactions.order_by('-id').first()

class Transaction(BaseModel):
    TRANSACTION_TYPE_CHOICES = [
        ('payment', 'Payment'),
        ('refund', 'Refund'),
        ('other', 'Other'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]
    payment = models.ForeignKey(Payment, related_name='transactions', on_delete=models.CASCADE)
    type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES, default='payment')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='INR')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    gateway_response = models.JSONField(blank=True, null=True)
    session_id = models.CharField(max_length=255, blank=True, null=True)  # Stripe/Razorpay session/order ID
    receipt_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return f"{self.type} | {self.amount} {self.currency} | {self.status}"
