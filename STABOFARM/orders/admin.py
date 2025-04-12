from django.contrib import admin
from .models import Payment, Order, OrderProduct


# Register your models here.


class OrderProductInline(admin.TabularInline):
    model = OrderProduct
    readonly_fields = ('payment', 'user', 'product', 'quantity', 'product_price', 'ordered')
    extra = 0


class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number',  'order_total', 'status', 'is_ordered',
                    'created_at']
    list_filter = ['status', 'is_ordered']
    search_fields = ['order_number',]
    list_per_page = 20
    inlines = [OrderProductInline]

class PymentAdmin(admin.ModelAdmin):
    pass
admin.site.register(Payment, PymentAdmin)
admin.site.register(Order, OrderAdmin)

class OderProductAdmin(admin.ModelAdmin):
    pass
admin.site.register(OrderProduct, OderProductAdmin)