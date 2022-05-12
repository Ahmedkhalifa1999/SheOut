import models

class order_item:
    ID = None
    quantity = 0

"""
takes a list or order_item and checks whether the items are avialable in specified quantity
and returns true or false accordingly, ALSO REMOVES CART FROM DATABASE
"""
def available(order: list) -> bool:
    obj = order_item()
    for item in order:
        qnt = models.item.objects.filter(id=item.id)[0]['quantity']
        if item.quantity > qnt:
            return False

    ## updating db

    ##msh 3arfen n update the database
    for item in order:
        db_item = models.item.objects.get(id=item.id)
        db_item.quantity -= item.quantity
        db_item.save()
    return True