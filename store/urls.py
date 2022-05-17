from django.urls import path
from . import views


urlpatterns= [
    path('', views.index, name='index'),
    path('shop/', views.view_shop, name='shop'),
    path('item/', views.item, name='item'),
    path('cart/', views.cart, name='cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('about/', views.about, name='about'),
    path('login_register/', views.login_register, name= 'login_register'),
]