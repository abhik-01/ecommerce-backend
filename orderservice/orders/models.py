from django.db import models


class Order(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('SHIPPED', 'Shipped'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
    ]
    DELIVERY_STATUS_CHOICES = [
        ('NOT_SHIPPED', 'Not Shipped'),
        ('IN_TRANSIT', 'In Transit'),
        ('DELIVERED', 'Delivered'),
    ]
    user_id = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_id = models.IntegerField(null=True, blank=True)
    delivery_status = models.CharField(max_length=20, choices=DELIVERY_STATUS_CHOICES, default='NOT_SHIPPED')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order {self.id} - User {self.user_id}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product_id = models.IntegerField()
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Item {self.id} for Order {self.order_id}"


class OrderTracking(models.Model):
    STATUS_CHOICES = [
        ('NOT_SHIPPED', 'Not Shipped'),
        ('IN_TRANSIT', 'In Transit'),
        ('DELIVERED', 'Delivered'),
    ]
    order = models.ForeignKey(Order, related_name='tracking', on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    location = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Tracking {self.id} for Order {self.order_id}"
