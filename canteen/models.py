"""
Models for the SmartCanteen application.
Database design with proper relationships, validations, and ORM structure.
"""
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxLengthValidator
from django.utils import timezone
from django.utils.text import slugify
from decimal import Decimal
import random
import string


class CustomUser(models.Model):
    """
    Extended user model for additional canteen-specific fields.
    Can be used to replace default Django User model if needed.
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('blocked', 'Blocked'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='canteen_profile')
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    registration_date = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)

    class Meta:
        db_table = 'custom_user'
        verbose_name = 'Custom User'
        verbose_name_plural = 'Custom Users'
        ordering = ['-registration_date']

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username}"

    def is_active_user(self):
        return self.status == 'active' and self.user.is_active


class OTPVerification(models.Model):
    """
    OTP model for email-based verification.
    Handles user registration verification.
    """
    VERIFICATION_TYPE_CHOICES = [
        ('registration', 'Registration'),
        ('password_reset', 'Password Reset'),
        ('email_change', 'Email Change'),
        ('login', 'Login'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='otp_verification')
    otp_code = models.CharField(max_length=6)
    verification_type = models.CharField(
        max_length=20,
        choices=VERIFICATION_TYPE_CHOICES,
        default='registration'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    attempts = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    is_verified = models.BooleanField(default=False)

    class Meta:
        db_table = 'otp_verification'
        verbose_name = 'OTP Verification'
        verbose_name_plural = 'OTP Verifications'
        ordering = ['-created_at']

    def __str__(self):
        return f"OTP for {self.user.email}"

    def is_valid(self, otp_validity_minutes=10):
        """Check if OTP is still valid based on creation time."""
        elapsed_time = (timezone.now() - self.created_at).total_seconds() / 60
        return elapsed_time < otp_validity_minutes

    def increment_attempts(self):
        """Increment failed attempt counter."""
        self.attempts += 1
        self.save()

    def is_max_attempts_exceeded(self, max_attempts=3):
        """Check if maximum attempts exceeded."""
        return self.attempts >= max_attempts

    @staticmethod
    def generate_otp(length=6):
        """Generate random OTP code."""
        return ''.join(random.choices(string.digits, k=length))


class Category(models.Model):
    """
    Food item categories for better organization.
    Examples: Breakfast, Lunch, Snacks, Beverages, Desserts
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Bootstrap icon class")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'category'
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class FoodItem(models.Model):
    """
    Food items available in the canteen.
    Complete model with pricing, availability, and management.
    """
    AVAILABILITY_CHOICES = [
        ('available', 'Available'),
        ('unavailable', 'Unavailable'),
        ('out_of_stock', 'Out of Stock'),
    ]

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True, null=True)
    description = models.TextField()
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        related_name='food_items'
    )
    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    image = models.ImageField(
        upload_to='food_items/',
        null=True,
        blank=True,
        help_text='Upload food image (recommended: 400x300px)'
    )
    availability_status = models.CharField(
        max_length=20,
        choices=AVAILABILITY_CHOICES,
        default='available'
    )
    quantity_available = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)]
    )
    calories = models.IntegerField(
        null=True,
        blank=True,
        help_text="Calories per serving"
    )
    ingredients = models.TextField(
        blank=True,
        null=True,
        help_text="Comma-separated ingredients"
    )
    is_vegetarian = models.BooleanField(default=False)
    is_vegan = models.BooleanField(default=False)
    is_gluten_free = models.BooleanField(default=False)
    
    # Admin tracking
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_food_items'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'food_item'
        verbose_name = 'Food Item'
        verbose_name_plural = 'Food Items'
        ordering = ['category', 'name']
        indexes = [
            models.Index(fields=['availability_status']),
            models.Index(fields=['price']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return f"{self.name} - ₹{self.price}"

    def is_available(self):
        """Check if food item is available for ordering."""
        return (
            self.availability_status == 'available' and
            self.quantity_available > 0
        )

    def update_availability(self):
        """Auto-update availability based on quantity."""
        if self.quantity_available <= 0:
            self.availability_status = 'out_of_stock'
        else:
            self.availability_status = 'available'
        self.save()

    def save(self, *args, **kwargs):
        """
        Generate a unique, SEO-friendly slug from the name if not provided.
        Ensures existing slugs are preserved and avoids collisions.
        """
        if not self.slug and self.name:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1

            while FoodItem.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            self.slug = slug

        super().save(*args, **kwargs)


class Cart(models.Model):
    """
    Shopping cart model.
    Tracks user's cart items before checkout.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='cart'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cart'
        verbose_name = 'Cart'
        verbose_name_plural = 'Carts'

    def __str__(self):
        return f"Cart of {self.user.username}"

    def get_total_items(self):
        """Get total number of items in cart."""
        return sum(item.quantity for item in self.items.all())

    def get_total_price(self):
        """Calculate total price of cart items."""
        return sum(item.get_subtotal() for item in self.items.all())

    def clear(self):
        """Clear all items from cart."""
        self.items.all().delete()


class CartItem(models.Model):
    """
    Individual items in the shopping cart.
    Links food items with quantities to cart.
    """
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items'
    )
    food_item = models.ForeignKey(
        FoodItem,
        on_delete=models.CASCADE,
        related_name='cart_items'
    )
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)]
    )
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cart_item'
        verbose_name = 'Cart Item'
        verbose_name_plural = 'Cart Items'
        unique_together = ['cart', 'food_item']
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.food_item.name} x {self.quantity}"

    def get_subtotal(self):
        """Calculate subtotal for this cart item."""
        return self.food_item.price * self.quantity


class Order(models.Model):
    """
    Order model representing customer orders.
    Comprehensive tracking of order lifecycle.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready for Pickup'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash Payment'),
        ('card', 'Card Payment'),
        ('upi', 'UPI'),
        ('wallet', 'Wallet'),
    ]

    # Relationships
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='orders'
    )

    # Order identification
    order_id = models.CharField(max_length=20, unique=True, db_index=True)

    # Order details
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='cash'
    )
    
    # Pricing
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    tax = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    # Special requests
    special_instructions = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    estimated_ready_time = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'order'
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_id']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Order {self.order_id} - {self.user.username}"

    @staticmethod
    def generate_order_id():
        """Generate unique order ID in format: ORD20240101001."""
        import datetime
        date_str = datetime.datetime.now().strftime('%Y%m%d')
        random_num = random.randint(100, 999)
        return f"ORD{date_str}{random_num}"

    def calculate_total(self, tax_percentage=5):
        """Calculate total amount with tax."""
        self.tax = (self.subtotal * Decimal(tax_percentage)) / Decimal('100')
        self.total_amount = self.subtotal + self.tax - self.discount
        return self.total_amount

    def mark_as_completed(self):
        """Mark order as completed."""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()

    def can_cancel(self):
        """Check if order can be cancelled."""
        cancellable_statuses = ['pending', 'confirmed']
        return self.status in cancellable_statuses

    def cancel_order(self):
        """Cancel the order."""
        if self.can_cancel():
            self.status = 'cancelled'
            self.save()
            return True
        return False


