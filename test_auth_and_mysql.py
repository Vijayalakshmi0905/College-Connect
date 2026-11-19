"""
Comprehensive Test Suite for College Connect:
- Authentication (Register, Login, Logout)
- Role-based Authorization (Student, Staff, Admin)
- Dashboards (Student, Staff, Admin)
- Admin Management Actions (Add Dish, Toggle Availability, Add User)
- Ordering & Payment Integration
"""

from app import app, db
from models import User, Student, Staff, FoodItem, Order, OrderItem, Payment
from test_support import login, logout, post_form, post_json

client = app.test_client()

print("==================================================")
print("RUNNING AUTHENTICATION & ROLE AUTHORIZATION TESTS")
print("==================================================")

# 1. Verify Models and Seed Data
with app.app_context():
    admin = User.query.filter_by(role='ADMIN').first()
    assert admin is not None, "Admin seed user missing"
    assert admin.check_password('Admin@123'), "Admin password verification failed"

    staff = User.query.filter_by(role='STAFF').first()
    assert staff is not None, "Staff seed user missing"
    assert staff.staff_profile is not None, "Staff profile missing"

    student = User.query.filter_by(role='STUDENT').first()
    assert student is not None, "Student seed user missing"
    assert student.student_profile is not None, "Student profile missing"

    food_count = FoodItem.query.count()
    assert food_count >= 16, f"Expected at least 16 food items, got {food_count}"
    print(f"PASS: Models verified (Users: {User.query.count()}, Food Items: {food_count})")

# 2. Test Student Registration
reg_payload_invalid = {
    "full_name": "Test Student",
    "student_id": "CS2026-999",
    "email": "teststudent@collegeconnect.com",
    "phone": "12345",  # Invalid phone
    "password": "Password123",
    "confirm_password": "Password123"
}
res_reg_bad = post_form(client, '/register', reg_payload_invalid)
assert b"Please enter a valid 10-digit Indian mobile number" in res_reg_bad.data
print("PASS: Rejected invalid phone in student registration")

import random
test_student_id = f"CS2026-{random.randint(1000, 9999)}"
test_email = f"teststudent_{random.randint(1000, 9999)}@collegeconnect.com"

reg_payload_valid = {
    "full_name": "Vikram Seth",
    "student_id": test_student_id,
    "email": test_email,
    "phone": "9876543210",
    "department": "Computer Science",
    "year_of_study": "3rd Year",
    "password": "Password@123",
    "confirm_password": "Password@123"
}
res_reg_good = post_form(client, '/register', reg_payload_valid)
assert res_reg_good.status_code == 200
assert b"Student Portal" in res_reg_good.data or b"Vikram Seth" in res_reg_good.data
print("PASS: Student registered and redirected to Student Dashboard!")

# 3. Test Logout
res_logout = logout(client)
assert b"signed out of College Connect" in res_logout.data
print("PASS: User logged out successfully!")

# 4. Test Student Login & Role Authorization
res_login_student = login(client, test_email, "Password@123", "STUDENT")
assert res_login_student.status_code == 200
assert b"Student Portal" in res_login_student.data or b"Vikram Seth" in res_login_student.data
print("PASS: Student logged in successfully!")

# Student attempting to access Admin Dashboard -> Should be rejected
res_student_admin = client.get('/admin-dashboard', follow_redirects=True)
assert b"Access restricted" in res_student_admin.data or res_student_admin.status_code == 403
print("PASS: Protected Admin Dashboard from unauthorized Student access!")

# Student attempting to access Staff Dashboard -> Should be rejected
res_student_staff = client.get('/staff-dashboard', follow_redirects=True)
assert b"Access restricted" in res_student_staff.data or res_student_staff.status_code == 403
print("PASS: Protected Staff Dashboard from unauthorized Student access!")

logout(client)

# 5. Test Staff Login
res_login_staff = login(client, "staff@collegeconnect.com", "Staff@123", "STAFF")
assert res_login_staff.status_code == 200
assert b"Canteen Staff Kitchen Dashboard" in res_login_staff.data
print("PASS: Staff logged in and accessed Staff Dashboard!")

# Staff attempting to access Admin Dashboard -> Should be rejected
res_staff_admin = client.get('/admin-dashboard', follow_redirects=True)
assert b"Access restricted" in res_staff_admin.data
print("PASS: Protected Admin Dashboard from Staff access!")

