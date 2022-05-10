import email
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
import models


class customer:
    username: str = None
    password: str = None


class newcustomer:
    username: str = None
    password: str = None
    email: str = None
    address: str = None


"""
takes a newcustomer object and creates a new user for it in the user authentication system
and a new customer for it in the database
checks if username or email already exist in the database and returns false if they do and true otherwise
"""


def register_user(newcustomer: newcustomer) -> bool:

    is_available = User.objects.filter(username=newcustomer.username).exists()
    is_available = is_available & models.customer.objects.filter(email=newcustomer.email).exists()
    is_available = not is_available  
    if is_available:
        # lw ha3ml el satr alee gy dah lazm azwd password fe el database + msh 3rfen eh el sa7 3shan fathy myz3lsh
        models.customer.objects.create(name=newcustomer.username, email=newcustomer.email, address=newcustomer.address)
        customer.username = newcustomer.username
        customer.password = newcustomer.password
    return is_available


"""
takes a customer object containing the credneitals of a customer logging in and checks their validity
returns true on valid credentials and false otherwise
"""


def authenticate_user(customer: customer) -> bool:
    user = authenticate(customer.username, customer.password)
    if user is None:
        return False
    else:
        return True