class OrderItem(models.Model):
    """
    Individual items in an order.
    Snapshot of food item at the time of order.
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    food_item = models.ForeignKey(
        FoodItem,
        on_delete=models.SET_NULL,
        null=True,
        related_name='order_items'
    )
    
    # Snapshot data (capture price at order time)
    item_name = models.CharField(max_length=200)
    item_price = models.DecimalField(max_digits=8, decimal_places=2)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    
    # Calculated fields
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'order_item'
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'
        ordering = ['order']

    def __str__(self):
        return f"{self.item_name} x {self.quantity}"

    def save(self, *args, **kwargs):
        """Override save to auto-calculate subtotal."""
        self.subtotal = self.item_price * self.quantity
        super().save(*args, **kwargs)


class Review(models.Model):
    """
    Customer reviews and ratings for food items.
    Helps maintain quality and customer feedback.
    """
    RATING_CHOICES = [
        (1, '1 - Poor'),
        (2, '2 - Fair'),
        (3, '3 - Good'),
        (4, '4 - Very Good'),
        (5, '5 - Excellent'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    food_item = models.ForeignKey(FoodItem, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(choices=RATING_CHOICES)
    comment = models.TextField(blank=True, null=True, max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'review'
        verbose_name = 'Review'
        verbose_name_plural = 'Reviews'
        unique_together = ['user', 'food_item']
        ordering = ['-created_at']

    def __str__(self):
        return f"Review by {self.user.username} for {self.food_item.name}"


class AnnouncementNotification(models.Model):
    """
    Admin announcements and notifications to users.
    Keep customers updated about special items, closures, etc.
    """
    title = models.CharField(max_length=200)
    message = models.TextField()
    announcement_type = models.CharField(
        max_length=20,
        choices=[
            ('info', 'Information'),
            ('warning', 'Warning'),
            ('promotion', 'Promotion'),
            ('closure', 'Closure'),
        ],
        default='info'
    )
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'announcement'
        verbose_name = 'Announcement'
        verbose_name_plural = 'Announcements'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def is_expired(self):
        """Check if announcement is expired."""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