logout(client)

# 6. Test Admin Login
res_login_admin = login(client, "admin@collegeconnect.com", "Admin@123", "ADMIN")
assert res_login_admin.status_code == 200
assert b"Canteen Administration Hub" in res_login_admin.data
print("PASS: Admin logged in and accessed Admin Hub!")

# Admin can also access Staff Dashboard
res_admin_staff = client.get('/staff-dashboard', follow_redirects=True)
assert res_admin_staff.status_code == 200
assert b"Canteen Staff Kitchen Dashboard" in res_admin_staff.data
print("PASS: Admin can access Staff Dashboard!")

# 7. Test Admin Feature: Add Food Item
test_dish_name = f"Special Frankie {random.randint(1000, 9999)}"
res_add_dish = post_form(client, '/admin/food-items/add', {
    "name": test_dish_name,
    "category": "Snacks",
    "price": "70",
    "description": "Spicy tandoori paneer rolled in whole wheat paratha with mint sauce",
    "image": "https://images.unsplash.com/photo-1546833999-b9f581a1996d?w=500",
    "is_veg": "on"
})
assert b"added to canteen catalog successfully" in res_add_dish.data
print("PASS: Admin successfully added new food item to catalog!")

# 8. Test Admin Feature: Toggle Availability
with app.app_context():
    dish = FoodItem.query.filter_by(name=test_dish_name).first()
    assert dish is not None
    dish_id = dish.id

res_toggle = post_form(client, f'/admin/food-items/{dish_id}/toggle')
assert b"marked as Sold Out" in res_toggle.data
print("PASS: Admin toggled food item availability to Sold Out!")

# 9. Test Admin Feature: Add New Staff User
test_staff_user = f"chef_{random.randint(1000, 9999)}"
test_staff_mail = f"{test_staff_user}@collegeconnect.com"
res_add_staff = post_form(client, '/admin/users/add', {
    "username": test_staff_user,
    "full_name": "Suresh Patel",
    "email": test_staff_mail,
    "role": "STAFF",
    "phone": "9876543212",
    "staff_id": f"STF-{random.randint(100, 999)}",
    "password": "StaffPassword@123"
})
assert b"created successfully" in res_add_staff.data
print("PASS: Admin created new staff account successfully!")

# 10. Test Order Creation and Payment Linking
order_payload = {
    "student_name": "Vikram Seth",
    "student_id": "CS2026-777",
    "phone": "+91 9876543210",
    "pickup_slot": "12:30 PM - Lunch Slot 1",
    "payment_method": "Pay at Canteen Counter / UPI",
    "items": [
        {"id": 1, "name": "Masala Dosa", "price": 60, "quantity": 1}
    ]
}

logout(client)
login(client, test_email, "Password@123", "STUDENT")
res_order = post_json(client, '/api/orders', order_payload)
assert res_order.status_code == 201
order_data = res_order.get_json()["order"]
new_order_id = order_data["order_id"]
assert order_data["payment"] is not None
assert order_data["payment"]["payment_status"] == "PENDING"
print(f"PASS: Order #{new_order_id} created with linked Payment record (Status: PENDING)!")

# 11. Test Order Completion updates Payment to COMPLETED
staff_client = app.test_client()
login(staff_client, "staff@collegeconnect.com", "Staff@123", "STAFF")
res_update_status = post_json(staff_client, f'/api/staff/orders/{new_order_id}/status', {"status": "COMPLETED"})
assert res_update_status.status_code == 200
completed_order = res_update_status.get_json()["order"]
assert completed_order["status"] == "COMPLETED"
assert completed_order["payment"]["payment_status"] == "COMPLETED"
assert completed_order["payment"]["paid_at"] is not None
print("PASS: Order status transition to COMPLETED automatically marked Payment as COMPLETED!")

# 12. Test Health Check Endpoint
res_health = client.get('/health')
assert res_health.status_code == 200
health_data = res_health.get_json()
assert health_data["status"] == "healthy"
assert "database_engine" in health_data
print(f"PASS: Health check responded 200 OK (Engine: {health_data['database_engine']})")

print("\n==================================================")
print("ALL AUTHENTICATION, ROLE, & ADMIN TESTS PASSED!!!")
print("==================================================")
