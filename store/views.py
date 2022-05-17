from django.shortcuts import redirect, render
from django.http import HttpRequest, HttpResponse
from .inventory_management import orders, shop
from .customer_management import customer, product

def index(request: HttpRequest):
    if not request.user.is_authenticated:
        return redirect('/login_register/')
    return render(request, 'index.html')

def view_shop(request: HttpRequest):
    if not request.user.is_authenticated:
        return redirect('/login_register/')
    parameters = shop.filter_parameters()
    item_list = shop.search(parameters)
    context = {
        'item_list': item_list,
        'count' : len(item_list)
    }
    return render(request, 'shop.html', context)


def item(request: HttpRequest):
    if not request.user.is_authenticated:
        return redirect('/login_register/')
    if request.method == 'POST':
        product.add_to_cart(request.user.username, request.POST['item_name'], request.POST['size'], request.POST['quantity'])
        return redirect('/shop')

    item = shop.getItem(request.GET['name'])
    if item == None:
        return redirect('/shop')
    context = {
        'name' : item.name,
        'price' : item.price,
        'image' : "product_images/" + item.name + ".png"
    }
    return render(request, 'shop-detail.html', context)

def cart(request: HttpRequest):
    if not request.user.is_authenticated:
        return redirect('/login_register/')
    cart = product.get_cart(request.user.username)
    context = {
        'cart' : cart
    }
    return render(request, 'cart.html', context)

def checkout(request: HttpRequest):
    if not request.user.is_authenticated:
        return redirect('/login_register/')
    if request.method == 'POST':
        product.checkout(request.user.username)
        return redirect('/')
    else:
        return render(request, 'checkout.html')

def about(request: HttpRequest):
    if not request.user.is_authenticated:
        return redirect('/login_register/')
    return render(request, 'about.html')

def login_register(request: HttpRequest):
    if request.method == 'POST':
        if request.POST['which'] == 'register':
            customer.register_user(request.POST['email'], request.POST['password'])
            customer.authenticate_user(request, request.POST['email'], request.POST['password'])
            return redirect('/')
        else:
            if (customer.authenticate_user(request, request.POST['email'], request.POST['password'])):
                return redirect('/')
            else:
                return redirect('/login_register/')
    else:
        return render(request, 'login-register.html')
