from django.shortcuts import redirect, render
from django.http import HttpRequest, HttpResponse

def index(request):
    pass

def shop(request):
    pass

def item(request):
    pass

def cart(request):
    pass

def checkout(request):
    pass

def about(request):
    return render(request, 'about.html')

def login_register(request):
    pass

def base(request: HttpRequest):
    if (request.user.is_authenticated()):
        redirect('index/')
    else:
        redirect('login_register')
