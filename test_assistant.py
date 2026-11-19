"""Canteen assistant regression tests; all data stays in in-memory SQLite."""
import os
from unittest.mock import patch
from sqlalchemy.exc import SQLAlchemyError

os.environ['APP_ENV'] = 'test'
os.environ['TEST_DATABASE_URL'] = 'sqlite:///:memory:'
os.environ.pop('DATABASE_URL', None)
os.environ.pop('MYSQL_URL', None)

from app import app, db
from models import FoodItem, Order, Payment, Student, User
from test_support import login, post_json

assert app.config['SQLALCHEMY_DATABASE_URI'] == 'sqlite:///:memory:'
assistant_route = next(rule for rule in app.url_map.iter_rules() if rule.endpoint == 'assistant_chat')
assert assistant_route.rule == '/api/assistant' and 'POST' in assistant_route.methods

anonymous = app.test_client()
for path in ('/', '/menu', '/login'):
    page = anonymous.get(path)
    assert page.status_code == 200
    assert b'assistantLauncher' in page.data and b'canteenAssistantPanel' in page.data
    assert b'data-assistant-endpoint="/api/assistant"' in page.data
    assert b'assistant.js?v=2' in page.data
print('PASS: Assistant widget is included on homepage, menu, and login pages')

# A missing CSRF token must not reach the chatbot endpoint.
assert anonymous.post('/api/assistant', json={'message': 'Show the menu'}).status_code == 400

menu_response = post_json(anonymous, '/api/assistant', {'message': 'Show me the current menu'})
assert menu_response.status_code == 200, menu_response.get_data(as_text=True)
menu_reply = menu_response.get_json()['reply']
with app.app_context():
    available_food = FoodItem.query.filter_by(available=True).order_by(FoodItem.price.asc()).first()
    assert available_food
    veg_food = FoodItem.query.filter_by(available=True, is_veg=True).order_by(FoodItem.price.asc()).first()
    assert veg_food
assert available_food.name in menu_reply and '₹' in menu_reply and 'available' in menu_reply
print('PASS: Public menu responses use current database items and availability')

budget = veg_food.price
budget_response = post_json(anonymous, '/api/assistant', {
    'message': f'Recommend vegetarian food under ₹{budget:g}'
})
assert budget_response.status_code == 200
budget_reply = budget_response.get_json()['reply']
assert veg_food.name in budget_reply and f'₹{budget:g}' in budget_reply
assert 'vegetarian' in budget_reply
print('PASS: Dietary and budget recommendations use live catalogue prices')

specific_response = post_json(anonymous, '/api/assistant', {
    'message': f'Is {available_food.name} available and what is its price?'
})
assert specific_response.status_code == 200
assert available_food.name in specific_response.get_json()['reply']
assert f'₹{available_food.price:g}' in specific_response.get_json()['reply']
assert 'available' in specific_response.get_json()['reply']
print('PASS: Item availability and price questions are answered from the catalogue')

with patch.object(app.logger, 'exception'), patch('app._assistant_menu_reply', side_effect=SQLAlchemyError('simulated database outage')):
    failed_menu = post_json(anonymous, '/api/assistant', {'message': 'Show me the menu'})
assert failed_menu.status_code == 503
assert failed_menu.is_json and 'retry shortly' in failed_menu.get_json()['error']
print('PASS: Backend database exceptions return a useful JSON error and do not expose traceback details')

how_to_order = post_json(anonymous, '/api/assistant', {
    'message': f'How do I order {available_food.name}?'
})
assert how_to_order.status_code == 200 and available_food.name in how_to_order.get_json()['reply']
print('PASS: Food-ordering questions are not mistaken for private order tracking')

anonymous_tracking = post_json(anonymous, '/api/assistant', {'message': 'Track my latest order'})
assert anonymous_tracking.status_code == 401
assert anonymous_tracking.get_json()['needs_login'] is True
print('PASS: Anonymous users cannot access order tracking')

