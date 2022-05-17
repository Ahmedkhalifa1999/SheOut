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
    customer_ref = models.customer.objects.filter(email=username)[0]
    db_order = models.order.objects.create(customer=customer_ref, time = time.now())
    for item in order:
        models.orderling.objects.create(main_order = db_order, item=item.name, size=item.size, quantity=item.quantity, price=models.item.objects.filter(name=item.name)[0].price)