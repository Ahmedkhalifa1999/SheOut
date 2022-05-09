import models
from inventory_management.availability import available

class cart_item:
    ID: int = None
    quantity: int = 0


"""
takes a customer id and item id id and adds respective the specified item to the specified customer's cart
"""
def add_to_cart(customer_id: int, item_id: int) -> None:
    pass

"""
checks if specified customer cart is avaialable using available function imported from inventory_management module
and returns true if it is and false otherwise
"""
def checkout(customer_id: int) -> bool:
    pass

"""
returns specified customer cart as a list of cart_item objects
"""
def get_cart(customer_id: int) -> list:
    pass