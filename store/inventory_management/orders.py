from .. import models
import time

class order_item:
    name = ""
    size = ""
    quantity = 0

"""
takes a list or order_item and checks whether the items are avialable in specified quantity
and returns true or false accordingly, ALSO REMOVES CART FROM DATABASE
"""
def record_order(username: str, order: list) :
    db_order = models.order.objects.create(customer=username, time = time.now())
    for item in order:
        models.orderling.objects.create(main_order = db_order.id, item=item.name, size=item.size, quantity=item.quantity, price=models.item.objects.filter(name=item.name)[0].price)