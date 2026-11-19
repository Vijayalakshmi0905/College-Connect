"""
College Connect - Main Flask Application
Features:
- MySQL database integration via PyMySQL and Flask-SQLAlchemy (with fallback)
- Authentication for Student, Staff, and Admin roles (Flask-Login)
- Role-based authorization and session management
- Interactive Food Ordering, Cart, and Checkout
- Canteen Staff Kitchen Queue & Real-time Live Polling
- Student Live Tracking & Dashboard
- Admin Management Hub (Users, Menu Catalog, Orders, Sales Analytics)
"""

import os
import re
import random
import secrets
import hmac
from datetime import datetime
from functools import wraps
from urllib.parse import urljoin, urlsplit
from sqlalchemy import text, func, or_
from sqlalchemy.exc import SQLAlchemyError

from flask import Flask, current_app, render_template, jsonify, request, redirect, url_for, flash, session, make_response, abort
from flask_login import (
    LoginManager, login_user, logout_user, login_required, current_user
)

# Configuration & Models
from db_config import get_active_database_uri, is_production, SECRET_KEY
from models import db, User, Student, Staff, FoodItem, Order, OrderItem, Payment
from food_data import FOOD_ITEMS, CATEGORIES

# Initialize Flask application
app = Flask(__name__)
if is_production() and not SECRET_KEY:
    raise RuntimeError('Set a unique SECRET_KEY before starting College Connect in production.')
app.config['SECRET_KEY'] = SECRET_KEY
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = is_production()
app.config['APP_ENV'] = 'production' if is_production() else 'development'
app.config['DEBUG'] = (
    os.environ.get('FLASK_DEBUG', 'false').strip().lower() in {'1', 'true', 'yes'}
    and os.environ.get('APP_ENV', 'development').strip().lower() != 'test'
    and not is_production()
)

# Configure Database URI
db_uri, db_engine_info = get_active_database_uri()
app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize Extensions
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please sign in to access this page.'
login_manager.login_message_category = 'warning'


@login_manager.unauthorized_handler
def handle_unauthorized_request():
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'error': 'Authentication required.'}), 401
    flash(login_manager.login_message, login_manager.login_message_category)
    return redirect(url_for('login', next=request.url))


def get_csrf_token():
    token = session.get('_csrf_token')
    if not token:
        token = secrets.token_urlsafe(32)
        session['_csrf_token'] = token
    return token


@app.context_processor
def inject_csrf_token():
    return {'csrf_token': get_csrf_token}


@app.before_request
def protect_state_changing_requests():
    if request.method in {'POST', 'PUT', 'PATCH', 'DELETE'}:
        submitted_token = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token', '')
        expected_token = session.get('_csrf_token', '')
        if not expected_token or not submitted_token or not hmac.compare_digest(submitted_token, expected_token):
            abort(400, description='Invalid or missing CSRF token.')

VALID_STATUSES = ['CONFIRMED', 'PREPARING', 'READY FOR PICKUP', 'COMPLETED']


@login_manager.user_loader
def load_user(user_id):
    """Loads user by ID for Flask-Login."""
    try:
        return User.query.get(int(user_id))
    except Exception:
        return None


def role_required(*roles):
    """Decorator to enforce role-based access control."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                if request.path.startswith('/api/'):
                    return jsonify({'success': False, 'error': 'Authentication required.'}), 401
                flash('Please sign in to access this campus portal.', 'warning')
                return redirect(url_for('login', next=request.url))
            if current_user.role not in roles:
                if request.path.startswith('/api/'):
                    return jsonify({'success': False, 'error': 'Insufficient privileges.'}), 403
                flash(f'Access restricted. Requires {", ".join(roles)} privileges.', 'danger')
                return redirect(url_for('home'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def is_safe_redirect_target(target):
    """Only allow redirects back to this host."""
    if not target:
        return False
    ref = urlsplit(urljoin(request.host_url, target))
    base = urlsplit(request.host_url)
    return ref.scheme in ('http', 'https') and ref.netloc == base.netloc


def no_cache(f):
    """
    Decorator that adds Cache-Control: no-store headers to prevent browsers
    from caching protected pages. This stops back-button access after logout.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        response = make_response(f(*args, **kwargs))
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response
    return decorated_function


def generate_order_id():
    """Generates a unique 5-digit order identifier prefixed with CC-"""
    while True:
        order_id = f"CC-{random.randint(10000, 99999)}"
        if not Order.query.filter_by(order_id=order_id).first():
            return order_id


