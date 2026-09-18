from django.urls import path

from . import views

app_name = "store"

urlpatterns = [
    path("", views.index, name="index"),
    path("shop/", views.product_list, name="product_list"),
    path("item/<slug:slug>/", views.product_detail, name="product_detail"),
    path("about/", views.about, name="about"),
    path("cart/", views.cart, name="cart"),
    path("cart/add/<slug:slug>/", views.cart_add, name="cart_add"),
    path("cart/update/<int:pk>/", views.cart_update, name="cart_update"),
    path("cart/remove/<int:pk>/", views.cart_remove, name="cart_remove"),
    path("checkout/", views.checkout, name="checkout"),
    path("orders/", views.order_list, name="order_list"),
    path("orders/<int:pk>/", views.order_detail, name="order_detail"),
    path("register/", views.register, name="register"),
    path("login/", views.StoreLoginView.as_view(), name="login"),
    path("logout/", views.StoreLogoutView.as_view(), name="logout"),
    path("login_register/", views.legacy_login_register),
]
