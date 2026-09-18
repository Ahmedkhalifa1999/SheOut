from django.contrib import admin

from .models import CartItem, Order, OrderLine, Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "stock", "created_at")
    list_filter = ("category",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    list_editable = ("price", "stock")


class OrderLineInline(admin.TabularInline):
    model = OrderLine
    extra = 0
    readonly_fields = ("line_total",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status", "created_at", "total")
    list_filter = ("status", "created_at")
    search_fields = ("user__username", "address")
    readonly_fields = ("created_at", "total")
    inlines = [OrderLineInline]


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("user", "product", "size", "quantity", "added_at")
    list_filter = ("size",)
    search_fields = ("user__username", "product__name")