def generate_pickup_token():
    """Generates a unique pickup token (e.g. T-048) not currently duplicated among active orders."""
    active_tokens = {
        order.token_number
        for order in Order.query.filter(
            Order.status.in_(['CONFIRMED', 'PREPARING', 'READY FOR PICKUP'])
        ).all()
    }
    for i in range(1, 1000):
        token = f"T-{i:03d}"
        if token not in active_tokens:
            return token
    return f"T-{random.randint(100, 999):03d}"


def is_valid_status_transition(current_status, new_status):
    """Validates status transitions."""
    if new_status not in VALID_STATUSES:
        return False, f"Invalid status '{new_status}'. Allowed statuses are: {', '.join(VALID_STATUSES)}."
    if current_status == new_status:
        return False, f"Order is already marked as {current_status}."
    if current_status == 'COMPLETED':
        return False, "Order is already COMPLETED and its status cannot be modified."
    return True, None


def validate_order_payload(data):
    """Validate order-specific inputs; identity comes from the logged-in profile."""
    if not data or not isinstance(data, dict):
        return False, "Invalid request payload."

    pickup_slot = (data.get('pickup_slot') or '').strip()
    if not pickup_slot:
        return False, "Please select an upcoming pickup time window."

    items = data.get('items')
    if not items or not isinstance(items, list) or len(items) == 0:
        return False, "Your food tray is empty. Please add items before placing an order."

    for item in items:
        if not isinstance(item, dict) or not item.get('name') or item.get('price') is None:
            return False, "Invalid food items detected in order."
        qty = item.get('quantity', 1)
        if not isinstance(qty, (int, float)) or qty <= 0:
            return False, f"Invalid quantity for {item.get('name')}."

    return True, {
        'pickup_slot': pickup_slot,
        'payment_method': data.get('payment_method', 'Pay at Canteen Counter / UPI'),
        'items': items
    }


# ==========================================
# AUTHENTICATION ROUTES
# ==========================================

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Student registration route."""
    if current_user.is_authenticated:
        if current_user.is_student():
            return redirect(url_for('student_dashboard'))
        elif current_user.is_staff():
            return redirect(url_for('staff_dashboard'))
        elif current_user.is_admin():
            return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        student_id_val = request.form.get('student_id', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        department = request.form.get('department', 'Computer Science').strip()
        year_of_study = request.form.get('year_of_study', '3rd Year').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Validations
        if not full_name or len(full_name) < 2:
            flash('Please enter your full name (minimum 2 characters).', 'danger')
            return render_template('auth/register.html')

        if not student_id_val or len(student_id_val) < 3:
            flash('Please enter a valid Student ID / Roll Number.', 'danger')
            return render_template('auth/register.html')

        clean_phone = re.sub(r'[\s\-\(\)\+]', '', phone)
        if clean_phone.startswith('91') and len(clean_phone) == 12:
            clean_phone = clean_phone[2:]
        if not re.match(r'^[6-9]\d{9}$', clean_phone):
            flash('Please enter a valid 10-digit Indian mobile number.', 'danger')
            return render_template('auth/register.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('auth/register.html')

        if password != confirm_password:
            flash('Passwords do not match. Please verify.', 'danger')
            return render_template('auth/register.html')

        # Check existing user
        if User.query.filter((User.email == email) | (User.username == student_id_val)).first():
            flash('An account with this email or Student ID already exists. Please sign in.', 'warning')
            return redirect(url_for('login'))

        if Student.query.filter_by(student_id=student_id_val).first():
            flash('This Student ID is already registered.', 'warning')
            return render_template('auth/register.html')

        try:
            user = User(
                username=student_id_val,
                email=email,
                role='STUDENT',
                is_active=True
            )
            user.set_password(password)
            db.session.add(user)
            db.session.flush()

            student = Student(
                user_id=user.id,
                student_id=student_id_val,
                full_name=full_name,
                phone=f"+91 {clean_phone}",
                department=department,
                year_of_study=year_of_study
            )
            db.session.add(student)
            db.session.commit()

            login_user(user)
            flash(f'Welcome to College Connect, {full_name}! Your student account is ready.', 'success')
            return redirect(url_for('student_dashboard'))

        except Exception as e:
            db.session.rollback()
            flash(f'Registration error: {e}', 'danger')

    return render_template('auth/register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Role-aware user login route."""
    if current_user.is_authenticated:
        if current_user.is_student():
            return redirect(url_for('student_dashboard'))
        elif current_user.is_staff():
            return redirect(url_for('staff_dashboard'))
        elif current_user.is_admin():
            return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password = request.form.get('password', '')
        selected_role = request.form.get('role', 'STUDENT').strip().upper()
        remember = bool(request.form.get('remember'))

        user = User.query.filter(
            (User.email == identifier.lower()) | (User.username == identifier)
        ).first()

        if not user or not user.check_password(password):
            flash('Invalid email/username or password. Please verify.', 'danger')
            return render_template('auth/login.html')

        if not user.is_active:
            flash('This account is disabled. Please contact the campus canteen admin.', 'danger')
            return render_template('auth/login.html')

        # Check role permission (Admins can log in through any tab)
        if selected_role != user.role and user.role != 'ADMIN':
            flash(f'Account exists, but does not match role {selected_role}. Please select the {user.role} tab.', 'warning')
            return render_template('auth/login.html')

        login_user(user, remember=remember)
        session['_csrf_token'] = secrets.token_urlsafe(32)
        flash(f'Welcome back, {user.username}!', 'success')

        next_page = request.args.get('next')
        if is_safe_redirect_target(next_page):
            return redirect(next_page)

        if user.is_admin():
            return redirect(url_for('admin_dashboard'))
        elif user.is_staff():
            return redirect(url_for('staff_dashboard'))
        else:
            return redirect(url_for('student_dashboard'))

    return render_template('auth/login.html')


