
from django.contrib import admin

from .models import Product, Category, Shop, Variation, VariationCategory, ProductVariation
# Register your models here.


class ProductAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'price', 'stock', 'category', 'modified_date', 'is_available')
    prepopulated_fields = {'slug': ('product_name',)}
    list_per_page = 20

class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('category_name',)}
    list_display = ('category_name', 'slug',)
    list_per_page = 20

class VariationAdmin(admin.ModelAdmin):
    list_display = ( 'variation_category', 'variation_value', 'is_active')
    list_editable = ('is_active',)
    list_filter = ('variation_category', 'variation_value')
    list_per_page = 20

class ProductVariationAdmin(admin.ModelAdmin):
    list_display = ('product', 'price', 'stock')
    list_filter = ( 'product', 'price')
    list_per_page = 20



admin.site.register(Product, ProductAdmin)
admin.site.register(VariationCategory)
admin.site.register(Variation, VariationAdmin)
admin.site.register(ProductVariation, ProductVariationAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Shop)