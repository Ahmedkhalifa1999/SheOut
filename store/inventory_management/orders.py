from .. import models
import datetime

class order_item:
    name = ""
    size = ""
    quantity = 0

"""
takes a list or order_item and checks whether the items are avialable in specified quantity
and returns true or false accordingly, ALSO REMOVES CART FROM DATABASE
"""
def record_order(username: str, order: list, address: str) :
    customer_ref = models.customer.objects.filter(email=username)[0]
    db_order = models.order.objects.create(customer=customer_ref, time = datetime.datetime.now(), address = address)
    for item in order:
        item_entries = models.item.objects.filter(name=item.name)
        if (item_entries.exists()):
            item_price = item_entries[0].price
            models.orderling.objects.create(main_order = db_order, item=item_entries[0], size=item.size, quantity=item.quantity, price=item_price)