"""Security regression checks; always use an isolated in-memory test database."""

import os
import re
from pathlib import Path

os.environ['APP_ENV'] = 'test'
os.environ['TEST_DATABASE_URL'] = 'sqlite:///:memory:'
os.environ.pop('DATABASE_URL', None)

from app import app, db
from models import User, Student, FoodItem, Order
import db_config
from test_support import post_json


def csrf_token(client, path='/'):
    response = client.get(path)
    assert response.status_code == 200, (path, response.status_code)
    match = re.search(rb'<meta name="csrf-token" content="([^"]+)">', response.data)
    assert match, 'CSRF meta token missing'
    return match.group(1).decode()


def login(client, username, password, role):
    response = client.get('/login')
    token = re.search(rb'name="csrf_token" value="([^"]+)"', response.data).group(1).decode()
    return client.post('/login', data={
        'csrf_token': token, 'identifier': username, 'password': password, 'role': role
    }, follow_redirects=True)


def api_headers(client):
    return {'X-CSRF-Token': csrf_token(client)}


assert app.config['SQLALCHEMY_DATABASE_URI'] == 'sqlite:///:memory:'
client = app.test_client()

# Anonymous callers cannot read staff data or access protected dashboards.
assert client.get('/api/staff/orders').status_code == 401
assert client.get('/api/staff/stats').status_code == 401
assert client.get('/admin-dashboard').status_code == 302
assert client.get('/staff-dashboard').status_code == 302
assert post_json(client, '/api/orders', {}).status_code == 401

# A student cannot call staff/admin APIs, but can create an order using the
# server-side catalog price and their own registered profile details.
assert login(client, 'student', 'Student@123', 'STUDENT').status_code == 200
assert client.get('/api/staff/stats').status_code == 403
assert client.get('/admin-dashboard').status_code == 302
assert client.get('/staff-dashboard').status_code == 302

with app.app_context():
    student_user = User.query.filter_by(username='student').first()
    menu_item = FoodItem.query.filter_by(available=True).first()
    assert student_user and student_user.student_profile and menu_item
    student_profile = student_user.student_profile
    food_id = menu_item.id
    expected_price = float(menu_item.price)
    expected_name = menu_item.name

order_response = client.post('/api/orders', json={
    'student_name': 'Forged Name', 'student_id': 'FAKE-999', 'phone': '9876543210',
    'pickup_slot': 'Immediate (15-20 Mins)',
    'items': [{'id': food_id, 'name': 'Forged Dish', 'price': 0.01, 'quantity': 1}]
}, headers=api_headers(client))
assert order_response.status_code == 201, order_response.get_data(as_text=True)
created_order = order_response.get_json()['order']
assert created_order['student_name'] == student_profile.full_name
assert created_order['student_id'] == student_profile.student_id
assert created_order['items'][0]['name'] == expected_name
assert created_order['total_amount'] == expected_price
assert client.get(f"/api/orders/{created_order['order_id']}").status_code == 200
assert client.get(f"/order-confirmation?order_id={created_order['order_id']}").status_code == 200

with app.app_context():
    db.session.add(FoodItem(
        name='Regression Non Veg Item', category='Lunch', price=75,
        available=True, is_veg=False
    ))
    db.session.commit()
menu_page = client.get('/menu').get_data(as_text=True)
assert 'class="veg-indicator" title="Vegetarian"' in menu_page
assert 'class="non-veg-indicator" title="Non-vegetarian"' in menu_page

# A different student cannot read or render the first student's order.
with app.app_context():
    other = User(username='second_test_student', email='second_test_student@example.test', role='STUDENT')
    other.set_password('Student@123')
    db.session.add(other)
    db.session.flush()
    db.session.add(Student(
        user_id=other.id, student_id='TEST-SECOND-001', full_name='Second Student',
        phone='+91 9876543211'
    ))
    db.session.commit()

other_client = app.test_client()
assert login(other_client, 'second_test_student', 'Student@123', 'STUDENT').status_code == 200
assert other_client.get(f"/api/orders/{created_order['order_id']}").status_code == 404
assert other_client.get(f"/order-confirmation?order_id={created_order['order_id']}").status_code == 404

# Staff role can use the staff endpoints; a missing CSRF token blocks writes.
staff_client = app.test_client()
assert login(staff_client, 'staff', 'Staff@123', 'STAFF').status_code == 200
assert staff_client.get('/api/staff/orders').status_code == 200
assert staff_client.get('/api/staff/stats').status_code == 200
assert post_json(staff_client, '/api/orders', {}).status_code == 403
assert staff_client.post(
    f"/api/staff/orders/{created_order['order_id']}/status",
    json={'status': 'PREPARING'}
).status_code == 400
status_response = staff_client.post(
    f"/api/staff/orders/{created_order['order_id']}/status",
    json={'status': 'PREPARING'}, headers=api_headers(staff_client)
)
assert status_response.status_code == 200, status_response.get_data(as_text=True)

# Logout is POST-only and removes the complete Flask session.
logout_response = staff_client.post('/logout', data={'csrf_token': csrf_token(staff_client)})
assert logout_response.status_code == 302
with staff_client.session_transaction() as session:
    assert not session
assert staff_client.get('/logout').status_code == 405

# User-controlled text is escaped at the dynamic HTML insertion points.
root = Path(__file__).parent
staff_template = (root / 'templates' / 'staff_dashboard.html').read_text(encoding='utf-8')
cart_template = (root / 'templates' / 'cart.html').read_text(encoding='utf-8')
confirmation_template = (root / 'templates' / 'order_confirmation.html').read_text(encoding='utf-8')
cart_script = (root / 'static' / 'js' / 'cart.js').read_text(encoding='utf-8')
assert 'escapeHtml(order.student_name)' in staff_template
assert 'escapeHtml(i.name)' in staff_template
assert 'escapeHtml(item.name)' in cart_template and 'function escapeHtml' in cart_script
assert 'escapeHtml(item.name)' in confirmation_template

# Production database failures raise instead of selecting local SQLite.
original = (db_config.APP_ENV, db_config.DB_HOST, db_config.DB_PORT, db_config.DB_PASSWORD,
            db_config.DB_USER, db_config.DB_NAME, os.environ.pop('DATABASE_URL', None))
try:
    db_config.APP_ENV = 'production'
    db_config.DB_HOST = '127.0.0.1'
    db_config.DB_PORT = '1'
    db_config.DB_PASSWORD = 'test-only'
    db_config.DB_USER = 'test'
    db_config.DB_NAME = 'test'
    try:
        db_config.get_active_database_uri()
    except RuntimeError as error:
        assert 'SQLite fallback is disabled' in str(error)
    else:
        raise AssertionError('Production silently accepted an unreachable MySQL server.')
finally:
    (db_config.APP_ENV, db_config.DB_HOST, db_config.DB_PORT, db_config.DB_PASSWORD,
     db_config.DB_USER, db_config.DB_NAME) = original[:6]
    if original[6] is not None:
        os.environ['DATABASE_URL'] = original[6]

print('PASS: security, ownership, CSRF, logout, XSS escaping, and production database checks')
