# client data ( register user , authenticate user , get personal data)
# product data ( add item to cart , checkout , get cart )

from operator import truediv
from django.contrib.auth import authenticate , login
from django.contrib.auth.models import User

class customer:
    username = None
    password = None

class newcustomer:
    username = None
    password = None
    email = None        
    
        
def register_user(newcustomer):

    User.objects.filter(username = newcustomer.username).exists()
    
    



def authenticate_user(customer):
    user = authenticate(customer.username , customer.password)
    if user is None:
        return False
    else:
        return True    

