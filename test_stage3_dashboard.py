"""
Comprehensive Test Suite for Stage 3: Canteen Staff Dashboard & SQLite Persistence
"""

import os
from app import app, db, Order, OrderItem
from models import FoodItem
from test_support import login, logout, post_json

client = app.test_client()
assert login(client, 'student@collegeconnect.com', 'Student@123', 'STUDENT').status_code == 200

print("==================================================")
print("RUNNING STAGE 3 CANTEEN STAFF DASHBOARD TEST SUITE")
print("==================================================")

# 1. Test Public Flask HTML Routes
routes = [
    ('/', 200, b'College Connect'),
    ('/menu', 200, b'Canteen Menu'),
    ('/cart', 200, b'Your Order Tray'),
    ('/checkout', 200, b'Student Checkout'),
    ('/health', 200, b'healthy')
]

for url, expected_code, expected_content in routes:
    res = client.get(url)
    assert res.status_code == expected_code, f"Route {url} failed: expected {expected_code}, got {res.status_code}"
    assert expected_content in res.data, f"Route {url} content missing: {expected_content}"
    print(f"PASS: HTML Route '{url}' -> Status {res.status_code}")

# Verify Staff Dashboard and staff APIs require authentication.
anonymous_client = app.test_client()
res_unauth = anonymous_client.get('/staff-dashboard')
assert res_unauth.status_code == 302, "Protected route must redirect unauthenticated users"
assert anonymous_client.get('/api/staff/orders').status_code == 401
staff_client = app.test_client()
login(staff_client, 'staff', 'Staff@123', 'STAFF')
res_staff = staff_client.get('/staff-dashboard')
assert res_staff.status_code == 200
assert b'Canteen Staff Kitchen Dashboard' in res_staff.data
print("PASS: Staff Dashboard protected and accessible after staff authentication!")

# 2. Place a New Student Order via Student Checkout API
with app.app_context():
    menu_item_1 = FoodItem.query.filter_by(name='Paneer Butter Masala Thali').first()
    menu_item_2 = FoodItem.query.filter_by(name='Alphonso Mango Lassi').first()
    assert menu_item_1 and menu_item_2

student_order_payload = {
    "student_name": "Divya Krishnan",
    "student_id": "CS2026-055",
    "phone": "+91 9876543210",
    "pickup_slot": "12:30 PM - Lunch Slot 1",
    "payment_method": "Pay at Canteen Counter / UPI",
    "items": [
        {"id": menu_item_1.id, "name": menu_item_1.name, "category": menu_item_1.category, "price": menu_item_1.price, "quantity": 1},
        {"id": menu_item_2.id, "name": menu_item_2.name, "category": menu_item_2.category, "price": menu_item_2.price, "quantity": 2}
    ]
}

res_order = post_json(client, '/api/orders', student_order_payload)
assert res_order.status_code == 201, f"Order placement failed: {res_order.get_json()}"
order_json = res_order.get_json()
assert order_json["success"] is True
created_order = order_json["order"]

order_id = created_order["order_id"]
token_number = created_order["token_number"]
status = created_order["status"]
total_amount = created_order["total_amount"]

print(f"\nPASS: Order Created Successfully in SQLite:")
print(f"  Order ID: {order_id}")
print(f"  Pickup Token: {token_number}")
print(f"  Initial Status: {status}")
print(f"  Total Amount: ₹{total_amount} (Expected ₹220)")
assert total_amount == float(menu_item_1.price) + float(menu_item_2.price) * 2
assert status == "CONFIRMED"

# 3. Verify Order Persistence directly in SQLite Database
with app.app_context():
    db_order = Order.query.filter_by(order_id=order_id).first()
    assert db_order is not None, "Order was not found in SQLite database!"
    assert db_order.student_name == "Aarav Sharma"
    assert db_order.student_id == "CS2026-001"
    assert db_order.token_number == token_number
    assert len(db_order.items) == 2
    assert db_order.status == "CONFIRMED"
    print("PASS: Verified order and items exist in SQLite database!")

# 4. Test Staff Dashboard Stats API
res_stats = staff_client.get('/api/staff/stats')
assert res_stats.status_code == 200
stats = res_stats.get_json()["stats"]
assert stats["total"] >= 1
assert stats["pending"] >= 1
print(f"PASS: Staff Stats API -> Total: {stats['total']}, Pending: {stats['pending']}, Preparing: {stats['preparing']}, Ready: {stats['ready']}, Completed: {stats['completed']}")

