from .. import models
from ..inventory_management.availability import available,order_item
from store.models import customer
import datetime 

class cart_item:
    ID: int = None
    quantity: int = 0


"""
takes a customer id and item id and adds respective the specified item to the specified customer's cart
"""
def add_to_cart(username: str, item_name: str, quantity: int) -> None:
    models.cart_item.objects.create(customer=username, item=item_name, quantity=quantity)


"""
returns specified customer cart as a list of cart_item objects
"""
def get_cart(customer_id: int) -> list:
    items = []
    for item in models.cart_item.objects.filter(id=customer_id):
        item_2 = cart_item()
        item_2.ID = item['id']
        item_2.quantity = item['quantity']
        items.append(item_2)

    return items

    
        

"""
checks if specified customer cart is avaialable using available function imported from inventory_management module
and returns true if it is and false otherwise
"""
def checkout(customer_id: int) -> bool:
    cart = get_cart(customer_id)
    is_available = available(cart)
    if (is_available):
        order = models.order(customer=customer_id, time=datetime.datetime.now())
        order.save()
        for item in cart:
            price = models.item.objects.filter(id=item.id)[0]['price']
            models.orderling.objects.create(main_order = order.id, item = item.ID, price = price, quantity = item.quantity)
        
        
    return is_available
    
