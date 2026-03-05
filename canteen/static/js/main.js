/**
 * SmartCanteen - Main JavaScript File
 * Handles AJAX interactions, form validations, and UI enhancements
 */

// ============================================================================
// CONFIGURATION
// ============================================================================

const API_ENDPOINTS = {
    ADD_TO_CART: '/add-to-cart/',
    UPDATE_CART: '/update-cart-item/',
    REMOVE_FROM_CART: '/remove-from-cart/',
};

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Get CSRF token from cookie
 */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

const csrftoken = getCookie('csrftoken');

/**
 * Show toast/alert message
 */
function showMessage(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.setAttribute('role', 'alert');
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    const container = document.querySelector('.container-fluid') || document.querySelector('.container');
    if (container) {
        container.insertBefore(alertDiv, container.firstChild);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            alertDiv.remove();
        }, 5000);
    }
}

/**
 * Format currency
 */
function formatCurrency(value) {
    return '₹' + parseFloat(value).toFixed(2);
}

// ============================================================================
// CART FUNCTIONS
// ============================================================================

/**
 * Add item to cart via AJAX
 */
function addToCartAjax(itemId, quantity = 1) {
    const csrftoken = document.querySelector('[name=csrftoken]').value;
    const formData = new FormData();
    formData.append('quantity', quantity);

    fetch(`/add-to-cart/${itemId}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrftoken,
        },
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showMessage(data.message, 'success');
            updateCartBadge(data.cart_count);
        } else {
            showMessage(data.message, 'danger');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showMessage('An error occurred. Please try again.', 'danger');
    });
}

/**
 * Update cart badge count
 */
function updateCartBadge(count) {
    const badge = document.querySelector('.nav-link .badge') || 
                  document.querySelector('[data-cart-count]');
    if (badge) {
        if (count > 0) {
            badge.textContent = count;
            badge.style.display = 'block';
        } else {
            badge.style.display = 'none';
        }
    }
}

/**
 * Update cart item quantity
 */
function updateCartItem(itemId, newQuantity) {
    const csrftoken = getCookie('csrftoken');
    const formData = new FormData();
    formData.append('quantity', newQuantity);

    fetch(`/update-cart-item/${itemId}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrftoken,
        },
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            if (data.action === 'removed') {
                // Remove the row
                const row = document.querySelector(`[data-item-id="${itemId}"]`);
                if (row) row.remove();
                showMessage('Item removed from cart', 'info');
            } else {
                // Update subtotal
                const subtotalCell = document.querySelector(`[data-subtotal-${itemId}]`);
                if (subtotalCell) {
                    subtotalCell.textContent = formatCurrency(data.subtotal);
                }
                showMessage('Cart updated', 'success');
            }
            // Reload cart page or update total
            location.reload();
        } else {
            showMessage(data.message, 'danger');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showMessage('An error occurred', 'danger');
    });
}

// ============================================================================
// FORM VALIDATION
// ============================================================================

/**
 * Validate email format
 */
function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

/**
 * Validate password strength
 */
function validatePassword(password) {
    const requirements = {
        length: password.length >= 8,
        uppercase: /[A-Z]/.test(password),
        number: /[0-9]/.test(password),
        special: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)
    };
    return Object.values(requirements).every(req => req);
}

/**
 * Client-side form validation
 */
function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return true;

    let isValid = true;
    const inputs = form.querySelectorAll('input, textarea, select');

    inputs.forEach(input => {
        // Clear previous error
        input.classList.remove('is-invalid');
        
        // Check if required field is empty
        if (input.required && !input.value.trim()) {
            input.classList.add('is-invalid');
            isValid = false;
        }

        // Email validation
        if (input.type === 'email' && input.value && !validateEmail(input.value)) {
            input.classList.add('is-invalid');
            isValid = false;
        }

        // Number validation
        if (input.type === 'number' && input.value) {
            if (input.min && parseInt(input.value) < parseInt(input.min)) {
                input.classList.add('is-invalid');
                isValid = false;
            }
            if (input.max && parseInt(input.value) > parseInt(input.max)) {
                input.classList.add('is-invalid');
                isValid = false;
            }
        }
    });

    return isValid;
}

// ============================================================================
// ORDER FUNCTIONS
// ============================================================================

/**
 * Track order status
 */
