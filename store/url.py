from django.urls import path


from store.views import cart, index, shop,checkout,item,about,login_register
from .import views


urlpatterns= [


    path('',views.base, name='base'),
    index(index,views.index, name='index'),
    shop(shop, views.shop, name='shop'),
    item(item, views.item, name='item'),
    cart(cart,views.cart,name='cart'),
    checkout(checkout,views.checkout, name='checkout'),
    about(about,views.about,name='about'),
    login_register(login_register,views.login_register,name= 'login_register')

]