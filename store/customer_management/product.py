from .. import models
from ..inventory_management.orders import record_order, order_item
from store.models import customer
import datetime 

class cart_item:
    ref: str = ""
    size: str = ""
    quantity: int = 0

    def __init__(self, name, size, quantity):
        self.name = name
        self.size = size
        self.quantity = quantity


"""
takes a customer id and item id and adds respective the specified item to the specified customer's cart
"""
def add_to_cart(username: str, item_name: str, size: str, quantity: int) -> None:
    customer_ref = models.customer.objects.filter(email=username)[0]
    item_ref = models.item.objects.filter(name=item_name)[0]
    models.cart_item.objects.create(customer=customer_ref, item=item_ref, size=size, quantity=quantity)


"""
returns specified customer cart as a list of cart_item objects
"""
def get_cart(username: str) -> list:
    return [cart_item(entry.item.name, entry.size, entry.quantity) for entry in models.cart_item.objects.filter(customer=username)]

    
        

"""
checks if specified customer cart is avaialable using available function imported from inventory_management module
and returns true if it is and false otherwise
"""
def checkout(username: str, address: str) -> bool:
    entries = models.cart_item.objects.filter(customer=username)
    cart = [cart_item(entry.item.name, entry.size, entry.quantity) for entry in entries]
    record_order(username, cart, address)
    entries.delete()
    