@app.route('/logout', methods=['POST'])
@login_required
def logout():
    """Logs out the active user and completely clears the session."""
    logout_user()
    session.clear()   # Wipes ALL session keys, including the login and CSRF tokens.
    response = make_response(redirect(url_for('home', signed_out=1)))
    # Prevent any cached authenticated pages being served from browser cache
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response


# ==========================================
# PUBLIC & STUDENT PAGES
# ==========================================

@app.route('/')
def home():
    """Renders the College Connect homepage."""
    # Feature real catalogue records, ordered by historical quantity where
    # available. Keep every field (including availability) sourced from DB.
    popularity_rows = (
        db.session.query(OrderItem.food_item_id, func.sum(OrderItem.quantity))
        .filter(OrderItem.food_item_id.isnot(None))
        .group_by(OrderItem.food_item_id)
        .all()
    )
    popularity = {food_id: quantity for food_id, quantity in popularity_rows}
    db_items = FoodItem.query.all()
    db_items.sort(key=lambda item: (-popularity.get(item.id, 0), item.id))
    return render_template('index.html', popular_items=db_items[:4])


@app.route('/menu')
def menu():
    """Renders the Food Menu page from the database food items."""
    db_items = FoodItem.query.order_by(FoodItem.id.asc()).all()
    items_data = [item.to_dict() for item in db_items] if db_items else FOOD_ITEMS
    return render_template('menu.html', items=items_data, categories=CATEGORIES)


def _assistant_is_order_question(message):
    return bool(re.search(
        r'\b(track|tracking|pickup token|pick.?up token|my\s+(?:latest\s+)?order|order\s+(?:status|update|progress|token|history))\b|\bCC-\d+\b',
        message,
        re.I,
    ))


def _assistant_budget(message):
    patterns = (
        r'\b(?:under|below|within|up\s*to|upto|budget(?:\s+(?:of|is))?|for)\s*(?:₹|rs\.?\s*)?(\d+(?:\.\d{1,2})?)',
        r'(?:₹|rs\.?\s*)(\d+(?:\.\d{1,2})?)',
    )
    for pattern in patterns:
        match = re.search(pattern, message, re.I)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
    return None


def _assistant_food_label(item):
    availability = 'available' if item.available else 'currently unavailable'
    food_type = 'vegetarian' if item.is_veg else 'non-vegetarian'
    return f'{item.name} — ₹{item.price:g}, {availability}, {food_type}'


