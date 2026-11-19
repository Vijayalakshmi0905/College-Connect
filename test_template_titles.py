"""Ensure every rendered application page has the fixed browser title."""
import os

os.environ['APP_ENV'] = 'test'
os.environ['TEST_DATABASE_URL'] = 'sqlite:///:memory:'
os.environ.pop('DATABASE_URL', None)
os.environ.pop('MYSQL_URL', None)

from app import app
from test_support import login

EXPECTED_TITLE = '<title>College Connect - Canteen Ordering System</title>'
client = app.test_client()

def assert_title(response, path):
    assert response.status_code == 200, f'{path}: HTTP {response.status_code}'
    html = response.get_data(as_text=True)
    assert html.count('<title>') == 1, f'{path}: expected exactly one title element'
    assert EXPECTED_TITLE in html, f'{path}: expected fixed title was not rendered'
    assert '{% block title %}' not in html, f'{path}: Jinja title syntax leaked into response'


for path in ('/', '/menu', '/login', '/register'):
    assert_title(client.get(path), path)

student = app.test_client()
assert login(student, 'student', 'Student@123', 'STUDENT').status_code == 200
for path in ('/cart', '/checkout', '/student-dashboard', '/order-confirmation'):
    assert_title(student.get(path), path)

staff = app.test_client()
assert login(staff, 'staff', 'Staff@123', 'STAFF').status_code == 200
assert_title(staff.get('/staff-dashboard'), '/staff-dashboard')

admin = app.test_client()
assert login(admin, 'admin', 'Admin@123', 'ADMIN').status_code == 200
assert_title(admin.get('/admin-dashboard'), '/admin-dashboard')

print('PASS: All public, student, staff, and admin pages render the exact College Connect browser title')