student_client = app.test_client()
assert login(student_client, 'student', 'Student@123', 'STUDENT').status_code == 200
other_user = None
with app.app_context():
    student_user = User.query.filter_by(username='student').first()
    assert student_user and student_user.student_profile
    student_profile = student_user.student_profile
    order = Order(
        order_id='CC-61001', token_number='T-771', status='READY FOR PICKUP',
        student_name=student_profile.full_name, student_id=student_profile.student_id,
        phone=student_profile.phone, pickup_slot='12:30 PM - Lunch Slot 1',
        subtotal=120, total_amount=120, item_count=1, user_id=student_user.id,
        student_profile_id=student_profile.id,
    )
    db.session.add(order)
    latest_order = Order(
        order_id='CC-61002', token_number='T-772', status='PREPARING',
        student_name=student_profile.full_name, student_id=student_profile.student_id,
        phone=student_profile.phone, pickup_slot='01:00 PM - Lunch Slot 2',
        subtotal=80, total_amount=80, item_count=1, user_id=student_user.id,
        student_profile_id=student_profile.id,
    )
    db.session.add(latest_order)
    other_user = User(username='assistant_other', email='assistant_other@example.test', role='STUDENT')
    other_user.set_password('TestOnly@123')
    db.session.add(other_user)
    db.session.flush()
    other_profile = Student(
        user_id=other_user.id, student_id='ASST-OTHER-1', full_name='Other Test Student',
        phone='+91 9000000012',
    )
    db.session.add(other_profile)
    db.session.commit()
    student_name = student_profile.full_name
    student_phone = student_profile.phone

with app.app_context():
    before_counts = (FoodItem.query.count(), Order.query.count(), Payment.query.count())
own_tracking = post_json(student_client, '/api/assistant', {'message': 'Track my order CC-61001'})
assert own_tracking.status_code == 200, own_tracking.get_data(as_text=True)
tracking_reply = own_tracking.get_json()['reply']
assert 'CC-61001' in tracking_reply and 'T-771' in tracking_reply and 'Ready for Pickup' in tracking_reply
assert student_name not in tracking_reply and student_phone not in tracking_reply
assert 'payment' not in tracking_reply.casefold()
with app.app_context():
    assert (FoodItem.query.count(), Order.query.count(), Payment.query.count()) == before_counts
print('PASS: Students can view their own status and pickup token without exposing profile/payment data')

latest_tracking = post_json(student_client, '/api/assistant', {'message': 'Track my latest order and pickup token'})
assert latest_tracking.status_code == 200
assert 'CC-61002' in latest_tracking.get_json()['reply'] and 'T-772' in latest_tracking.get_json()['reply']
assert 'T-771' not in latest_tracking.get_json()['reply']
print('PASS: Latest-order requests return the newest order and token belonging to the signed-in student')

other_client = app.test_client()
assert login(other_client, 'assistant_other', 'TestOnly@123', 'STUDENT').status_code == 200
cross_account = post_json(other_client, '/api/assistant', {'message': 'Track order CC-61001'})
assert cross_account.status_code == 404
assert 'T-771' not in cross_account.get_data(as_text=True)
latest_other = post_json(other_client, '/api/assistant', {'message': 'Track my latest order'})
assert latest_other.status_code == 200 and 'no orders' in latest_other.get_json()['reply'].casefold()
print('PASS: A student cannot retrieve another student’s order or token')

staff_client = app.test_client()
assert login(staff_client, 'staff', 'Staff@123', 'STAFF').status_code == 200
staff_tracking = post_json(staff_client, '/api/assistant', {'message': 'Track my order'})
assert staff_tracking.status_code == 403
print('PASS: Staff and other non-student roles cannot use student tracking')

with app.app_context():
    assert (FoodItem.query.count(), Order.query.count(), Payment.query.count()) == before_counts
print('PASS: Assistant queries do not add, update, or delete food, order, or payment records')
print('\n--- ALL CANTEEN ASSISTANT TESTS PASSED ---')