def _assistant_menu_reply(message):
    """Answer food and budget questions from current catalogue rows only."""
    foods = FoodItem.query.order_by(FoodItem.name.asc()).all()
    if not foods:
        return 'The canteen menu is not available right now. Please check the Food Menu page again soon.'

    lowered = message.casefold()
    mentioned_item = next((item for item in sorted(foods, key=lambda row: len(row.name), reverse=True)
                          if item.name.casefold() in lowered), None)
    if mentioned_item:
        return _assistant_food_label(mentioned_item) + '.'

    budget = _assistant_budget(message)
    wants_nonveg = bool(re.search(r'\b(non.?veg|non.?vegetarian|chicken|egg)\b', lowered))
    wants_veg = not wants_nonveg and bool(re.search(r'\b(veg|vegetarian)\b', lowered))
    if budget is not None:
        choices = [item for item in foods if item.available and item.price <= budget]
        if wants_veg:
            choices = [item for item in choices if item.is_veg]
        elif wants_nonveg:
            choices = [item for item in choices if not item.is_veg]
        choices.sort(key=lambda item: (item.price, item.name.casefold()))
        if not choices:
            return f'I couldn’t find an available menu item within ₹{budget:g}' + (' in that food category.' if wants_veg or wants_nonveg else '.')
        recommendations = '\n'.join(f'• {_assistant_food_label(item)}' for item in choices[:5])
        return f'Here are current options within ₹{budget:g}:\n{recommendations}'

    if wants_veg or wants_nonveg:
        foods = [item for item in foods if (item.is_veg if wants_veg else not item.is_veg)]
    if re.search(r'\b(unavailable|sold\s*out|not available)\b', lowered):
        foods = [item for item in foods if not item.available]
    else:
        foods = [item for item in foods if item.available]
    if not foods:
        return 'There are no matching items in the current menu right now.'

    items_text = '\n'.join(f'• {_assistant_food_label(item)}' for item in foods[:10])
    remaining = len(foods) - min(len(foods), 10)
    if remaining:
        items_text += f'\n…and {remaining} more. Open Food Menu to see the full list.'
    return 'Here’s what the current canteen menu shows:\n' + items_text


def _assistant_order_reply(message):
    """Return only the authenticated student's own order progress and token."""
    if not current_user.is_authenticated:
        return jsonify({
            'success': False,
            'error': 'Please sign in as a student to check your order status and pickup token.',
            'needs_login': True,
        }), 401
    if current_user.role != 'STUDENT':
        return jsonify({'success': False, 'error': 'Order tracking is available to signed-in students only.'}), 403

    student = current_user.student_profile
    if not student:
        return jsonify({'success': False, 'error': 'Your student profile is unavailable. Please contact the college administrator.'}), 403

    ownership = or_(
        Order.user_id == current_user.id,
        (Order.user_id.is_(None) & or_(
            Order.student_profile_id == student.id,
            Order.student_id == student.student_id,
        )),
    )
    order_id_match = re.search(r'\bCC-\d+\b', message, re.I)
    query = Order.query.filter(ownership)
    if order_id_match:
        order = query.filter_by(order_id=order_id_match.group(0).upper()).first()
    else:
        order = query.order_by(Order.created_at.desc(), Order.id.desc()).first()

    if not order:
        # Use the same response for missing and non-owned order IDs.
        if order_id_match:
            return jsonify({'success': False, 'error': 'I couldn’t find that order in your account.'}), 404
        return jsonify({'success': True, 'intent': 'order_tracking', 'reply': 'There are no orders in your account yet. Once you place an order, I can share its status and pickup token.'}), 200

    status_labels = {
        'CONFIRMED': 'Confirmed',
        'PREPARING': 'Preparing',
        'READY FOR PICKUP': 'Ready for Pickup',
        'COMPLETED': 'Completed',
    }
    reply = (
        f'Order {order.order_id} is {status_labels.get(order.status, "In progress")}. '
        f'Pickup token: {order.token_number}. Pickup time: {order.pickup_slot}.'
    )
    return jsonify({'success': True, 'intent': 'order_tracking', 'reply': reply}), 200


@app.route('/api/assistant', methods=['POST'])
def assistant_chat():
    """Read-only canteen assistant backed by the catalogue and owned orders."""
    payload = request.get_json(silent=True)
    message = payload.get('message', '') if isinstance(payload, dict) else ''
    if not isinstance(message, str) or not message.strip():
        return jsonify({'success': False, 'error': 'Enter a question to continue.'}), 400
    message = message.strip()
    if len(message) > 500:
        return jsonify({'success': False, 'error': 'Please keep your question under 500 characters.'}), 400

    try:
        if _assistant_is_order_question(message):
            return _assistant_order_reply(message)

        menu_intent = re.search(
            r'\b(menu|food|price|cost|available|availability|veg|vegetarian|non.?veg|budget|recommend|recommendation|suggest|eat|dish|item|sold\s*out)\b|₹|\brs\.?\s*\d',
            message,
            re.I,
        )
        mentioned_food = any(item.name.casefold() in message.casefold() for item in FoodItem.query.all())
        if menu_intent or mentioned_food:
            return jsonify({'success': True, 'intent': 'menu', 'reply': _assistant_menu_reply(message)}), 200

        if re.match(r'^(hi|hello|hey|good morning|good afternoon|good evening)\b', message, re.I):
            reply = 'Hi! I can help you find canteen food, check current prices and availability, recommend meals within a budget, or track your own order after you sign in.'
        else:
            reply = 'I can help with the current food menu, prices, availability, vegetarian choices, budget recommendations, and your own order status after sign-in. What would you like to check?'
        return jsonify({'success': True, 'intent': 'help', 'reply': reply}), 200
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception('Canteen assistant database request failed')
        return jsonify({
            'success': False,
            'error': 'The assistant could not read canteen data right now. Please retry shortly.',
        }), 503
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Canteen assistant request failed')
        return jsonify({
            'success': False,
            'error': 'The assistant could not complete that request. Please retry shortly.',
        }), 500


