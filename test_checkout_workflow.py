"""Student registration, login, and authenticated-profile checkout workflow."""

import re

from app import app
from models import FoodItem, Order, Student, User
from test_support import login, logout, post_form, post_json

client = app.test_client()
registration = post_form(client, '/register', {
    'full_name': 'Checkout Test Student',
    'student_id': 'FLOW-2026-900',
    'email': 'checkout-flow-900@collegeconnect.com',
    'phone': '9876543210',
    'department': 'Computer Science',
    'year_of_study': '3rd Year',
    'password': 'Checkout@123',
    'confirm_password': 'Checkout@123'
})
assert registration.status_code == 200
assert b'Checkout Test Student' in registration.data
assert logout(client).status_code == 200
assert login(client, 'checkout-flow-900@collegeconnect.com', 'Checkout@123', 'STUDENT').status_code == 200
print('PASS: Student registration and login completed before checkout')

with app.app_context():
    dosa = FoodItem.query.filter_by(name='Masala Dosa').first()
    chai = FoodItem.query.filter_by(name='Kulhad Masala Chai').first()
    thali = FoodItem.query.filter_by(name='Paneer Butter Masala Thali').first()
    assert dosa and chai and thali

menu_response = client.get('/menu')
assert menu_response.status_code == 200
menu_item_match = re.search(rb'data-id="(\d+)"\s+data-name="Masala Dosa"', menu_response.data)
assert menu_item_match, 'Masala Dosa was not available to add from the menu.'
menu_dosa_id = int(menu_item_match.group(1))
assert menu_dosa_id == dosa.id
print('PASS: Cart item ID matches the food menu database ID')

print("--- STARTING CHECKOUT WORKFLOW TESTS ---")

base_payload = {
    "pickup_slot": "Immediate (15-20 Mins)",
    "payment_method": "Pay at Canteen Counter / UPI",
    "items": [
        {"id": dosa.id, "name": dosa.name, "price": dosa.price, "quantity": 1}
    ]
}

# Student identity is not required in the order request; it comes from the login session.
res_empty_cart = post_json(client, '/api/orders', {**base_payload, "items": []})
assert res_empty_cart.status_code == 400
print(f"PASS: Rejected empty items: {res_empty_cart.get_json()['error']}")

# 2. Test successful checkout without personal fields in the request
valid_payload_1 = {
    # These untrusted client values must never replace the authenticated profile.
    "student_name": "Different Person",
    "student_id": "UNRELATED-999",
    "phone": "0000000000",
    "pickup_slot": "Immediate (15-20 Mins)",
    "payment_method": "Pay at Canteen Counter / UPI",
    "items": [
        {"id": dosa.id, "name": dosa.name, "price": dosa.price, "quantity": 2},
        {"id": chai.id, "name": chai.name, "price": chai.price, "quantity": 1}
    ]
}

res1 = post_json(client, '/api/orders', valid_payload_1)
assert res1.status_code == 201, f"Expected 201, got {res1.status_code}: {res1.get_json()}"
data1 = res1.get_json()
assert data1["success"] is True
order1 = data1["order"]
print("\n--- ORDER #1 CREATED SUCCESSFULLY ---")
print(f"Order ID: {order1['order_id']}")
print(f"Token Number: {order1['token_number']}")
print(f"Status: {order1['status']}")
print(f"Total Amount: ₹{order1['total_amount']}")

assert order1["order_id"].startswith("CC-")
assert order1["token_number"].startswith("T-")
assert order1["status"] == "CONFIRMED"
assert order1["total_amount"] == (float(dosa.price) * 2 + float(chai.price))
assert order1["phone"] == "+91 9876543210"
assert order1["student_name"] == "Checkout Test Student"
assert order1["student_id"] == "FLOW-2026-900"
with app.app_context():
    registered_user = User.query.filter_by(email='checkout-flow-900@collegeconnect.com').one()
    registered_student = Student.query.filter_by(user_id=registered_user.id).one()
    saved_order = Order.query.filter_by(order_id=order1['order_id']).one()
    assert order1['user_id'] == registered_user.id
    assert saved_order.student_profile_id == registered_student.id
print("PASS: Order identity was taken from the authenticated student profile")
print("PASS: Order is linked to the logged-in user and student profile")

# 3. Test Successful Order Submission #2 and Token Uniqueness
valid_payload_2 = {
    "pickup_slot": "12:30 PM - Lunch Slot 1",
    "payment_method": "Pay at Canteen Counter / UPI",
    "items": [
        {"id": thali.id, "name": thali.name, "price": thali.price, "quantity": 1}
    ]
}

res2 = post_json(client, '/api/orders', valid_payload_2)
assert res2.status_code == 201
data2 = res2.get_json()
order2 = data2["order"]
print("\n--- ORDER #2 CREATED SUCCESSFULLY ---")
print(f"Order ID: {order2['order_id']}")
print(f"Token Number: {order2['token_number']}")
print(f"Status: {order2['status']}")

# Ensure uniqueness
assert order1["order_id"] != order2["order_id"], "Order IDs must be unique!"
assert order1["token_number"] != order2["token_number"], "Tokens must be unique among active orders!"
print("PASS: Order IDs and Tokens are guaranteed unique!")

# 4. Test Confirmation Page Rendering with Order #1
res_confirm = client.get(f"/order-confirmation?order_id={order1['order_id']}")
assert res_confirm.status_code == 200
html_confirm = res_confirm.data.decode('utf-8')

# Verify Order Confirmation Requirements:
assert order1['order_id'] in html_confirm, "Order ID missing from confirmation page"
assert order1['token_number'] in html_confirm, "Pickup token missing from confirmation page"
assert "CONFIRMED" in html_confirm, "Order status CONFIRMED missing from confirmation page"
assert "Checkout Test Student" in html_confirm, "Student name missing from confirmation page"
assert dosa.name in html_confirm, "Ordered item missing from confirmation page"
assert chai.name in html_confirm, "Ordered item missing from confirmation page"
assert str(int(order1['total_amount'])) in html_confirm, "Total amount missing from confirmation page"
print("\nPASS: Order Confirmation Page contains all required details (Order ID, Token, Status, Items, Student Info, Total)!")

# 5. Test Checkout Page Loads with saved profile details and no editable identity/password fields
res_checkout = client.get('/checkout')
assert res_checkout.status_code == 200
html_checkout = res_checkout.data.decode('utf-8')
assert 'Checkout Test Student' in html_checkout
assert 'FLOW-2026-900' in html_checkout
assert 'checkout-flow-900@collegeconnect.com' in html_checkout
assert '+91 9876543210' in html_checkout
assert 'studentName' not in html_checkout
assert 'studentPhone' not in html_checkout
assert 'type="password"' not in html_checkout
assert 'pickupSlot' in html_checkout
assert 'Confirm & Generate Pickup Token' in html_checkout
print("PASS: Checkout page renders correctly!")

print("\n==========================================")
print("ALL CHECKOUT & CONFIRMATION TESTS PASSED!!")
print("==========================================")
