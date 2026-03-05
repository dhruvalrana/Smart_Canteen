"""
Context processors for SmartCanteen.
Makes global context available to all templates.
"""
from canteen.models import Cart


def cart_context(request):
    """
    Add cart information to template context.
    Available in all templates as {{ cart_count }} and {{ cart_total }}.
    """
    cart_count = 0
    cart_total = 0

    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            cart_count = cart.get_total_items()
            cart_total = cart.get_total_price()
        except Cart.DoesNotExist:
            pass

    return {
        'cart_count': cart_count,
        'cart_total': cart_total,
    }