@app.route('/cart')
@login_required
@role_required('STUDENT')
@no_cache
def cart():
    """Renders the Shopping Cart page. Requires authentication."""
    return render_template('cart.html')


@app.route('/checkout')
@login_required
@role_required('STUDENT')
@no_cache
def checkout():
    """Renders the Student Checkout page. Requires authentication."""
    student = current_user.student_profile
    if not student:
        flash('Your student profile is unavailable. Please contact the college administrator.', 'danger')
        return redirect(url_for('student_dashboard'))
    return render_template('checkout.html', student=student)


@app.route('/order-confirmation')
@login_required
@role_required('STUDENT')
@no_cache
def order_confirmation():
    """Renders the Order Confirmation / Live Tracking page. Requires authentication."""
    order_id = request.args.get('order_id')
    order_record = None
    if order_id:
        order_obj = Order.query.filter_by(order_id=order_id).first()
        if order_obj:
            student = current_user.student_profile if current_user.is_student() else None
            owns_order = order_obj.user_id == current_user.id or (
                student is not None and order_obj.student_id == student.student_id
            )
            if not owns_order:
                abort(404)
            order_record = order_obj.to_dict()
    return render_template('order_confirmation.html', order=order_record)


# ==========================================
# ROLE-BASED DASHBOARDS
# ==========================================

@app.route('/student-dashboard')
@login_required
@role_required('STUDENT', 'ADMIN')
def student_dashboard():
    """Student portal displaying profile, active orders, and order history."""
    student = current_user.student_profile

    # Orders placed by this user (or matching student ID)
    if student:
        orders = Order.query.filter(
            (Order.user_id == current_user.id) | (Order.student_id == student.student_id)
        ).order_by(Order.created_at.desc()).all()
    else:
        orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()

    active_orders = [o for o in orders if o.status in ['CONFIRMED', 'PREPARING', 'READY FOR PICKUP']]
    total_spent = sum(o.total_amount for o in orders)

    return render_template(
        'student_dashboard.html',
        student=student,
        orders=orders,
        active_orders=active_orders,
        total_spent=total_spent
    )


@app.route('/staff-dashboard')
@login_required
@role_required('STAFF', 'ADMIN')
def staff_dashboard():
    """Canteen Staff Kitchen & Orders Dashboard."""
    return render_template('staff_dashboard.html')


@app.route('/admin-dashboard')
@login_required
@role_required('ADMIN')
def admin_dashboard():
    """Comprehensive Admin Hub: users, menu items, orders, and sales reports."""
    all_orders = Order.query.order_by(Order.created_at.desc()).all()
    food_items = FoodItem.query.order_by(FoodItem.category.asc(), FoodItem.name.asc()).all()
    users = User.query.order_by(User.created_at.desc()).all()

    total_orders = len(all_orders)
    total_revenue = sum(o.total_amount for o in all_orders)
    student_count = Student.query.count()

    # Sales Reports: Top Dishes
    from collections import Counter
    dish_counter = Counter()
    category_revenue = Counter()

    for o in all_orders:
        for item in o.items:
            dish_counter[item.name] += item.quantity
            category_revenue[item.category or 'General'] += item.price * item.quantity

    top_dishes = dish_counter.most_common(5)
    category_rev_list = category_revenue.most_common()

    return render_template(
        'admin_dashboard.html',
        all_orders=all_orders,
        food_items=food_items,
        users=users,
        total_orders=total_orders,
        total_revenue=total_revenue,
        student_count=student_count,
        top_dishes=top_dishes,
        category_revenue=category_rev_list
    )


# ==========================================
# ADMIN MANAGEMENT ACTIONS
# ==========================================

