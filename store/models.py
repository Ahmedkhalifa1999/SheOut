from django.db import models
from django.forms import IntegerField

# Create your models here.
class item(models.Model):
    id=models.IntegerField(max_length=200)
    name= models.CharField(max_length=200)
    price=models.IntegerField(max_length=500)
    color=models.CharField(max_length=100)
    size=models.IntegerField(max_length=100)

class customer(models.Model):
    name=models.CharField(max_length=100)
    password=models.IntegerField(max_length=500)
    cart=models.CharField(max_length=1000000)

#class cart(models.Model):