# 5. Test Staff Orders API with Search and Filters
res_staff_orders = staff_client.get('/api/staff/orders')
assert res_staff_orders.status_code == 200
orders_list = res_staff_orders.get_json()["orders"]
found_order = next((o for o in orders_list if o["order_id"] == order_id), None)
assert found_order is not None, f"Order {order_id} not returned in staff orders list!"
assert found_order["token_number"] == token_number
print("PASS: Order is present in Staff Orders queue API!")

student_history = client.get('/student-dashboard')
assert student_history.status_code == 200
assert order_id in student_history.get_data(as_text=True)
assert 'Order History' in student_history.get_data(as_text=True)
assert 'Paneer Butter Masala Thali' in student_history.get_data(as_text=True)
print("PASS: Student dashboard shows the current order in order history!")

# Test Search Filter
res_search = staff_client.get(f'/api/staff/orders?search={order_id}')
assert res_search.status_code == 200
search_results = res_search.get_json()["orders"]
assert any(o["order_id"] == order_id for o in search_results)
print(f"PASS: Search by Order ID '{order_id}' returned matching order!")

# 6. Test Status Transition 1: CONFIRMED -> PREPARING
res_prep = post_json(staff_client, f'/api/staff/orders/{order_id}/status', {"status": "PREPARING"})
assert res_prep.status_code == 200, f"Failed transition to PREPARING: {res_prep.get_json()}"
assert res_prep.get_json()["order"]["status"] == "PREPARING"
print("PASS: Staff updated order status to 'PREPARING'!")

# Verify Student Tracking API reflects PREPARING
res_track_1 = client.get(f'/api/orders/{order_id}')
assert res_track_1.status_code == 200
assert res_track_1.get_json()["order"]["status"] == "PREPARING"
print("PASS: Student tracking API reflects 'PREPARING' in real-time!")

# 7. Test Status Transition 2: PREPARING -> READY FOR PICKUP
res_ready = post_json(staff_client, f'/api/staff/orders/{order_id}/status', {"status": "READY FOR PICKUP"})
assert res_ready.status_code == 200
assert res_ready.get_json()["order"]["status"] == "READY FOR PICKUP"
print("PASS: Staff updated order status to 'READY FOR PICKUP'!")

# Verify Student Tracking API reflects READY FOR PICKUP
res_track_2 = client.get(f'/api/orders/{order_id}')
assert res_track_2.get_json()["order"]["status"] == "READY FOR PICKUP"
print("PASS: Student tracking API reflects 'READY FOR PICKUP' in real-time!")

# 8. Test Status Transition 3: READY FOR PICKUP -> COMPLETED
res_completed = post_json(staff_client, f'/api/staff/orders/{order_id}/status', {"status": "COMPLETED"})
assert res_completed.status_code == 200
assert res_completed.get_json()["order"]["status"] == "COMPLETED"
print("PASS: Staff updated order status to 'COMPLETED'!")

# Verify in SQLite database that status is now COMPLETED
with app.app_context():
    db_order_completed = Order.query.filter_by(order_id=order_id).first()
    assert db_order_completed.status == "COMPLETED"
    print("PASS: SQLite database persisted status 'COMPLETED'!")

# 9. Test Invalid Status Transitions
# Attempting to move a COMPLETED order back to PREPARING should be rejected
res_invalid = post_json(staff_client, f'/api/staff/orders/{order_id}/status', {"status": "PREPARING"})
assert res_invalid.status_code == 400, f"Expected 400 for invalid transition, got {res_invalid.status_code}"
print(f"PASS: Rejected invalid transition on COMPLETED order: {res_invalid.get_json()['error']}")

# Attempting an unrecognized status
res_bogus = post_json(staff_client, f'/api/staff/orders/{order_id}/status', {"status": "FLYING_TO_MARS"})
assert res_bogus.status_code == 400
print(f"PASS: Rejected invalid status name: {res_bogus.get_json()['error']}")

# Attempting to update a non-existent order
res_404 = post_json(staff_client, '/api/staff/orders/CC-999999/status', {"status": "PREPARING"})
assert res_404.status_code == 404
print(f"PASS: Returned 404 for non-existent order ID: {res_404.get_json()['error']}")

# 10. Test Order Confirmation Page renders with updated order details
res_confirm_html = client.get(f'/order-confirmation?order_id={order_id}')
assert res_confirm_html.status_code == 200
html_text = res_confirm_html.data.decode('utf-8')
assert order_id in html_text
assert token_number in html_text
assert "Aarav Sharma" in html_text
assert "Paneer Butter Masala Thali" in html_text
print("PASS: Order confirmation page renders with accurate student and item details!")

print("\n==================================================")
print("ALL STAGE 3 STAFF DASHBOARD & TRACKING TESTS PASSED!")
print("==================================================")
