from django.db import models
from accounts.models import Account
from store.models import Product, Shop, ProductVariation


PAYMENT_STATUS = (
        ('Paid', 'Paid'),
        ('Pending', 'Pending'),
    )
STATUS = (
        ('New', 'New'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    )
class Payment(models.Model):
    user = models.ForeignKey(Account, on_delete=models.CASCADE)
    payment_id = models.CharField(max_length=100)
    payment_method = models.CharField(max_length=100)
    amount_paid = models.CharField(max_length=100)  # this is the total amount paid
    status = models.CharField(max_length=100, choices=PAYMENT_STATUS)
    payment_slip = models.ImageField(null=True, upload_to='pyments/%Y/%m/%d')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.payment_id
    class Meta:
        ordering = ('-created_at',)


class Order(models.Model):
    branch = models.ForeignKey(Shop, on_delete=models.CASCADE, null=True)
    user = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True)
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, blank=True, null=True)
    order_number = models.CharField(max_length=20)
    discount_amount = models.FloatField(default=0)
    order_total = models.FloatField()
    status = models.CharField(max_length=10, choices=STATUS, default='New')
    ip = models.CharField(blank=True, max_length=20)
    back_track = models.JSONField(null=True)
    is_ordered = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.first_name

    class Meta:
        ordering = ('-updated_at','-created_at')
    

    def get_order_day(self):
        date = self.created_at.date()
    
    




class OrderProduct(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, blank=True, null=True)
    user = models.ForeignKey(Account, on_delete=models.CASCADE)
    branch = models.ForeignKey(Shop, on_delete=models.SET_NULL, null=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variations = models.ForeignKey(ProductVariation, on_delete=models.SET_NULL, null=True)
    quantity = models.IntegerField()
    product_price = models.FloatField()
    ordered = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.order.order_number

    class Meta:
        ordering = ('-updated_at','-created_at')



