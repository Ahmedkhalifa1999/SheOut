import email
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from .. import models


"""
takes a newcustomer object and creates a new user for it in the user authentication system
and a new customer for it in the database
checks if username or email already exist in the database and returns false if they do and true otherwise
"""


def register_user(email, password) -> bool:
    exists = models.customer.objects.filter(email=email).exists()

    if not exists:
        models.customer.objects.create(email=email)
        User.objects.create_user(email, email, password)
    return exists


"""
takes a customer object containing the credneitals of a customer logging in and checks their validity
returns true on valid credentials and false otherwise
"""


def authenticate_user(request, email, password) -> bool:
    user = authenticate(request, username = email,password = password)
    if user is None:
        return False
    else:
        login(request, user)
        return True
