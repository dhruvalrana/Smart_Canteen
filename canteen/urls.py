"""
URL configuration for canteen app.
"""
from django.urls import path
from canteen import views

app_name = 'canteen'

urlpatterns = [
    # ====== HOME & BROWSING ======
    path('', views.home, name='home'),
    path('food/', views.food_list, name='food_list'),
    path('food/<slug:slug>/', views.food_detail, name='food_detail'),

    # ====== AUTHENTICATION ======
    path('register/', views.register, name='register'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('login/', views.login_view, name='login'),
    path('login/verify-otp/', views.login_verify_otp, name='login_verify_otp'),
    path('logout/', views.logout_view, name='logout'),
    path('password-reset-request/', views.password_reset_request, name='password_reset_request'),
    path('password-reset/', views.password_reset, name='password_reset'),

    # ====== CART ======
    path('cart/', views.cart_view, name='cart'),
    path('add-to-cart/<int:item_id>/', views.add_to_cart, name='add_to_cart'),
    path('update-cart-item/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    path('remove-from-cart/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),

    # ====== ORDERS ======
    path('checkout/', views.checkout, name='checkout'),
    path('orders/', views.order_list, name='order_list'),
    path('order/<str:order_id>/', views.order_detail, name='order_detail'),
    path('order/<str:order_id>/cancel/', views.cancel_order, name='cancel_order'),

    # ====== REVIEWS ======
    path('review/add/<slug:slug>/', views.add_review, name='add_review'),

    # ====== USER PROFILE ======
    path('profile/', views.profile_view, name='profile'),
    path('profile/change-email/', views.change_email_request, name='change_email_request'),
    path('profile/change-email/verify/', views.change_email_verify, name='change_email_verify'),

    # ====== ADMIN - DASHBOARD & REPORTS ======
    path('management/dashboard/', views.admin_dashboard, name='admin_dashboard'),

    # ====== ADMIN - FOOD ITEMS ======
    path('management/food-items/', views.manage_food_items, name='manage_items'),
    path('management/food-items/add/', views.add_food_item, name='add_food_item'),
    path('management/food-items/<int:pk>/edit/', views.edit_food_item, name='edit_food_item'),
    path('management/food-items/<int:pk>/delete/', views.delete_food_item, name='delete_food_item'),

    # ====== ADMIN - ORDERS ======
    path('management/orders/', views.manage_orders, name='manage_orders'),
    path('management/orders/<str:order_id>/update/', views.update_order_status, name='update_order_status'),
    path('management/orders/<str:order_id>/', views.admin_order_detail, name='admin_order_detail'),
]
