from .. import models

class filter_parameters:
    name = None
    category = None
    size = None

class item:
    name = None
    price = None
    sizes = None

"""
takes a filter_parameters object and returns list of items matching filter criteria
"""

# hwa hna m3rfnash nst5dm el category 34an msh mawgoda class item l fel models f n3ml eh????
def search(parameters: filter_parameters) -> list:
    items = []
    for temp_item in models.item.objects.filter(name=parameters.name, size = parameters.size):
        item2 = item()
        item2.name = temp_item['name']
        item2.sizes = temp_item['size']
        items.append(item2)

    return items

"""
takes item ID and returns object of type item corresponding to passed item ID
"""
def getItem(name: str) -> item:
    result = models.item.objects.filter(name=name)
    if not result.exists():
        return None
    res = item()
    res.name = name
    res.price = result[0].price
    res.sizes = result[0].size
    return res


