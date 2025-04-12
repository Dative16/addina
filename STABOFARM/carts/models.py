from django.db import models
from store.models import ProductVariation, Product
from accounts.models import Account
from datetime import timedelta, date, timezone

class Cart(models.Model):
    cart_id = models.CharField(max_length=250, blank=True)
    date_added = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.cart_id


class CartItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True)
    user = models.ForeignKey(Account, on_delete=models.CASCADE, null=True)
    product_variation = models.ForeignKey(ProductVariation, on_delete=models.CASCADE)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, null=True)
    quantity = models.IntegerField()
    is_active = models.BooleanField(default=True)
    discount_amount = models.PositiveSmallIntegerField(default=0)

    def sub_total(self):
        variation_price = self.product_variation.sub_total
        return variation_price * self.quantity


    def __unicode__(self):
        return self.product
    
    def __str__(self):
        if self.user:
            return self.user.username
        return str(self.product_variation)
    

# FIXME ============== DISCOUNT SECTION ================


class BulkDiscount(models.Model):
    """
    • To Create a BulkDiscount model to define the discount thresholds.
    • Modify the order system to check if a product's quantity qualifies for a discount.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    min_quantity = models.IntegerField()  # Minimum quantity to qualify for the discount
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2)

    def __str__(self):
        return f"{self.product.product_name} - {self.min_quantity}+ - {self.discount_percentage}% off"



class ExpiryDiscount(models.Model):
    """
    • Calculate the number of days left before expiration.
    • Offer a discount if the expiration is within a certain period (e.g., 30 days).
    """

    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    days_before_expiry = models.IntegerField()  # Number of days before expiry to apply discount
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2)

    def __str__(self):
        return f"{self.product.product_name} - {self.days_before_expiry} days before expiry - {self.discount_percentage}% off"
    
class Coupon(models.Model):
    """
    • Create a Coupon model to manage coupon codes.
    • Validate and apply the coupon during checkout.
    """
    code = models.CharField(max_length=50, unique=True)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    valid_from = models.DateField()
    valid_to = models.DateField()
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.code   

class Promotion(models.Model):
    """
    Create promotions valid for specific time periods (e.g., Black Friday or seasonal discounts).
    • Add a Promotion model with a start and end time.
    • Apply the promotion if the current time falls within the valid period.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()

    def __str__(self):
        return f"{self.product.product_name} - {self.discount_percentage}% off"


class ClearanceDiscount(models.Model):
    """
    Offer discounts on products that are overstocked or slow-moving.
    • Add a ClearanceDiscount model based on stock levels.
    • Automatically apply the discount if the stock is greater than a threshold.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    min_stock = models.IntegerField()  # Apply discount if stock exceeds this level
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2)

    def __str__(self):
        return f"{self.product.product_name} - {self.discount_percentage}% off"

# 
class Customer(models.Model):
    user = models.OneToOneField(Account, on_delete=models.CASCADE)
    membership_level = models.CharField(max_length=100, choices=[('bronze', 'Bronze'), ('silver', 'Silver'), ('gold', 'Gold')])

    def __str__(self) -> str:
        return f"{self.user.first_name} - {self.membership_level}"

class MembershipDiscount(models.Model):
    """
    Offer personalized discounts based on loyalty, purchase history, or membership.
    """
    level = models.CharField(max_length=100)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2)

    def __str__(self) -> str:
        return f"{self.level} - {self.discount_percentage}"


class CustomerDiscount(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    membership = models.ForeignKey(MembershipDiscount, on_delete=models.CASCADE, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.customer.user.first_name +" - "+str(self.membership.level)


class DiscountRule(models.Model):
    name = models.CharField(max_length=100)
    condition_type = models.CharField(max_length=50, choices=[('quantity', 'Quantity'), ('expiry', 'Expiry Date')])
    condition_value = models.IntegerField()  # For quantity or days before expiry
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2)

    def is_applicable(self, product, quantity):
        if self.condition_type == 'quantity':
            return quantity >= self.condition_value
        elif self.condition_type == 'expiry':
            days_to_expiry = (product.expire_date - timezone.now().date()).days
            return days_to_expiry <= self.condition_value
        return False

    def calculate_discount(self, quantity):
        if quantity >= self.min_quantity or self.is_expiry_discount():
            return (self.discount_percentage / 100) * self.product.price
        return 0
    
    def __str__(self) -> str:
        return self.name

class DiscountApproval(models.Model):
    employee = models.ForeignKey(Account, on_delete=models.CASCADE)
    discount = models.ForeignKey(DiscountRule, on_delete=models.CASCADE)
    is_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(Account, related_name='approved_by', null=True, blank=True, on_delete=models.SET_NULL)
    requested_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return self.approved_by.first_name +" - "+ str(self.is_approved)