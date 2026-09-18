from decimal import Decimal

from django.contrib.auth import get_user_model

from store.models import CartItem, Product

User = get_user_model()

PASSWORD = "correct-horse-battery-staple"


def make_user(email="shopper@example.com", password=PASSWORD, **extra):
    return User.objects.create_user(username=email, email=email, password=password, **extra)


def make_product(name="Blue shirt", price="80.00", stock=10, **extra):
    return Product.objects.create(name=name, price=Decimal(price), stock=stock, **extra)


def add_to_cart(user, product, size="M", quantity=1):
    return CartItem.objects.create(user=user, product=product, size=size, quantity=quantity)
