"""Fixtures for docs/review/reproduce_flows.py.

Run with:  python manage.py shell < docs/review/seed_fixtures.py

Creates two extra items (one with a space in its name, to reproduce F4) and an
auth user that has no matching store.customer row (to reproduce F5). Safe to
run more than once.
"""
from django.contrib.auth.models import User

from store.models import customer, item

item.objects.get_or_create(name="red shirt", defaults={"price": 120, "category": "Shirts"})
item.objects.get_or_create(name="black pants", defaults={"price": 200, "category": "Pants"})

if not User.objects.filter(username="staff@shop.com").exists():
    User.objects.create_user("staff@shop.com", "staff@shop.com", "staffpass123")

print("items:", list(item.objects.values_list("name", "price", "category")))
print("customers:", list(customer.objects.values_list("email", flat=True)))
print("users:", list(User.objects.values_list("username", flat=True)))
