from django.urls import path
from . import views
from .views import favorites_list

urlpatterns = [
    path('', views.home_view, name='home'),
    path('all/', views.product_list, name='product_list'),
    path('cart/', views.cart_view, name='cart_view'),
    path('add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path("ajax/get-attribute-values/", views.get_attribute_values, name="get_attribute_values"),
    path('product/<int:product_id>/rate/', views.rate_product, name='rate_product'),
    path('favorite/<int:product_id>/', views.toggle_favorite, name='toggle_favorite'),
    path("my-favorites/", favorites_list, name="favorites_list"),
    path('cart/update/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    path('checkout/', views.checkout_view, name='checkout'),
    path('checkout/process/', views.process_checkout, name='process_checkout'),
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),
    path("admin/get_attribute_values/", views.get_attribute_values, name="admin_get_attribute_values"),
    path("apply-coupon/", views.apply_coupon_api, name="apply_coupon_api"),
    path('terms_of_service/', views.terms_of_service_view, name='terms_of_service'),
    path('privacy_policy/', views.privacy_policy_view, name='privacy_policy'),
    path('company_profile/', views.company_profile_view, name='company_profile'),
    path('about-us/', views.about_us_view, name='about_us'),
    path('shop/checkout/success/', views.checkout_success, name='checkout_success'),
    path('category/<slug:slug>/', views.category_products, name='category_products'),
    path('order/<int:order_id>/invoice/', views.download_invoice, name='download_invoice'),
    path("my-orders/", views.my_orders, name="my_orders"),

]