@app.route('/admin/food-items/add', methods=['POST'])
@login_required
@role_required('ADMIN')
def admin_add_food_item():
    """Admin action to add a new food item."""
    name = request.form.get('name', '').strip()
    category = request.form.get('category', 'Snacks').strip()
    price = request.form.get('price', 0)
    description = request.form.get('description', '').strip()
    image = request.form.get('image', '').strip() or 'https://images.unsplash.com/photo-1546833999-b9f581a1996d?w=500&auto=format&fit=crop&q=60'
    is_veg = bool(request.form.get('is_veg'))

    if not name or not price:
        flash('Dish name and valid price are required.', 'danger')
        return redirect(url_for('admin_dashboard'))

    try:
        new_item = FoodItem(
            name=name,
            category=category,
            price=float(price),
            description=description,
            image=image,
            available=True,
            is_veg=is_veg
        )
        db.session.add(new_item)
        db.session.commit()
        flash(f'Dish "{name}" added to canteen catalog successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding dish: {e}', 'danger')

    return redirect(url_for('admin_dashboard'))


@app.route('/admin/food-items/<int:item_id>/toggle', methods=['POST'])
@login_required
@role_required('ADMIN')
def admin_toggle_food_availability(item_id):
    """Admin action to toggle food item availability (In Stock / Sold Out)."""
    item = FoodItem.query.get_or_404(item_id)
    item.available = not item.available
    db.session.commit()
    status_str = "In Stock" if item.available else "Sold Out"
    flash(f'"{item.name}" marked as {status_str}.', 'info')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/users/add', methods=['POST'])
@login_required
@role_required('ADMIN')
def admin_add_user():
    """Admin action to create a Staff or Admin account."""
    username = request.form.get('username', '').strip()
    full_name = request.form.get('full_name', '').strip()
    email = request.form.get('email', '').strip().lower()
    role = request.form.get('role', 'STAFF').strip().upper()
    phone = request.form.get('phone', '').strip()
    staff_id = request.form.get('staff_id', '').strip() or f"STF-{random.randint(100, 999)}"
    password = request.form.get('password', '')

    if role not in {'STAFF', 'ADMIN'}:
        flash('Only Staff or Admin accounts can be created here.', 'danger')
        return redirect(url_for('admin_dashboard'))

    if not username or not email or len(password) < 6:
        flash('Valid username, email, and password (min 6 chars) are required.', 'danger')
        return redirect(url_for('admin_dashboard'))

    if User.query.filter((User.email == email) | (User.username == username)).first():
        flash('User with this email or username already exists.', 'warning')
        return redirect(url_for('admin_dashboard'))

    try:
        user = User(
            username=username,
            email=email,
            role=role,
            is_active=True
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        if role == 'STAFF':
            staff = Staff(
                user_id=user.id,
                staff_id=staff_id,
                full_name=full_name,
                role_title='Canteen Staff',
                phone=phone
            )
            db.session.add(staff)

        db.session.commit()
        flash(f'{role} account for {username} created successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating user: {e}', 'danger')

    return redirect(url_for('admin_dashboard'))


# ==========================================
# ORDERING & RESTFUL APIS
# ==========================================

@app.route('/api/orders', methods=['POST'])
@login_required
@role_required('STUDENT')
def create_order():
    """
    Validates order details, calculates totals, generates a unique order ID
    and unique pickup token, stores order and payment records, and returns confirmation.
    """
    data = request.get_json(silent=True)
    is_valid, result = validate_order_payload(data)

    if not is_valid:
        return jsonify({'success': False, 'error': result}), 400

    student = current_user.student_profile
    if not student:
        return jsonify({'success': False, 'error': 'A student profile is required to place an order.'}), 400

    # Rebuild order lines from the live catalog; prices and labels from the
    # browser are untrusted and unavailable items must not be orderable.
    catalog_items = {}
    try:
        for requested in result['items']:
            item_id = requested.get('id')
            if isinstance(item_id, bool) or not isinstance(item_id, int):
                raise ValueError('Invalid food item in order. Please refresh the menu.')
            quantity = requested.get('quantity', 1)
            if isinstance(quantity, bool) or not isinstance(quantity, int) or not 1 <= quantity <= 99:
                raise ValueError('Each item quantity must be a whole number between 1 and 99.')
            food = FoodItem.query.filter_by(id=item_id, available=True).first()
            if not food:
                raise ValueError('One or more selected items are unavailable. Please refresh the menu.')
            if item_id in catalog_items:
                catalog_items[item_id]['quantity'] += quantity
            else:
                catalog_items[item_id] = {
                    'id': food.id, 'name': food.name, 'category': food.category,
                    'price': float(food.price), 'image': food.image, 'quantity': quantity
                }
    except (TypeError, ValueError) as error:
        return jsonify({'success': False, 'error': str(error)}), 400

    result['items'] = list(catalog_items.values())
    result['student_name'] = student.full_name
    result['student_id'] = student.student_id
    result['phone'] = student.phone

    cleaned = result
    order_id = generate_order_id()
    token_number = generate_pickup_token()

    subtotal = sum(float(item['price']) * int(item['quantity']) for item in cleaned['items'])
    total_amount = subtotal
    item_count = sum(int(item['quantity']) for item in cleaned['items'])

    user_id = current_user.id
    student_profile_id = student.id

    # Create Order row
    order = Order(
        order_id=order_id,
        token_number=token_number,
        status='CONFIRMED',
        student_name=cleaned['student_name'],
        student_id=cleaned['student_id'],
        phone=cleaned['phone'],
        pickup_slot=cleaned['pickup_slot'],
        payment_method=cleaned['payment_method'],
        subtotal=subtotal,
        total_amount=total_amount,
        item_count=item_count,
        user_id=user_id,
        student_profile_id=student_profile_id
    )

    db.session.add(order)
    db.session.flush()

    # Create Order Items
    for item in cleaned['items']:
        order_item = OrderItem(
            order_id=order.id,
            food_item_id=item.get('id'),
            name=item.get('name'),
            category=item.get('category'),
            price=float(item.get('price')),
            quantity=int(item.get('quantity', 1)),
            image=item.get('image')
        )
        db.session.add(order_item)

    # Create Payment Record
    payment = Payment(
        order_id=order.id,
        payment_id=f"PAY-{order_id}",
        amount=total_amount,
        payment_method=cleaned['payment_method'],
        payment_status='PENDING'
    )
    db.session.add(payment)

    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Order successfully confirmed and assigned to canteen queue.',
        'order': order.to_dict()
    }), 201