function pollOrderStatus(orderId, pollInterval = 5000) {
    const statusElement = document.querySelector('[data-order-status]');
    if (!statusElement) return;

    setInterval(() => {
        fetch(`/order/${orderId}/`, {
            headers: {
                'Accept': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.status) {
                statusElement.textContent = data.status.toUpperCase();
                statusElement.className = `badge bg-${getStatusColor(data.status)}`;
            }
        })
        .catch(error => console.log('Error polling order status:', error));
    }, pollInterval);
}

/**
 * Get status badge color
 */
function getStatusColor(status) {
    const statusColors = {
        'pending': 'warning',
        'confirmed': 'info',
        'preparing': 'info',
        'ready': 'success',
        'completed': 'success',
        'cancelled': 'danger'
    };
    return statusColors[status] || 'secondary';
}

/**
 * Copy order ID to clipboard
 */
function copyOrderId(orderId) {
    navigator.clipboard.writeText(orderId).then(() => {
        showMessage('Order ID copied to clipboard!', 'success');
    }).catch(err => {
        console.error('Failed to copy:', err);
    });
}

// ============================================================================
// INITIALIZATION
// ============================================================================

/**
 * Initialize on DOM ready
 */
document.addEventListener('DOMContentLoaded', function() {
    
    // Initialize Bootstrap components
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Add quantity input validation
    const quantityInputs = document.querySelectorAll('input[type="number"][name="quantity"]');
    quantityInputs.forEach(input => {
        input.addEventListener('change', function() {
            if (this.value < 1) this.value = 1;
            if (this.max && this.value > this.max) this.value = this.max;
        });
    });

    // Add to cart buttons
    const addToCartButtons = document.querySelectorAll('[data-add-to-cart]');
    addToCartButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const itemId = this.dataset.addToCart;
            const quantityInput = document.querySelector(`[data-item-quantity-${itemId}]`);
            const quantity = quantityInput ? quantityInput.value : 1;
            addToCartAjax(itemId, quantity);
        });
    });

    // Remove from cart forms
    const removeCartForms = document.querySelectorAll('[data-remove-from-cart]');
    removeCartForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!confirm('Remove this item from cart?')) {
                e.preventDefault();
            }
        });
    });

    // Confirm delete buttons
    const deleteButtons = document.querySelectorAll('[data-confirm-delete]');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm('Are you sure you want to delete this item?')) {
                e.preventDefault();
            }
        });
    });

    // Order status polling
    const orderStatusElement = document.querySelector('[data-order-id]');
    if (orderStatusElement) {
        const orderId = orderStatusElement.dataset.orderId;
        pollOrderStatus(orderId);
    }

    // Password strength indicator
    const passwordInput = document.querySelector('input[name="password1"]');
    if (passwordInput) {
        passwordInput.addEventListener('input', function() {
            const strength = validatePassword(this.value);
            const indicator = document.querySelector('[data-password-strength]');
            if (indicator) {
                if (this.value.length === 0) {
                    indicator.innerHTML = '';
                } else {
                    indicator.innerHTML = strength ? 
                        '<small class="text-success">Strong password</small>' :
                        '<small class="text-danger">Weak password</small>';
                }
            }
        });
    }

    // Search functionality
    const searchInputs = document.querySelectorAll('[data-search]');
    searchInputs.forEach(input => {
        input.addEventListener('input', function() {
            clearTimeout(this.searchTimeout);
            this.searchTimeout = setTimeout(() => {
                const searchForm = this.closest('form');
                if (searchForm) searchForm.submit();
            }, 500);
        });
    });
});

// ============================================================================
// EXPORT FUNCTIONS FOR EXTERNAL USE
// ============================================================================

window.SmartCanteen = {
    addToCart: addToCartAjax,
    updateCartItem: updateCartItem,
    showMessage: showMessage,
    validateForm: validateForm,
    copyToClipboard: copyOrderId,
    formatCurrency: formatCurrency
};

// Smooth scroll for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
        const href = this.getAttribute('href');
        if (href === '#') return;
        
        e.preventDefault();
        const target = document.querySelector(href);
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Prevent multiple form submissions
document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', function() {
        const buttons = this.querySelectorAll('button[type="submit"]');
        buttons.forEach(button => {
            button.disabled = true;
            button.innerHTML += ' <span class="spinner-border spinner-border-sm ms-2" role="status" aria-hidden="true"></span>';
        });
    });
});
