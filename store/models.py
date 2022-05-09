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
    name = models.CharField(max_length=20, null=True)
    price = models.PositiveIntegerField(null=True)
    size = models.CharField(max_length = 3, choices = sizes, null = True)
    quantity = models.PositiveIntegerField(default = 0)
    image = models.FilePathField(null=True)

    def __str__(self):
        return ""

# Table represneting customer data (not used for user authentication)
class customer(models.Model):
    name = models.CharField(max_length = 50, null=True)
    email = models.EmailField(null=True)
    address = models.CharField(max_length = 100, null=True)

    def __str__(self):
        return ""

# Table represnting cart items (to store user carts)
class cart_item(models.Model):
    customer = models.ForeignKey('customer', on_delete = models.CASCADE)
    item = models.ForeignKey('item', on_delete = models.RESTRICT)
    quantity = models.PositiveIntegerField(default=0)

    def __str__(self):
        return ""

# Table specifying order fragements 
class orderling(models.Model):
    main_order = models.ForeignKey('order', on_delete = models.CASCADE)
    item = models.ForeignKey('item', on_delete = models.RESTRICT)
    price = models.PositiveIntegerField(null=True)
    quantity = models.PositiveIntegerField(default=0)

    def __str__(self):
        return ""

# Table seprifying orders
class order(models.Model):
    customer = models.ForeignKey('customer', null = True, on_delete = models.SET_NULL)
    time = models.DateTimeField(null = True)
    def __str__(self):
        return ""