@app.route('/api/orders/<order_id>')
@login_required
@role_required('STUDENT')
def get_order_details(order_id):
    """Retrieves order details for a given order_id from database."""
    order = Order.query.filter_by(order_id=order_id).first()
    if not order:
        return jsonify({'success': False, 'error': 'Order not found.'}), 404
    student = current_user.student_profile
    if not student or (order.user_id != current_user.id and order.student_id != student.student_id):
        return jsonify({'success': False, 'error': 'Order not found.'}), 404
    return jsonify({'success': True, 'order': order.to_dict()}), 200


@app.route('/api/staff/orders')
@login_required
@role_required('STAFF', 'ADMIN')
def api_staff_orders():
    """Returns list of orders with optional status and search filters."""
    status_filter = request.args.get('status', 'all').strip()
    search_query = request.args.get('search', '').strip().lower()

    query = Order.query.order_by(Order.created_at.desc())

    if status_filter and status_filter.lower() != 'all':
        query = query.filter(Order.status == status_filter.upper())

    orders = query.all()

    if search_query:
        orders = [
            o for o in orders
            if search_query in o.order_id.lower()
            or search_query in o.student_name.lower()
            or search_query in o.token_number.lower()
            or search_query in o.student_id.lower()
            or search_query in o.phone.lower()
        ]

    return jsonify({
        'success': True,
        'orders': [o.to_dict() for o in orders],
        'count': len(orders)
    }), 200


@app.route('/api/staff/stats')
@login_required
@role_required('STAFF', 'ADMIN')
def api_staff_stats():
    """Returns summary counts for staff dashboard counter cards."""
    total = Order.query.count()
    confirmed = Order.query.filter_by(status='CONFIRMED').count()
    preparing = Order.query.filter_by(status='PREPARING').count()
    ready = Order.query.filter_by(status='READY FOR PICKUP').count()
    completed = Order.query.filter_by(status='COMPLETED').count()

    return jsonify({
        'success': True,
        'stats': {
            'total': total,
            'pending': confirmed,
            'confirmed': confirmed,
            'preparing': preparing,
            'ready': ready,
            'completed': completed
        }
    }), 200


