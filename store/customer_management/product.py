import models
from inventory_management.availability import available,order_item
from store.models import customer

class cart_item:
    ID: int = None
    quantity: int = 0


"""
takes a customer id and item id and adds respective the specified item to the specified customer's cart
"""
def add_to_cart(customer_id: int, item_id: int, quantities:int) -> None:
    models.cart_item.objects.create(customer=customer_id,item=item_id,quantity=quantities)


"""
returns specified customer cart as a list of cart_item objects
"""
def get_cart(customer_id: int) -> list:
    for item in models.cart_item.objects.filter(id=customer_id):
        

"""
checks if specified customer cart is avaialable using available function imported from inventory_management module
and returns true if it is and false otherwise
"""

def checkout(customer_id: int) -> bool:
    pass
