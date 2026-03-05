"""
Views for the SmartCanteen application.
User and Admin modules with proper authentication and authorization.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.http import JsonResponse, HttpResponseRedirect
from django.core.mail import send_mail
from django.conf import settings
from django.views.decorators.http import require_POST, require_GET
from django.db.models import Q, Sum, Count, Avg
from django.core.paginator import Paginator
from django.core.files.base import ContentFile
from decimal import Decimal
from datetime import timedelta
import urllib.request
import urllib.parse
import io
import os

from canteen.models import (
    FoodItem, Cart, CartItem, Order, OrderItem, CustomUser,
    OTPVerification, Category, Review, AnnouncementNotification
)
from canteen.forms import (
    UserRegistrationForm, OTPVerificationForm, LoginForm,
    PasswordResetRequestForm, PasswordResetForm, FoodItemForm,
    AddToCartForm, UpdateCartItemForm, PlaceOrderForm,
    ReviewForm, OrderStatusUpdateForm, UserProfileForm,
    ChangeEmailRequestForm
)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def is_admin_user(user):
    """Check if user is admin."""
    return user.is_staff or user.is_superuser


def send_otp_email(user, otp_code, verification_type='registration'):
    """
    Send OTP email to user.
    Always prints OTP to server console as a fallback debug aid.
    """
    # Always log to server console so admin can see OTP even if email fails
    print(f"\n{'='*50}")
    print(f"OTP for {user.email} ({verification_type}): {otp_code}")
    print(f"{'='*50}\n")

    if verification_type == 'registration':
        subject = 'Your SmartCanteen Registration Code'
        message = (
            f"Hello {user.first_name or user.username} 👋,\n\n"
            f"Greetings from SmartCanteen! 👋 \n\n"
            f"Your SmartCanteen registration verification code is:\n\n"
            f"    {otp_code}\n\n"
            f"⚠️ This code is valid for the next 10 minutes.\n"
            f"Please don't share it with anyone.\n\n"
            f"Didn't request this? 🚨 Change your password ASAP to secure your account.\n\n"
            f"Best,\n"
            f"The SmartCanteen Squad 🍴"
        )
    elif verification_type == 'login':
        subject = 'Your SmartCanteen Login Code'
        message = (
            f"Hello {user.first_name or user.username} 👋,\n\n"
            f"Your SmartCanteen login verification code is:\n\n"
            f"    {otp_code}\n\n"
            f"⚠️ This code is valid for the next 10 minutes.\n"
            f"Please don't share it with anyone.\n\n"
            f"Didn't request this? 🚨 Change your password ASAP to secure your account.\n\n"
            f"Best,\n"
            f"The SmartCanteen Squad 🍴"
        )
    else:
        subject = 'Your SmartCanteen Password Reset Code'
        message = (
            f"Hello {user.first_name or user.username},\n\n"
            f"Your SmartCanteen password reset code is:\n\n"
            f"    {otp_code}\n\n"
            f"This code is valid for 10 minutes.\n"
            f"Do not share this code with anyone.\n\n"
            f"If you did not request a password reset, you can ignore this email.\n\n"
            f"-- SmartCanteen Team"
        )

    try:
        send_mail(
            subject,
            message,
            getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@smartcanteen.local'),
            [user.email],
            fail_silently=False,
        )
        print(f"Email sent successfully to {user.email}")
        return True
    except Exception as e:
        print(f"Email sending error for {user.email}: {e}")
        return False


def get_or_create_cart(user):
    """Get or create cart for user."""
    cart, created = Cart.objects.get_or_create(user=user)
    return cart


def fetch_image_from_url(url):
    """
    Download an image from a URL and return (filename, ContentFile).
    Only http/https schemes are allowed. Returns None on failure.
    """
    MAX_SIZE = 5 * 1024 * 1024  # 5 MB
    ALLOWED_CONTENT_TYPES = {'image/jpeg', 'image/png', 'image/webp', 'image/gif'}
    ALLOWED_SCHEMES = {'http', 'https'}

    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ALLOWED_SCHEMES:
            return None, 'Only http/https URLs are allowed.'

        req = urllib.request.Request(url, headers={'User-Agent': 'SmartCanteen/1.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            content_type = response.headers.get_content_type()
            if content_type not in ALLOWED_CONTENT_TYPES:
                return None, f'URL does not point to a supported image (got {content_type}).'

            data = response.read(MAX_SIZE + 1)
            if len(data) > MAX_SIZE:
                return None, 'Image from URL exceeds the 5 MB size limit.'

        # Derive a filename from the URL path or fall back to a generic name
        url_path = parsed.path.rstrip('/')
        basename = os.path.basename(url_path) or 'image'
        # Ensure it has an extension consistent with the content type
        ext_map = {
            'image/jpeg': '.jpg', 'image/png': '.png',
            'image/webp': '.webp', 'image/gif': '.gif',
        }
        if '.' not in basename:
            basename += ext_map.get(content_type, '.jpg')

        return basename, ContentFile(data)

    except Exception as e:
        return None, str(e)


# ============================================================================
# AUTHENTICATION VIEWS
# ============================================================================

def register(request):
    """
    User registration with email and password.
    Creates user account and generates OTP for verification.
    """
    if request.user.is_authenticated:
        return redirect('canteen:home')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            # Create user
            user = form.save(commit=False)
            user.is_active = False  # Deactivate until OTP verified
            user.save()

            # Generate and send OTP
            # Delete any existing OTP record first so created_at is always
            # fresh (auto_now_add would not update on an existing record).
            otp_code = OTPVerification.generate_otp()
            OTPVerification.objects.filter(user=user).delete()
            OTPVerification.objects.create(
                user=user,
                otp_code=otp_code,
                verification_type='registration',
                attempts=0,
                is_verified=False,
            )

            # Track which user is awaiting OTP verification
            request.session['pending_otp_user_id'] = user.pk

            # Send OTP email
            email_sent = send_otp_email(user, otp_code, 'registration')

            if email_sent:
                messages.success(
                    request,
                    f'Registration successful! OTP sent to {user.email}. '
                    'Please verify your account.'
                )
            else:
                # Fallback: show OTP in message so user can still verify
                messages.warning(
                    request,
                    f'Registration successful but email could not be sent. '
                    f'Your OTP is: {otp_code} (valid for 10 minutes).'
                )
            return redirect('canteen:verify_otp')
    else:
        form = UserRegistrationForm()

    context = {'form': form}
    return render(request, 'canteen/auth/register.html', context)


def verify_otp(request):
    """
    OTP verification during registration.
    Activates user account after successful OTP verification.
    """
    if request.user.is_authenticated:
        return redirect('canteen:home')

    if request.method == 'POST':
        form = OTPVerificationForm(request.POST)
        if form.is_valid():
            otp_code = form.cleaned_data['otp_code']

            # Retrieve user from session
            user_id = request.session.get('pending_otp_user_id')
            if not user_id:
                messages.error(request, 'Session expired. Please register again.')
                return redirect('canteen:register')

            # Find OTP verification record
            try:
                otp_verification = OTPVerification.objects.get(
                    user_id=user_id,
                    verification_type='registration',
                    is_verified=False
                )

                # Validate OTP
                if not otp_verification.is_valid():
                    messages.error(request, 'OTP has expired. Please register again.')
                    return redirect('canteen:register')

                if otp_verification.is_max_attempts_exceeded():
                    messages.error(request, 'Maximum OTP attempts exceeded. Please register again.')
                    OTPVerification.objects.filter(user=otp_verification.user).delete()
                    otp_verification.user.delete()
                    return redirect('canteen:register')

                if otp_verification.otp_code == otp_code:
                    # Mark as verified
                    otp_verification.is_verified = True
                    otp_verification.save()

                    # Activate user
                    user = otp_verification.user
                    user.is_active = True
                    user.save()

                    # Create custom user profile
                    CustomUser.objects.get_or_create(
                        user=user,
                        defaults={'is_verified': True}
                    )

                    # Clear the pending session key
                    request.session.pop('pending_otp_user_id', None)

                    messages.success(
                        request,
                        'Email verified! Your account is now active. Please login.'
                    )
                    return redirect('canteen:login')
                else:
                    otp_verification.increment_attempts()
                    messages.error(request, 'Invalid OTP. Please try again.')

            except OTPVerification.DoesNotExist:
                messages.error(request, 'No verification request found. Please register again.')
                return redirect('canteen:register')

    else:
        form = OTPVerificationForm()

    context = {'form': form}
    return render(request, 'canteen/auth/verify_otp.html', context)


def login_view(request):
    """
    User login view.
    Authenticates with email/username and password.
    """
    if request.user.is_authenticated:
        return redirect('canteen:home')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            remember_me = form.cleaned_data['remember_me']

            # Try to authenticate with email or username
            user = None
            try:
                user_obj = User.objects.get(email=email)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                user = authenticate(request, username=email, password=password)

            if user is not None:
                # Generate login OTP and await verification before logging in
                # Delete first so created_at is always fresh.
                otp_code = OTPVerification.generate_otp()
                OTPVerification.objects.filter(user=user).delete()
                OTPVerification.objects.create(
                    user=user,
                    otp_code=otp_code,
                    verification_type='login',
                    attempts=0,
                    is_verified=False,
                )

                # Preserve login context across OTP step
                request.session['login_otp_user_id'] = user.pk
                request.session['login_otp_remember_me'] = remember_me
                next_url = request.GET.get('next', '')
                if next_url:
                    request.session['login_otp_next_url'] = next_url

                email_sent = send_otp_email(user, otp_code, 'login')
                if email_sent:
                    messages.info(
                        request,
                        f'A verification code has been sent to {user.email}. '
                        'Please enter it below to complete login.'
                    )
                else:
                    messages.warning(
                        request,
                        f'Could not send OTP email. Your login OTP is: {otp_code} '
                        '(valid for 10 minutes).'
                    )
                return redirect('canteen:login_verify_otp')
            else:
                # Provide clearer feedback when account exists but is inactive
                account_hint = None
                try:
                    # Check by email first
                    existing = User.objects.get(email=email)
                    account_hint = existing
                except User.DoesNotExist:
                    try:
                        existing = User.objects.get(username=email)
                        account_hint = existing
                    except User.DoesNotExist:
                        account_hint = None

                if account_hint is not None and not account_hint.is_active:
                    messages.warning(
                        request,
                        'Your account is not activated. Please verify your email using the OTP sent during registration.'
                    )
                else:
                    messages.error(request, 'Invalid email or password.')
    else:
        form = LoginForm()

    context = {'form': form}
    return render(request, 'canteen/auth/login.html', context)


def login_verify_otp(request):
    """
    Verify OTP sent during login.
    Completes the login process after successful OTP verification.
    """
    if request.user.is_authenticated:
        return redirect('canteen:home')

    user_id = request.session.get('login_otp_user_id')
    if not user_id:
        messages.error(request, 'Session expired. Please login again.')
        return redirect('canteen:login')

    if request.method == 'POST':
        form = OTPVerificationForm(request.POST)
        if form.is_valid():
            otp_code = form.cleaned_data['otp_code']
            try:
                otp_verification = OTPVerification.objects.get(
                    user_id=user_id,
                    verification_type='login',
                    is_verified=False
                )

                if not otp_verification.is_valid():
                    messages.error(request, 'OTP has expired. Please login again.')
                    request.session.pop('login_otp_user_id', None)
                    request.session.pop('login_otp_remember_me', None)
                    request.session.pop('login_otp_next_url', None)
                    return redirect('canteen:login')

                if otp_verification.is_max_attempts_exceeded():
                    messages.error(request, 'Maximum OTP attempts exceeded. Please login again.')
                    OTPVerification.objects.filter(user_id=user_id, verification_type='login').delete()
                    request.session.pop('login_otp_user_id', None)
                    request.session.pop('login_otp_remember_me', None)
                    request.session.pop('login_otp_next_url', None)
                    return redirect('canteen:login')

                if otp_verification.otp_code == otp_code:
                    otp_verification.is_verified = True
                    otp_verification.save()

                    # Complete the login
                    user = otp_verification.user
                    login(request, user)

                    remember_me = request.session.pop('login_otp_remember_me', False)
                    next_url = request.session.pop('login_otp_next_url', None)
                    request.session.pop('login_otp_user_id', None)

                    if not remember_me:
                        request.session.set_expiry(0)
                    else:
                        request.session.set_expiry(timedelta(weeks=2))

                    messages.success(request, f'Welcome back, {user.first_name or user.username}!')
                    return redirect(next_url) if next_url else redirect('canteen:home')
                else:
                    otp_verification.increment_attempts()
                    messages.error(request, 'Invalid OTP. Please try again.')

            except OTPVerification.DoesNotExist:
                messages.error(request, 'No OTP found. Please login again.')
                return redirect('canteen:login')
    else:
        form = OTPVerificationForm()

    context = {'form': form, 'purpose': 'login'}
    return render(request, 'canteen/auth/login_verify_otp.html', context)


@login_required(login_url='canteen:login')
def logout_view(request):
    """Logout user."""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('canteen:home')


def password_reset_request(request):
    """
    Request password reset via email OTP.
    """
    if request.user.is_authenticated:
        return redirect('canteen:home')

    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user = User.objects.get(email=email)

            # Delete any existing OTP record first so created_at is always
            # fresh (auto_now_add would not update on an existing record).
            otp_code = OTPVerification.generate_otp()
            OTPVerification.objects.filter(user=user).delete()
            OTPVerification.objects.create(
                user=user,
                otp_code=otp_code,
                verification_type='password_reset',
                attempts=0,
                is_verified=False,
            )

            # Send OTP
            send_otp_email(user, otp_code, 'password reset')

            messages.success(
                request,
                'OTP sent to your email. Please check your inbox.'
            )
            return redirect('canteen:password_reset')
    else:
        form = PasswordResetRequestForm()

    context = {'form': form}
    return render(request, 'canteen/auth/password_reset_request.html', context)


def password_reset(request):
    """
    Reset password using OTP.
    """
    if request.user.is_authenticated:
        return redirect('canteen:home')

    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            otp_code = form.cleaned_data['otp_code']
            new_password = form.cleaned_data['new_password']

            try:
                otp_verification = OTPVerification.objects.get(
                    otp_code=otp_code,
                    verification_type='password_reset',
                    is_verified=False
                )

                if not otp_verification.is_valid():
                    messages.error(request, 'OTP has expired.')
                    return redirect('canteen:password_reset_request')

                if otp_verification.is_max_attempts_exceeded():
                    messages.error(request, 'Maximum attempts exceeded.')
                    return redirect('canteen:password_reset_request')

                # Update password
                user = otp_verification.user
                user.set_password(new_password)
                user.save()

                # Mark OTP as verified
                otp_verification.is_verified = True
                otp_verification.save()

                messages.success(request, 'Password reset successfully. Please login.')
                return redirect('canteen:login')

            except OTPVerification.DoesNotExist:
                messages.error(request, 'Invalid OTP. Please check and try again.')
    else:
        form = PasswordResetForm()

    context = {'form': form}
    return render(request, 'canteen/auth/password_reset.html', context)


# ============================================================================
# HOME & FOOD BROWSING VIEWS
# ============================================================================

def home(request):
    """
    Home page with featured food items.
    Shows announcements and featured items.
    """
    # Get active announcements
    announcements = AnnouncementNotification.objects.filter(
        is_active=True
    ).exclude(
        expires_at__lt=timezone.now()
    ).order_by('-created_at')[:3]

    # Get featured items (recently added, available)
    featured_items = FoodItem.objects.filter(
        availability_status='available'
    ).order_by('-created_at')[:8]

    # Get categories
    categories = Category.objects.filter(is_active=True).order_by('name')

    context = {
        'announcements': announcements,
        'featured_items': featured_items,
        'categories': categories,
    }
    return render(request, 'canteen/home.html', context)


def food_list(request):
    """
    Browse all food items with filtering and pagination.
    Supports search, category filter, and sorting.
    """
    items = FoodItem.objects.filter(
        availability_status='available'
    ).select_related('category')

    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        items = items.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    # Category filter
    category_id = request.GET.get('category')
    if category_id:
        items = items.filter(category_id=category_id)

    # Sorting
    sort_by = request.GET.get('sort', '-created_at')
    valid_sorts = ['name', '-name', 'price', '-price', '-created_at', 'created_at', 'rating', '-rating', 'average_rating', '-average_rating']
    if sort_by in valid_sorts:
        items = items.order_by(sort_by)
    else:
        items = items.order_by('-created_at')

    # Pagination
    paginator = Paginator(items, 12)
    page_num = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_num)

    context = {
        'page_obj': page_obj,
        'items': page_obj.object_list,
        'search_query': search_query,
        'categories': Category.objects.filter(is_active=True),
    }
    return render(request, 'canteen/food_list.html', context)


def food_detail(request, slug):
    """
    Detailed view of a food item.
    Shows reviews, ratings, and add to cart option.
    Primary access is by SEO-friendly slug, but this view
    also gracefully handles legacy numeric or invalid values.
    """
    # Handle bad/legacy values like "None" or empty slug by redirecting safely
    if not slug or str(slug).lower() == "none":
        return redirect("canteen:food_list")

    # Support old numeric ID links by redirecting to the canonical slug URL
    if str(slug).isdigit():
        food_item = get_object_or_404(FoodItem, pk=int(slug))
        return redirect("canteen:food_detail", slug=food_item.slug)

    food_item = get_object_or_404(FoodItem, slug=slug)
    reviews = food_item.reviews.all().select_related('user')
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg']

    # Get related items (same category)
    related_items = FoodItem.objects.filter(
        category=food_item.category,
        availability_status='available'
    ).exclude(pk=food_item.pk)[:4]

    if request.method == 'POST' and request.user.is_authenticated:
        form = AddToCartForm(request.POST)
        if form.is_valid():
            quantity = form.cleaned_data['quantity']
            cart = get_or_create_cart(request.user)
            
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                food_item=food_item,
                defaults={'quantity': quantity}
            )
            
            if not created:
                cart_item.quantity += quantity
                cart_item.save()

            messages.success(
                request,
                f'{food_item.name} added to cart!'
            )
            return redirect('canteen:cart')
    else:
        form = AddToCartForm()

    context = {
        'food_item': food_item,
        'reviews': reviews,
        'avg_rating': avg_rating,
        'review_count': reviews.count(),
        'related_items': related_items,
        'form': form,
    }
    return render(request, 'canteen/food_detail.html', context)


# ============================================================================
# CART VIEWS
# ============================================================================

@login_required(login_url='canteen:login')
def cart_view(request):
    """
    Shopping cart view.
    Shows all cart items with options to update/remove.
    """
    cart = get_or_create_cart(request.user)
    

    context = {
        'cart': cart,
        'items': cart.items.all().select_related('food_item'),
        'total_items': cart.get_total_items(),
        'total_price': cart.get_total_price(),
    }
    return render(request, 'canteen/cart.html', context)


@login_required(login_url='canteen:login')
@require_POST
def add_to_cart(request, item_id):
    """AJAX endpoint to add item to cart."""
    try:
        food_item = FoodItem.objects.get(pk=item_id)
        quantity = int(request.POST.get('quantity', 1))

        if not food_item.is_available():
            return JsonResponse({
                'status': 'error',
                'message': 'This item is not available.'
            }, status=400)

        if quantity <= 0:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid quantity.'
            }, status=400)

        cart = get_or_create_cart(request.user)
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            food_item=food_item,
            defaults={'quantity': quantity}
        )

        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        return JsonResponse({
            'status': 'success',
            'message': f'{food_item.name} added to cart!',
            'cart_count': cart.get_total_items(),
            'cart_total': str(cart.get_total_price()),
        })

    except FoodItem.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Food item not found.'
        }, status=404)
    except ValueError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid input.'
        }, status=400)


@login_required(login_url='canteen:login')
@require_POST
def update_cart_item(request, item_id):
    """Update quantity of cart item."""
    try:
        cart_item = CartItem.objects.get(pk=item_id, cart__user=request.user)
        form = UpdateCartItemForm(request.POST)

        if form.is_valid():
            quantity = form.cleaned_data['quantity']

            if quantity == 0:
                # Delete item from cart
                cart_item.delete()
                return JsonResponse({
                    'status': 'success',
                    'message': 'Item removed from cart.',
                    'action': 'removed'
                })
            else:
                # Update quantity
                cart_item.quantity = quantity
                cart_item.save()

                cart = cart_item.cart
                return JsonResponse({
                    'status': 'success',
                    'message': 'Cart updated.',
                    'action': 'updated',
                    'subtotal': str(cart_item.get_subtotal()),
                    'cart_total': str(cart.get_total_price()),
                })
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid input.'
            }, status=400)

    except CartItem.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Cart item not found.'
        }, status=404)


@login_required(login_url='canteen:login')
@require_POST
def remove_from_cart(request, item_id):
    """Remove item from cart."""
    try:
        cart_item = CartItem.objects.get(pk=item_id, cart__user=request.user)
        food_name = cart_item.food_item.name
        cart_item.delete()

        messages.success(request, f'{food_name} removed from cart.')
        return redirect('canteen:cart')

    except CartItem.DoesNotExist:
        messages.error(request, 'Item not found in cart.')
        return redirect('canteen:cart')


# ============================================================================
# ORDER VIEWS
# ============================================================================

@login_required(login_url='canteen:login')
def checkout(request):
    """
    Checkout page with order summary.
    Places order and creates order items.
    """
    cart = get_or_create_cart(request.user)

    if not cart.items.exists():
        messages.warning(request, 'Your cart is empty!')
        return redirect('canteen:food_list')

    if request.method == 'POST':
        form = PlaceOrderForm(request.POST)
        if form.is_valid():
            # Pricing calculations
            subtotal = cart.get_total_price()
            tax = (subtotal * Decimal('5')) / Decimal('100')
            discount = Decimal('0.00')
            total = subtotal + tax - discount

            # Create order with all required monetary fields populated
            order = Order.objects.create(
                user=request.user,
                order_id=Order.generate_order_id(),
                payment_method=form.cleaned_data['payment_method'],
                special_instructions=form.cleaned_data['special_instructions'],
                subtotal=subtotal,
                tax=tax,
                discount=discount,
                total_amount=total,
            )

            # Create order items from cart
            for cart_item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    food_item=cart_item.food_item,
                    item_name=cart_item.food_item.name,
                    item_price=cart_item.food_item.price,
                    quantity=cart_item.quantity,
                )

            # Clear cart
            cart.clear()

            messages.success(
                request,
                f'Order placed successfully! Order ID: {order.order_id}'
            )
            return redirect('canteen:order_detail', order_id=order.order_id)
    else:
        form = PlaceOrderForm()

    context = {
        'cart': cart,
        'items': cart.items.all().select_related('food_item'),
        'total_items': cart.get_total_items(),
        'subtotal': cart.get_total_price(),
        'tax': (cart.get_total_price() * Decimal('5')) / Decimal('100'),
        'total': cart.get_total_price() + (cart.get_total_price() * Decimal('5')) / Decimal('100'),
        'form': form,
    }
    return render(request, 'canteen/checkout.html', context)


@login_required(login_url='canteen:login')
def order_list(request):
    """List all user orders with filtering."""
    orders = request.user.orders.all().prefetch_related('items').order_by('-created_at')

    # Status filter
    status = request.GET.get('status')
    if status and status in dict(Order.STATUS_CHOICES):
        orders = orders.filter(status=status)

    # Pagination
    paginator = Paginator(orders, 10)
    page_num = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_num)

    context = {
        'page_obj': page_obj,
        'orders': page_obj.object_list,
        'statuses': Order.STATUS_CHOICES,
    }
    return render(request, 'canteen/order_list.html', context)


@login_required(login_url='canteen:login')
def order_detail(request, order_id):
    """Detailed view of single order."""
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    items = order.items.all()

    context = {
        'order': order,
        'items': items,
    }
    return render(request, 'canteen/order_detail.html', context)


@login_required(login_url='canteen:login')
@require_POST
def cancel_order(request, order_id):
    """Cancel an order."""
    order = get_object_or_404(Order, order_id=order_id, user=request.user)

    if order.cancel_order():
        messages.success(request, f'Order {order.order_id} has been cancelled.')
    else:
        messages.error(request, 'This order cannot be cancelled.')

    return redirect('canteen:order_detail', order_id=order.order_id)


# ============================================================================
# REVIEW VIEWS
# ============================================================================

@login_required(login_url='canteen:login')
def add_review(request, slug):
    """Add or edit review for a food item (accessed by slug)."""
    food_item = get_object_or_404(FoodItem, slug=slug)

    # Check if user has purchased this item
    if not order_contains_item(request.user, food_item):
        messages.warning(request, 'You can only review items you have purchased.')
        return redirect('canteen:food_detail', slug=food_item.slug)

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review, created = Review.objects.update_or_create(
                user=request.user,
                food_item=food_item,
                defaults={
                    'rating': form.cleaned_data['rating'],
                    'comment': form.cleaned_data['comment'],
                }
            )
            messages.success(request, 'Review added successfully!')
            return redirect('canteen:food_detail', slug=food_item.slug)
    else:
        try:
            review = Review.objects.get(user=request.user, food_item=food_item)
            form = ReviewForm(instance=review)
        except Review.DoesNotExist:
            form = ReviewForm()

    context = {
        'form': form,
        'food_item': food_item,
    }
    return render(request, 'canteen/add_review.html', context)


def order_contains_item(user, food_item):
    """Check if user has purchased this food item."""
    return user.orders.filter(
        items__food_item=food_item,
        status__in=['completed', 'ready']
    ).exists()


# ============================================================================
# ADMIN VIEWS
# ============================================================================

@login_required(login_url='canteen:login')
def is_admin_user_required(view_func):
    """Decorator to check admin access."""
    def wrapper(request, *args, **kwargs):
        if not is_admin_user(request.user):
            messages.error(request, 'Access denied. Admin privileges required.')
            return redirect('canteen:home')
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required(login_url='canteen:login')
@user_passes_test(is_admin_user)
def admin_dashboard(request):
    """Admin dashboard with statistics."""
    # Get statistics
    total_orders = Order.objects.count()
    pending_orders = Order.objects.filter(status='pending').count()
    ready_orders = Order.objects.filter(status='ready').count()
    completed_orders = Order.objects.filter(status='completed').count()

    total_revenue = Order.objects.filter(status='completed').aggregate(
        Sum('total_amount')
    )['total_amount__sum'] or Decimal('0')

    total_items = FoodItem.objects.count()
    available_items = FoodItem.objects.filter(
        availability_status='available'
    ).count()

    # Get orders for today
    today = timezone.now().date()
    today_orders = Order.objects.filter(created_at__date=today)
    today_revenue = today_orders.aggregate(
        Sum('total_amount')
    )['total_amount__sum'] or Decimal('0')

    # Recent orders
    recent_orders = Order.objects.all().select_related('user').order_by('-created_at')[:10]

    context = {
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'ready_orders': ready_orders,
        'completed_orders': completed_orders,
        'total_revenue': total_revenue,
        'total_items': total_items,
        'available_items': available_items,
        'today_orders': today_orders.count(),
        'today_revenue': today_revenue,
        'recent_orders': recent_orders,
    }
    return render(request, 'canteen/admin/dashboard.html', context)


@login_required(login_url='canteen:login')
@user_passes_test(is_admin_user)
def manage_food_items(request):
    """List all food items for admin."""
    items = FoodItem.objects.all().select_related('category').order_by('-created_at')

    # Search and filter
    search = request.GET.get('search')
    if search:
        items = items.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )

    category = request.GET.get('category')
    if category:
        items = items.filter(category_id=category)

    # Pagination
    paginator = Paginator(items, 20)
    page_num = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_num)

    context = {
        'page_obj': page_obj,
        'items': page_obj.object_list,
        'categories': Category.objects.filter(is_active=True),
    }
    return render(request, 'canteen/admin/manage_items.html', context)


@login_required(login_url='canteen:login')
@user_passes_test(is_admin_user)
def add_food_item(request):
    """Add new food item."""
    if request.method == 'POST':
        form = FoodItemForm(request.POST, request.FILES)
        if form.is_valid():
            food_item = form.save(commit=False)
            food_item.created_by = request.user

            # If no file uploaded but a URL was provided, fetch from URL
            if not request.FILES.get('image'):
                image_url = form.cleaned_data.get('image_url')
                if image_url:
                    filename, file_or_error = fetch_image_from_url(image_url)
                    if filename:
                        food_item.image.save(filename, file_or_error, save=False)
                    else:
                        form.add_error('image_url', f'Could not fetch image: {file_or_error}')
                        return render(request, 'canteen/admin/food_form.html', {'form': form, 'action': 'Add'})

            food_item.save()
            messages.success(request, f'{food_item.name} added successfully!')
            return redirect('canteen:manage_items')
    else:
        form = FoodItemForm()

    context = {'form': form, 'action': 'Add'}
    return render(request, 'canteen/admin/food_form.html', context)


@login_required(login_url='canteen:login')
@user_passes_test(is_admin_user)
def edit_food_item(request, pk):
    """Edit food item."""
    food_item = get_object_or_404(FoodItem, pk=pk)

    if request.method == 'POST':
        form = FoodItemForm(request.POST, request.FILES, instance=food_item)
        if form.is_valid():
            updated_item = form.save(commit=False)

            # If no file uploaded but a URL was provided, fetch from URL
            if not request.FILES.get('image'):
                image_url = form.cleaned_data.get('image_url')
                if image_url:
                    filename, file_or_error = fetch_image_from_url(image_url)
                    if filename:
                        updated_item.image.save(filename, file_or_error, save=False)
                    else:
                        form.add_error('image_url', f'Could not fetch image: {file_or_error}')
                        return render(request, 'canteen/admin/food_form.html', {
                            'form': form, 'food_item': food_item, 'action': 'Edit'
                        })

            updated_item.save()
            messages.success(request, f'{food_item.name} updated successfully!')
            return redirect('canteen:manage_items')
    else:
        form = FoodItemForm(instance=food_item)

    context = {'form': form, 'food_item': food_item, 'action': 'Edit'}
    return render(request, 'canteen/admin/food_form.html', context)


@login_required(login_url='canteen:login')
@user_passes_test(is_admin_user)
@require_POST
def delete_food_item(request, pk):
    """Delete food item."""
    food_item = get_object_or_404(FoodItem, pk=pk)
    name = food_item.name
    food_item.delete()

    messages.success(request, f'{name} deleted successfully!')
    return redirect('canteen:manage_items')


@login_required(login_url='canteen:login')
@user_passes_test(is_admin_user)
def manage_orders(request):
    """Admin view to manage all orders."""
    orders = Order.objects.all().select_related('user').prefetch_related('items').order_by('-created_at')

    status = request.GET.get('status')
    if status and status in dict(Order.STATUS_CHOICES):
        orders = orders.filter(status=status)

    paginator = Paginator(orders, 20)
    page_num = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_num)

    context = {
        'page_obj': page_obj,
        'orders': page_obj.object_list,
        'statuses': Order.STATUS_CHOICES,
    }
    return render(request, 'canteen/admin/manage_orders.html', context)


@login_required(login_url='canteen:login')
@user_passes_test(is_admin_user)
def update_order_status(request, order_id):
    """Update order status."""
    order = get_object_or_404(Order, order_id=order_id)

    if request.method == 'POST':
        form = OrderStatusUpdateForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            messages.success(request, f'Order {order.order_id} status updated!')
            return redirect('canteen:manage_orders')
    else:
        form = OrderStatusUpdateForm(instance=order)

    context = {'form': form, 'order': order}
    return render(request, 'canteen/admin/update_order.html', context)


@login_required(login_url='canteen:login')
@user_passes_test(is_admin_user)
def admin_order_detail(request, order_id):
    """Admin view of order details."""
    order = get_object_or_404(Order, order_id=order_id)
    items = order.items.all()

    context = {
        'order': order,
        'items': items,
    }
    return render(request, 'canteen/admin/order_detail.html', context)


# ============================================================================
# USER PROFILE
# ============================================================================

@login_required(login_url='canteen:login')
def profile_view(request):
    """User profile: view and update personal information."""
    user = request.user
    canteen_profile, _ = CustomUser.objects.get_or_create(
        user=user,
        defaults={'is_verified': True}
    )

    if request.method == 'POST':
        form = UserProfileForm(request.POST)
        if form.is_valid():
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.save()

            canteen_profile.phone_number = form.cleaned_data['phone_number']
            canteen_profile.save()

            messages.success(request, 'Profile updated successfully!')
            return redirect('canteen:profile')
    else:
        form = UserProfileForm(initial={
            'first_name': user.first_name,
            'last_name': user.last_name,
            'phone_number': canteen_profile.phone_number or '',
        })

    # Order statistics
    orders = user.orders.all()
    total_orders = orders.count()
    completed_orders = orders.filter(status='completed').count()
    total_spent = orders.filter(status='completed').aggregate(
        total=Sum('total_amount')
    )['total'] or Decimal('0.00')
    recent_orders = orders.order_by('-created_at')[:5]

    context = {
        'form': form,
        'canteen_profile': canteen_profile,
        'total_orders': total_orders,
        'completed_orders': completed_orders,
        'total_spent': total_spent,
        'recent_orders': recent_orders,
        'email_form': ChangeEmailRequestForm(user),
    }
    return render(request, 'canteen/profile.html', context)


@login_required(login_url='canteen:login')
def change_email_request(request):
    """
    Step 1: User submits a new email address.
    Generates and emails an OTP to the *new* address for verification.
    """
    if request.method == 'POST':
        form = ChangeEmailRequestForm(request.user, request.POST)
        if form.is_valid():
            new_email = form.cleaned_data['new_email']

            otp_code = OTPVerification.generate_otp()
            OTPVerification.objects.filter(user=request.user).delete()
            OTPVerification.objects.create(
                user=request.user,
                otp_code=otp_code,
                verification_type='email_change',
                attempts=0,
                is_verified=False,
            )

            # Store the requested new email in session (not committed yet)
            request.session['pending_new_email'] = new_email

            # Send OTP to the NEW email address
            print(f"\n{'='*50}")
            print(f"Email-change OTP for {request.user.email} → {new_email}: {otp_code}")
            print(f"{'='*50}\n")

            subject = 'Your SmartCanteen Email Change Code'
            message = (
                f"Hello {request.user.first_name or request.user.username},\n\n"
                f"We received a request to change the email address on your SmartCanteen account.\n\n"
                f"Your verification code is:\n\n"
                f"    {otp_code}\n\n"
                f"This code is valid for 10 minutes.\n"
                f"Do not share this code with anyone.\n\n"
                f"If you did not request this change, please ignore this email — your account is safe.\n\n"
                f"-- SmartCanteen Team"
            )
            try:
                send_mail(
                    subject, message,
                    getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@smartcanteen.local'),
                    [new_email],
                    fail_silently=False,
                )
                messages.info(
                    request,
                    f'A verification code has been sent to {new_email}. '
                    'Enter it below to confirm the change.'
                )
            except Exception as e:
                print(f"Email sending error: {e}")
                messages.warning(
                    request,
                    f'Could not send email. Your OTP is: {otp_code} (valid for 10 minutes).'
                )

            return redirect('canteen:change_email_verify')
    else:
        form = ChangeEmailRequestForm(request.user)

    return render(request, 'canteen/profile.html', {
        'email_form': form,
        'show_email_modal': True,
        # re-supply profile context so the page renders fully
        'form': UserProfileForm(initial={
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'phone_number': (
                request.user.canteen_profile.phone_number
                if hasattr(request.user, 'canteen_profile') else ''
            ),
        }),
        'canteen_profile': CustomUser.objects.get_or_create(
            user=request.user, defaults={'is_verified': True}
        )[0],
        'total_orders': request.user.orders.count(),
        'completed_orders': request.user.orders.filter(status='completed').count(),
        'total_spent': request.user.orders.filter(status='completed').aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0.00'),
        'recent_orders': request.user.orders.order_by('-created_at')[:5],
    })


@login_required(login_url='canteen:login')
def change_email_verify(request):
    """
    Step 2: User enters the OTP received at their new email address.
    If correct, the account email (and username) is updated.
    """
    new_email = request.session.get('pending_new_email')
    if not new_email:
        messages.error(request, 'Session expired. Please start the email change again.')
        return redirect('canteen:profile')

    if request.method == 'POST':
        form = OTPVerificationForm(request.POST)
        if form.is_valid():
            otp_code = form.cleaned_data['otp_code']
            try:
                otp_verification = OTPVerification.objects.get(
                    user=request.user,
                    verification_type='email_change',
                    is_verified=False,
                )

                if not otp_verification.is_valid():
                    messages.error(request, 'OTP has expired. Please request a new one.')
                    request.session.pop('pending_new_email', None)
                    return redirect('canteen:profile')

                if otp_verification.is_max_attempts_exceeded():
                    messages.error(request, 'Maximum OTP attempts exceeded. Please try again.')
                    OTPVerification.objects.filter(user=request.user).delete()
                    request.session.pop('pending_new_email', None)
                    return redirect('canteen:profile')

                if otp_verification.otp_code == otp_code:
                    # Apply the email change
                    user = request.user
                    user.email = new_email
                    user.username = new_email  # username mirrors email
                    user.save()

                    otp_verification.is_verified = True
                    otp_verification.save()

                    request.session.pop('pending_new_email', None)
                    messages.success(request, f'Email address updated to {new_email}.')
                    return redirect('canteen:profile')
                else:
                    otp_verification.increment_attempts()
                    messages.error(request, 'Invalid OTP. Please try again.')

            except OTPVerification.DoesNotExist:
                messages.error(request, 'No pending email change found. Please start again.')
                return redirect('canteen:profile')
    else:
        form = OTPVerificationForm()

    return render(request, 'canteen/auth/change_email_verify.html', {
        'form': form,
        'new_email': new_email,
    })
