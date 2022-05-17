from django.contrib import admin
from .models import *


# Register your models here.
admin.site.register(item)
admin.site.register(customer)
admin.site.register(order)
admin.site.register(orderling)
admin.site.register(cart_item)