@app.route('/api/staff/orders/<order_id>/status', methods=['POST'])
@login_required
@role_required('STAFF', 'ADMIN')
def api_update_order_status(order_id):
    """Updates order status and synchronizes payment record."""
    order = Order.query.filter_by(order_id=order_id).first()
    if not order:
        return jsonify({'success': False, 'error': f"Order #{order_id} not found."}), 404

    data = request.get_json(silent=True) or {}
    new_status = (data.get('status') or '').strip().upper()

    is_valid, err_msg = is_valid_status_transition(order.status, new_status)
    if not is_valid:
        return jsonify({'success': False, 'error': err_msg}), 400

    order.status = new_status
    order.updated_at = datetime.utcnow()

    # Mark payment as COMPLETED when order is completed
    if new_status == 'COMPLETED' and order.payment:
        order.payment.payment_status = 'COMPLETED'
        order.payment.paid_at = datetime.utcnow()

    db.session.commit()

    return jsonify({
        'success': True,
        'message': f"Order #{order.order_id} status updated to {new_status}.",
        'order': order.to_dict()
    }), 200


@app.route('/health')
def health():
    """Report healthy only when the configured database answers a query."""
    try:
        db.session.execute(text('SELECT 1')).scalar_one()
        status_code = 200
        status = 'healthy'
    except Exception:
        db.session.rollback()
        status_code = 503
        status = 'unhealthy'

    return jsonify({
        'status': status,
        'service': 'College Connect',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'version': '2.0.0',
        'database_engine': db_engine_info
    }), status_code


# ==========================================
# INITIALIZATION HOOK
# ==========================================

def initialize_database():
    """Creates tables and seeds default catalog and users if empty."""
    with app.app_context():
        try:
            # If running on local SQLite fallback, ensure columns match latest models
            if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']:
                import sqlite3
                sqlite_file = db.engine.url.database
                expected_local_db = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'college_connect.db')
                if sqlite_file and sqlite_file != ':memory:' and os.path.normcase(os.path.abspath(sqlite_file)) == os.path.normcase(expected_local_db) and os.path.exists(sqlite_file):
                    c = sqlite3.connect(sqlite_file)
                    cur = c.cursor()
                    tables = [t[0] for t in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
                    if 'orders' in tables:
                        cols = [col[1] for col in cur.execute("PRAGMA table_info(orders)").fetchall()]
                        if 'user_id' not in cols:
                            cur.execute("ALTER TABLE orders ADD COLUMN user_id INTEGER")
                        if 'student_profile_id' not in cols:
                            cur.execute("ALTER TABLE orders ADD COLUMN student_profile_id INTEGER")
                    if 'order_items' in tables:
                        item_cols = [col[1] for col in cur.execute("PRAGMA table_info(order_items)").fetchall()]
                        if 'food_item_id' not in item_cols:
                            cur.execute("ALTER TABLE order_items ADD COLUMN food_item_id INTEGER")
                    c.commit()
                    c.close()

            db.create_all()

            # Seed food catalog if empty
            if FoodItem.query.count() == 0:
                for item in FOOD_ITEMS:
                    food = FoodItem(
                        name=item['name'],
                        category=item['category'],
                        price=float(item['price']),
                        description=item['description'],
                        image=item['image'],
                        available=item.get('available', True),
                        is_veg=item.get('is_veg', True)
                    )
                    db.session.add(food)
                db.session.commit()

            # Seed default accounts if empty
            if User.query.count() == 0:
                # Admin
                admin = User(username='admin', email='admin@collegeconnect.com', role='ADMIN')
                admin.set_password('Admin@123')
                db.session.add(admin)

                # Staff
                staff_u = User(username='staff', email='staff@collegeconnect.com', role='STAFF')
                staff_u.set_password('Staff@123')
                db.session.add(staff_u)
                db.session.flush()

                staff_p = Staff(
                    user_id=staff_u.id,
                    staff_id='STF-001',
                    full_name='Chef Ramesh Sharma',
                    role_title='Canteen Kitchen Head',
                    phone='+91 9876543210'
                )
                db.session.add(staff_p)

                # Student
                stud_u = User(username='student', email='student@collegeconnect.com', role='STUDENT')
                stud_u.set_password('Student@123')
                db.session.add(stud_u)
                db.session.flush()

                stud_p = Student(
                    user_id=stud_u.id,
                    student_id='CS2026-001',
                    full_name='Aarav Sharma',
                    phone='+91 9876543210',
                    department='Computer Science',
                    year_of_study='3rd Year'
                )
                db.session.add(stud_p)

                db.session.commit()

        except Exception as e:
            print(f"[Database Init Notice]: {e}")


if not is_production():
    # Development keeps the existing local schema setup and demo seed behavior.
    # Production databases must be provisioned and migrated explicitly.
    initialize_database()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(
        host='0.0.0.0' if is_production() else '127.0.0.1',
        port=port,
        debug=app.config['DEBUG']
    )
