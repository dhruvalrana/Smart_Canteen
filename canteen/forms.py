"""
Forms for the SmartCanteen application.
All forms with proper validation and Django best practices.
"""
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.utils import timezone
from canteen.models import (
    FoodItem, Cart, CartItem, Order, OrderItem, 
    Review, CustomUser, OTPVerification
)
import re


class UserRegistrationForm(UserCreationForm):
    """
    User registration form with email and password validation.
    Extends Django's UserCreationForm with custom fields and validation.
    """
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address'
        })
    )
    first_name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First name'
        })
    )
    last_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last name'
        })
    )

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply Bootstrap classes to password fields
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Password (min 8 characters)'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm password'
        })

    def clean_email(self):
        """Validate email is unique."""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("This email address is already registered.")
        return email

    def clean_first_name(self):
        """Validate first name."""
        first_name = self.cleaned_data.get('first_name')
        if len(first_name.strip()) == 0:
            raise ValidationError("First name cannot be empty.")
        return first_name

    def clean_password1(self):
        """Validate password strength."""
        password = self.cleaned_data.get('password1')
        
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long.")
        
        if not any(char.isupper() for char in password):
            raise ValidationError("Password must contain at least one uppercase letter.")
        
        if not any(char.isdigit() for char in password):
            raise ValidationError("Password must contain at least one number.")
        
        if not any(char in '!@#$%^&*()_+-=[]{}|;:,.<>?' for char in password):
            raise ValidationError("Password must contain at least one special character.")
        
        return password

    def save(self, commit=True):
        """Save user with email as username."""
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']  # Use email as username
        if commit:
            user.save()
        return user


class OTPVerificationForm(forms.Form):
    """
    Form for OTP verification during registration.
    Simple 6-digit OTP input.
    """
    otp_code = forms.CharField(
        max_length=6,
        min_length=6,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control text-center',
            'placeholder': 'Enter 6-digit OTP',
            'type': 'text',
            'maxlength': '6',
            'pattern': '[0-9]{6}',
            'inputmode': 'numeric',
            'autocomplete': 'one-time-code',
            'aria-label': '6-digit OTP'
        })
    )

    def clean_otp_code(self):
        """Validate OTP is numeric."""
        otp = self.cleaned_data.get('otp_code')
        if not otp.isdigit():
            raise ValidationError("OTP must contain only numbers.")
        return otp


class LoginForm(forms.Form):
    """
    Custom login form.
    Email/username and password authentication.
    """
    email = forms.CharField(
        max_length=254,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email or Username',
            'type': 'text'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )


class PasswordResetRequestForm(forms.Form):
    """
    Form to request password reset via OTP.
    """
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your registered email'
        })
    )

    def clean_email(self):
        """Check if email exists in system."""
        email = self.cleaned_data.get('email')
        if not User.objects.filter(email=email).exists():
            raise ValidationError("No account found with this email address.")
        return email


class PasswordResetForm(forms.Form):
    """
    Form to reset password using OTP.
    """
    otp_code = forms.CharField(
        max_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control text-center',
            'placeholder': 'Enter 6-digit OTP',
            'maxlength': '6',
            'pattern': '[0-9]{6}',
            'inputmode': 'numeric',
            'autocomplete': 'one-time-code'
        })
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'New password'
        })
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm password'
        })
    )

    def clean_new_password(self):
        """Validate new password strength."""
        password = self.cleaned_data.get('new_password')
        
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long.")
        
        if not any(char.isupper() for char in password):
            raise ValidationError("Password must contain at least one uppercase letter.")
        
        if not any(char.isdigit() for char in password):
            raise ValidationError("Password must contain at least one number.")
        
        return password

    def clean(self):
        """Validate passwords match."""
        cleaned_data = super().clean()
        password = cleaned_data.get('new_password')
        confirm = cleaned_data.get('confirm_password')
        
        if password and confirm:
            if password != confirm:
                raise ValidationError("Passwords do not match.")
        
        return cleaned_data


