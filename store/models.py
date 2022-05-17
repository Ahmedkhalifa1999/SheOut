from django.db import models

# Table representing items available at shop
class item(models.Model):
    sizes = [
        ('XS', 'XS'),
        ('S', 'S'),
        ('M', 'M'),
        ('L', 'L'),
        ('XL', 'XL'),
        ('XXL', 'XXL')
    ]
    name = models.CharField(max_length=20, primary_key=True, default="")
    price = models.PositiveIntegerField(null=True)
    size = models.CharField(max_length = 3, choices = sizes, null = True)
    quantity = models.PositiveIntegerField(default = 0)

# Table represneting customer data (not used for user authentication)
class customer(models.Model):
    email = models.EmailField(primary_key=True, default="")

    def __str__(self):
        return self.email

# Table represnting cart items (to store user carts)
class cart_item(models.Model):
    customer = models.ForeignKey('customer', on_delete = models.CASCADE)
    item = models.ForeignKey('item', on_delete = models.RESTRICT)
    quantity = models.PositiveIntegerField(default=0)
        
# anhy item alee gwa el order 
# Table specifying order fragements 
class orderling(models.Model):
    main_order = models.ForeignKey('order', on_delete = models.CASCADE)
    item = models.ForeignKey('item', on_delete = models.RESTRICT)
    price = models.PositiveIntegerField(null=True)
    quantity = models.PositiveIntegerField(default=0)

# Table seprifying orders
class order(models.Model):
    customer = models.ForeignKey('customer', null = True, on_delete = models.SET_NULL)
    time = models.DateTimeField(null = True)