from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from accounts.models import Account
# Create your models here.

class Shop(models.Model):
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=250, unique=True)
    user  = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True)
    location = models.CharField(max_length=200, blank=True)
    description = models.TextField(null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    def get_url(self):
        return reverse('shop_details', args=[self.slug])
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = f"{slugify(self.name)}{slugify(self.user.username)}"
        super().save(*args, **kwargs)
    class Meta:
        verbose_name = 'Shop Branch'
        verbose_name_plural = 'Shop Branches'
        ordering = ('-modified_date', '-date_created')
    
    def __str__(self):
        return self.name



class Category(models.Model):
    category_name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(max_length=300, blank=True)
    cat_image = models.ImageField(upload_to='photos/category', blank=True)

    class Meta:
        verbose_name = 'category'
        verbose_name_plural = 'Categories'


    def get_url(self):
        return reverse('product_by_category', args=[self.slug])

    def __str__(self):
        return self.category_name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.category_name)
        super().save(*args, **kwargs)

class Product(models.Model):
    product_name = models.CharField(max_length=200)
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE)
    slug = models.SlugField(max_length=500, unique=True)
    description = models.TextField(max_length=500, blank=True)
    price = models.DecimalField(max_digits=100, decimal_places=2)
    image = models.ImageField(upload_to='photos/products', default='photos/products/default.png')
    stock = models.IntegerField()
    expire_date = models.DateField(null=True, blank=True)
    buy_price = models.DecimalField(max_digits=100, decimal_places=2, default=0)
    is_available = models.BooleanField(default=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    def get_url(self):
        return reverse('product_detail', args=[self.category.slug, self.slug])

    def __str__(self):
        return self.product_name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug =  slugify(f"{self.product_name} {self.category.category_name} {self.shop.name}") 
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ('-modified_date','-created_date')


class VariationCategory(models.Model):
    name = models.CharField(max_length=250, unique=True)  

    class Meta:
        verbose_name = 'Variation Category'
        verbose_name_plural = 'Variation Categories'

    def __str__(self):
        return self.name

class Variation(models.Model):
    variation_category = models.ForeignKey(VariationCategory, on_delete=models.CASCADE)
    variation_value = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    date_created = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.variation_value
    

class ProductVariation(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variations = models.ManyToManyField(Variation) 
    price = models.DecimalField(max_digits=10, decimal_places=2)  
    stock = models.PositiveIntegerField(null=True)
    is_active = models.BooleanField(default=True)
    date_created = models.DateTimeField(auto_now_add=True, null=True)
    sub_total = models.DecimalField(max_digits=10, decimal_places=2, null=True)

    def __str__(self):
        return f"{self.product} - {' '.join([v.variation_value for v in self.variations.all()])}"
    
    def get_full(self):
        return f"{' '.join([f'{v.variation_category.name}-{v.variation_value}' for v in self.variations.all()])}"
    
    def available_variations(self):
        return self.objects.filter(stock__gt=0)  # Variations with stock available
    
    def save(self, *args, **kwargs):
        if not self.sub_total:
            self.sub_total =  self.price + self.product.price
        super().save(*args, **kwargs)


class ReviewRating(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    user = models.ForeignKey(Account, on_delete=models.CASCADE)
    subject = models.CharField(max_length=100, blank=True)
    review = models.TextField(max_length=500, blank=True)
    rating = models.FloatField()
    ip = models.CharField(max_length=20, blank=True)
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.subject


class ProductGallery(models.Model):
    product = models.ForeignKey(Product, default=None, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='store/products', max_length=255)

    def __str__(self):
        return self.product.product_name

    class Meta:
        verbose_name = 'productgallery'
        verbose_name_plural = 'product gallery'