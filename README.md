# SmartCanteen

A full-featured **Django-based canteen management system** that lets students and staff browse a digital menu, place orders, and track them in real time — while giving canteen admins a powerful dashboard to manage food items, categories, and orders.

---

## Features

### Customer-Facing
- **OTP Email Verification** — Secure registration, login, password reset, and email change via 6-digit OTP codes
- **Food Menu** — Browse items by category with search, dietary filters (vegetarian, vegan, gluten-free), and calorie info
- **Food Detail Pages** — SEO-friendly slug URLs, ingredient lists, and customer reviews/ratings
- **Shopping Cart** — Add, update, and remove items with live quantity and subtotal tracking
- **Checkout & Orders** — Place orders, view order history, and cancel pending orders
- **User Profile** — Update personal info and change email with OTP verification

### Admin Panel (`/management/`)
- **Dashboard** — Sales stats, revenue totals, recent orders, and top-selling items
- **Food Item Management** — Add, edit, delete food items with image uploads
- **Category Management** — Organise the menu into logical categories
- **Order Management** — View all orders, update order status, and inspect order details

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.x, Django 4.2 |
| Database | SQLite (development) / PostgreSQL (production) |
| Image Handling | Pillow 10.0 |
| Environment Config | python-dotenv |
| Production Server | Gunicorn |
| Frontend | HTML5, Bootstrap, custom CSS/JS |

---

## Project Structure

```
smartcanteen/
├── manage.py
├── requirements.txt
├── db.sqlite3
├── media/                    # Uploaded food images
├── smartcanteen/             # Project config (settings, urls, wsgi)
└── canteen/                  # Main application
    ├── models.py             # DB models
    ├── views.py              # Request handlers
    ├── urls.py               # URL routing
    ├── forms.py              # Django forms
    ├── admin.py              # Django admin registration
    ├── context_processors.py # Cart context injected globally
    ├── static/               # CSS & JS assets
    ├── templates/canteen/    # HTML templates
    └── migrations/           # Database migrations
```

---

## Database Models

| Model | Purpose |
|---|---|
| `CustomUser` | Extends Django's `User` with phone, avatar, and status |
| `OTPVerification` | Manages OTP codes for email-based auth flows |
| `Category` | Groups food items (e.g. Breakfast, Lunch, Beverages) |
| `FoodItem` | Menu items with price, image, dietary flags, and stock |
| `Cart` / `CartItem` | Per-user shopping cart |
| `Order` / `OrderItem` | Completed orders with status tracking |
| `Review` | Customer ratings and comments on food items |
| `AnnouncementNotification` | Canteen announcements for users |

---

## Getting Started

### Prerequisites
- Python 3.9+
- pip

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/your-username/smartcanteen.git
cd smartcanteen

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create a .env file (see Environment Variables below)

# 5. Apply migrations
python manage.py migrate

# 6. Create a superuser (admin)
python manage.py createsuperuser

# 7. Run the development server
python manage.py runserver
```

Visit `http://127.0.0.1:8000` in your browser.

---

## Environment Variables

Create a `.env` file in the project root:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

# Email configuration (required for OTP delivery)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=your-email@gmail.com
```

> **Note:** If email is not configured, OTP codes are printed to the server console as a fallback.

---

## URL Reference

| URL | Description |
|---|---|
| `/` | Home page |
| `/food/` | Browse all food items |
| `/food/<slug>/` | Food item detail & reviews |
| `/register/` | User registration |
| `/login/` | User login (with OTP) |
| `/cart/` | Shopping cart |
| `/checkout/` | Place an order |
| `/orders/` | Order history |
| `/profile/` | User profile |
| `/management/dashboard/` | Admin dashboard |
| `/management/food-items/` | Admin food item list |
| `/management/orders/` | Admin order management |

---

## Production Deployment

1. Set `DEBUG=False` in `.env`
2. Configure PostgreSQL and update `DATABASES` in `settings.py`
3. Set a strong `SECRET_KEY`
4. Run `python manage.py collectstatic`
5. Uncomment the security middleware settings in `settings.py` (HTTPS, HSTS, secure cookies)
6. Serve with **Gunicorn** behind **Nginx**

```bash
gunicorn smartcanteen.wsgi:application --bind 0.0.0.0:8000
```

---

## License

This project is open source and available under the [MIT License](LICENSE).

