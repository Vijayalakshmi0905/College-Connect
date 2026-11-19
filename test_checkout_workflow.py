"""
Integration and Unit Tests for College Connect Checkout Workflow
Tests:
1. Validation of mobile numbers, student details, and cart items
2. Order submission and calculation
3. Unique token and order ID generation
4. Order confirmation page rendering and token visibility
"""

from app import app
from models import FoodItem
from test_support import login, post_json

client = app.test_client()
assert login(client, 'student@collegeconnect.com', 'Student@123', 'STUDENT').status_code == 200

with app.app_context():
    dosa = FoodItem.query.filter_by(name='Masala Dosa').first()
    chai = FoodItem.query.filter_by(name='Kulhad Masala Chai').first()
    thali = FoodItem.query.filter_by(name='Paneer Butter Masala Thali').first()
    assert dosa and chai and thali

print("--- STARTING CHECKOUT WORKFLOW TESTS ---")

# 1. Test Invalid Mobile Numbers
invalid_phones = [
    "12345",              # Too short
    "abcdefghij",         # Letters
    "5987654321",         # Starts with 5 (invalid in India)
    "98765432101",        # 11 digits
    "0000000000",         # All zeros
    ""                    # Empty
]

base_payload = {
    "student_name": "Rohan Verma",
    "student_id": "CS-2026-101",
    "pickup_slot": "Immediate (15-20 Mins)",
    "payment_method": "Pay at Canteen Counter / UPI",
    "items": [
        {"id": dosa.id, "name": dosa.name, "price": dosa.price, "quantity": 1}
    ]
}

for bad_phone in invalid_phones:
    payload = dict(base_payload)
    payload["phone"] = bad_phone
    res = post_json(client, '/api/orders', payload)
    assert res.status_code == 400, f"Expected 400 for phone '{bad_phone}', got {res.status_code}"
    json_data = res.get_json()
    assert json_data["success"] is False
    assert "Indian mobile number" in json_data["error"]
    print(f"PASS: Rejected invalid phone '{bad_phone}': {json_data['error']}")

# 2. Test Invalid Name, Student ID, and Empty Cart
res_bad_name = post_json(client, '/api/orders', {**base_payload, "student_name": "A", "phone": "9876543210"})
assert res_bad_name.status_code == 400
print(f"PASS: Rejected short name: {res_bad_name.get_json()['error']}")

res_bad_id = post_json(client, '/api/orders', {**base_payload, "student_id": "1", "phone": "9876543210"})
assert res_bad_id.status_code == 400
print(f"PASS: Rejected short student ID: {res_bad_id.get_json()['error']}")

res_empty_cart = post_json(client, '/api/orders', {**base_payload, "phone": "9876543210", "items": []})
assert res_empty_cart.status_code == 400
print(f"PASS: Rejected empty items: {res_empty_cart.get_json()['error']}")

# 3. Test Successful Order Submission #1
valid_payload_1 = {
    "student_name": "Aarav Sharma",
    "student_id": "CS2026-084",
    "phone": "+91 9876543210",
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

# 4. Test Successful Order Submission #2 and Token Uniqueness
valid_payload_2 = {
    "student_name": "Priya Nair",
    "student_id": "EC2025-042",
    "phone": "9123456780", # Valid 10-digit without prefix
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

# 5. Test Confirmation Page Rendering with Order #1
res_confirm = client.get(f"/order-confirmation?order_id={order1['order_id']}")
assert res_confirm.status_code == 200
html_confirm = res_confirm.data.decode('utf-8')

# Verify Order Confirmation Requirements:
assert order1['order_id'] in html_confirm, "Order ID missing from confirmation page"
assert order1['token_number'] in html_confirm, "Pickup token missing from confirmation page"
assert "CONFIRMED" in html_confirm, "Order status CONFIRMED missing from confirmation page"
assert "Aarav Sharma" in html_confirm, "Student name missing from confirmation page"
assert dosa.name in html_confirm, "Ordered item missing from confirmation page"
assert chai.name in html_confirm, "Ordered item missing from confirmation page"
assert str(int(order1['total_amount'])) in html_confirm, "Total amount missing from confirmation page"
print("\nPASS: Order Confirmation Page contains all required details (Order ID, Token, Status, Items, Student Info, Total)!")

# 6. Test Checkout Page Loads Successfully
res_checkout = client.get('/checkout')
assert res_checkout.status_code == 200
html_checkout = res_checkout.data.decode('utf-8')
assert 'studentName' in html_checkout
assert 'studentPhone' in html_checkout
assert 'pickupSlot' in html_checkout
assert 'Confirm & Generate Pickup Token' in html_checkout
print("PASS: Checkout page renders correctly!")

print("\n==========================================")
print("ALL CHECKOUT & CONFIRMATION TESTS PASSED!!")
print("==========================================")
