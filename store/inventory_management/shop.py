import models

class filter_parameters:
    name = None
    category = None
    size = None

class item:
    name = None
    price = None
    image = None
    sizes = None

"""
takes a filter_parameters object and returns list of items matching filter criteria
"""
def search(parameters: filter_parameters) -> list:
    items = []
    models.item.objects.filter(name=parameters.name)

"""
takes item ID and returns object of type item corresponding to passed item ID
"""
def getItem(ID: int) -> item:
    pass

