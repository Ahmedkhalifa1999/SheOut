from .. import models

class filter_parameters:
    name = ""
    category = None

class item:
    name = None
    price = None

    def __init__(self, name, price):
        self.name = name
        self.price = price

"""
takes a filter_parameters object and returns list of items matching filter criteria
"""

# hwa hna m3rfnash nst5dm el category 34an msh mawgoda class item l fel models f n3ml eh????
def search(parameters: filter_parameters) -> list:
    if parameters.category == None:
        return [item(entry.name, entry.price) for entry in models.item.objects.filter(name__contains = parameters.name)]
    else:
        return [item(entry.name, entry.price) for entry in models.item.objects.filter(name__contains = parameters.name, category = parameters.category)]

"""
takes item ID and returns object of type item corresponding to passed item ID
"""
def getItem(name: str) -> item:
    result = models.item.objects.filter(name=name)
    if not result.exists():
        return None
    required = item(name, result[0].price)
    return required


