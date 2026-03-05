"""
Django admin configuration for SmartCanteen.
Register models for admin panel management.
"""
from django.contrib import admin
from canteen.models import (
    CustomUser, OTPVerification, Category, FoodItem, Cart, CartItem,
    Order, OrderItem, Review, AnnouncementNotification
)


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone_number', 'registration_date', 'is_verified', 'status']
    list_filter = ['status', 'is_verified', 'registration_date']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'phone_number']
    readonly_fields = ['registration_date']


@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'verification_type', 'is_verified', 'created_at', 'attempts']
    list_filter = ['verification_type', 'is_verified', 'created_at']
    search_fields = ['user__email']
    readonly_fields = ['otp_code', 'created_at']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name']


@admin.register(FoodItem)
class FoodItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'availability_status', 'quantity_available', 'created_at']
    list_filter = ['category', 'availability_status', 'is_vegetarian', 'is_vegan', 'is_gluten_free', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'category')
        }),
        ('Pricing & Availability', {
            'fields': ('price', 'availability_status', 'quantity_available')
        }),
        ('Nutritional Information', {
            'fields': ('calories', 'ingredients')
        }),
        ('Dietary Information', {
            'fields': ('is_vegetarian', 'is_vegan', 'is_gluten_free')
        }),
        ('Image & Metadata', {
            'fields': ('image', 'created_by', 'created_at', 'updated_at')
        }),
    )


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['user', 'created_at', 'updated_at']
    search_fields = ['user__email']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['cart', 'food_item', 'quantity', 'added_at']
    list_filter = ['added_at']
    search_fields = ['cart__user__email', 'food_item__name']


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['item_name', 'item_price', 'quantity', 'subtotal']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_id', 'user', 'status', 'total_amount', 'created_at']
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['order_id', 'user__email']
    readonly_fields = ['order_id', 'created_at', 'updated_at', 'completed_at']
    inlines = [OrderItemInline]
    fieldsets = (
        ('Order Information', {
            'fields': ('order_id', 'user', 'status')
        }),
        ('Amounts', {
            'fields': ('subtotal', 'tax', 'discount', 'total_amount')
        }),
        ('Payment & Instructions', {
            'fields': ('payment_method', 'special_instructions')
        }),
        ('Timeline', {
            'fields': ('created_at', 'updated_at', 'estimated_ready_time', 'completed_at')
        }),
    )


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'item_name', 'item_price', 'quantity', 'subtotal']
    list_filter = ['order__created_at']
    search_fields = ['order__order_id', 'item_name']


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['user', 'food_item', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['user__email', 'food_item__name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(AnnouncementNotification)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ['title', 'announcement_type', 'is_active', 'created_at']
    list_filter = ['announcement_type', 'is_active', 'created_at']
    search_fields = ['title', 'message']
    readonly_fields = ['created_at', 'updated_at']