class FoodItemForm(forms.ModelForm):
    """
    Form for admin to add/edit food items.
    Complete CRUD form for food items.
    Supports both file upload and image URL.
    """
    image_url = forms.URLField(
        required=False,
        label='Or Image URL',
        widget=forms.URLInput(attrs={
            'class': 'form-control',
            'placeholder': 'https://example.com/image.jpg',
        }),
        help_text='Paste a direct link to an image (jpg, png, webp, gif). Used only if no file is uploaded.'
    )

    class Meta:
        model = FoodItem
        fields = [
            'name', 'description', 'category', 'price',
            'image', 'availability_status', 'quantity_available',
            'calories', 'ingredients',
            'is_vegetarian', 'is_vegan', 'is_gluten_free'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Food item name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Detailed description',
                'rows': 4
            }),
            'category': forms.Select(attrs={
                'class': 'form-select'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Price in ₹',
                'step': '0.01'
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'availability_status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'quantity_available': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Quantity',
                'min': '0'
            }),
            'calories': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Calories per serving'
            }),
            'ingredients': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Comma-separated ingredients',
                'rows': 3
            }),
            'is_vegetarian': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_vegan': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_gluten_free': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def clean_price(self):
        """Validate price is positive."""
        price = self.cleaned_data.get('price')
        if price and price <= 0:
            raise ValidationError("Price must be greater than zero.")
        return price

    def clean_quantity_available(self):
        """Validate quantity is non-negative."""
        quantity = self.cleaned_data.get('quantity_available')
        if quantity is not None and quantity < 0:
            raise ValidationError("Quantity cannot be negative.")
        return quantity


class AddToCartForm(forms.Form):
    """
    Simple form to add items to cart.
    """
    quantity = forms.IntegerField(
        min_value=1,
        max_value=100,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'value': '1',
            'min': '1',
            'max': '100'
        })
    )


class UpdateCartItemForm(forms.Form):
    """
    Form to update quantity of items in cart.
    """
    quantity = forms.IntegerField(
        min_value=0,
        max_value=100,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0',
            'max': '100'
        })
    )

    def clean_quantity(self):
        """Validate quantity."""
        quantity = self.cleaned_data.get('quantity')
        if quantity == 0:
            # 0 means delete from cart
            return quantity
        if quantity < 1:
            raise ValidationError("Quantity must be at least 1.")
        return quantity


class PlaceOrderForm(forms.ModelForm):
    """
    Form for placing orders.
    Captures order details and special instructions.
    """
    class Meta:
        model = Order
        fields = ['payment_method', 'special_instructions']
        widgets = {
            'payment_method': forms.RadioSelect(attrs={
                'class': 'form-check-input'
            }),
            'special_instructions': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Any special requests? (e.g., no onions, extra spice)',
                'rows': 3
            })
        }


class ReviewForm(forms.ModelForm):
    """
    Form for customers to review food items.
    """
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.RadioSelect(attrs={
                'class': 'form-check-input'
            }),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Share your feedback about this item',
                'rows': 4
            })
        }


class CategoryForm(forms.ModelForm):
    """
    Form for admin to manage categories.
    """
    class Meta:
        model = FoodItem.category.field.related_model
        fields = ['name', 'description', 'icon', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Category name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Category description',
                'rows': 3
            }),
            'icon': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Bootstrap icon class (e.g., bi-cup-hot)'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class OrderStatusUpdateForm(forms.ModelForm):
    """
    Form for admin to update order status.
    """
    class Meta:
        model = Order
        fields = ['status', 'estimated_ready_time']
        widgets = {
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'estimated_ready_time': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
        }


class SearchForm(forms.Form):
    """
    Search form for food items.
    """
    query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search food items...',
            'type': 'search'
        })
    )
    category = forms.ModelChoiceField(
        queryset=FoodItem.objects.values_list('category', flat=True).distinct(),
        required=False,
        empty_label='All Categories',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    sort_by = forms.ChoiceField(
        required=False,
        choices=[
            ('name', 'Name (A-Z)'),
            ('-price', 'Price (Low to High)'),
            ('price', 'Price (High to Low)'),
            ('-created_at', 'Newest First'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )


class UserProfileForm(forms.Form):
    """
    Form for users to update their profile information.
    """
    first_name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First name',
        })
    )
    last_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last name',
        })
    )
    phone_number = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+91 XXXXX XXXXX',
        })
    )

    def clean_first_name(self):
        value = self.cleaned_data.get('first_name', '').strip()
        if not value:
            raise ValidationError("First name cannot be empty.")
        return value

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number', '').strip()
        if phone and not re.match(r'^\+?[\d\s\-]{7,15}$', phone):
            raise ValidationError("Enter a valid phone number.")
        return phone


class ChangeEmailRequestForm(forms.Form):
    """
    Form to request an email address change.
    Validates the new address is not already taken.
    """
    new_email = forms.EmailField(
        label='New Email Address',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your new email address',
        })
    )

    def __init__(self, current_user, *args, **kwargs):
        self.current_user = current_user
        super().__init__(*args, **kwargs)

    def clean_new_email(self):
        email = self.cleaned_data.get('new_email', '').strip().lower()
        if email == self.current_user.email.lower():
            raise ValidationError("The new email is the same as your current email.")
        if User.objects.filter(email__iexact=email).exclude(pk=self.current_user.pk).exists():
            raise ValidationError("This email address is already in use by another account.")
        return email
