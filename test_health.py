from unittest.mock import patch

from app import app, db
from models import FoodItem

client = app.test_client()

# 1. Test /health JSON endpoint
res_health = client.get('/health')
assert res_health.status_code == 200, f"Status code: {res_health.status_code}"
data = res_health.get_json()
assert data['status'] == 'healthy', f"Status: {data.get('status')}"
assert data['service'] == 'College Connect', f"Service: {data.get('service')}"
assert data['version'] in ['1.0.0', '2.0.0'], f"Version: {data.get('version')}"
print("Health API JSON Response:", data)

# Health must reflect a database failure instead of always returning healthy.
with patch('app.db.session.execute', side_effect=RuntimeError('simulated database outage')):
    failed_health = client.get('/health')
    assert failed_health.status_code == 503
    assert failed_health.get_json()['status'] == 'unhealthy'
print("Database outage health reporting: PASS")

# 2. Test homepage renders modal trigger and modal markup
res_home = client.get('/')
assert res_home.status_code == 200
html = res_home.data.decode('utf-8')
assert 'data-bs-target="#healthModal"' in html, "Modal trigger missing"
assert 'id="healthModal"' in html, "healthModal missing"
assert 'id="healthStatusContent"' in html, "healthStatusContent missing"
assert 'System Health Monitor' in html, "Health modal title missing"
assert 'Popular Canteen Items' in html, "Database-backed menu section missing"
assert 'Browse Menu' in html and 'href="/menu"' in html, "Prominent menu navigation missing"
assert 'cmr-campus.png' in html, "Supplied campus hero image missing"
assert 'Flask Application Initialized' not in html and 'Initial Scaffold Ready' not in html
assert 'Popular Canteen Items' in html and 'availability-label' in html
assert 'footer-brand' in html and 'Campus food, on your time.' in html
assert 'name="viewport" content="width=device-width, initial-scale=1.0"' in html
assert 'navbar-expand-lg' in html and 'data-bs-target="#navContent"' in html
assert 'href="/login"' in html and 'href="/register"' in html
with app.app_context():
    catalogue_names = [item.name for item in FoodItem.query.all()]
assert not catalogue_names or any(name in html for name in catalogue_names), "Homepage food cards do not show database catalogue items"
if catalogue_names:
    assert 'food-kind-badge veg' in html or 'food-kind-badge non-veg' in html, "Food type indicator missing from homepage cards"
print("Homepage Modal & Trigger Verification: PASS")

campus_photo = client.get('/static/images/cmr-campus.png')
assert campus_photo.status_code == 200 and campus_photo.mimetype == 'image/png'
print("Supplied campus image route: PASS")

with open('templates/order_confirmation.html', encoding='utf-8') as tracking_template:
    tracking_html = tracking_template.read()
for label in ('Placed', 'Confirmed', 'Preparing', 'Ready for Pickup'):
    assert label in tracking_html, f"Order progress label missing: {label}"
assert 'printableOrderTicket' in tracking_html
print("Order tracking labels and print ticket markup: PASS")

menu_html = client.get('/menu').data.decode('utf-8')
assert 'row-cols-1 row-cols-sm-2 row-cols-md-3 row-cols-lg-4' in menu_html
assert 'd-md-none' in menu_html and 'View Cart' in menu_html
print("Responsive menu and mobile cart navigation markup: PASS")

# 3. Test static assets
res_js = client.get('/static/js/main.js')
assert res_js.status_code == 200
js_text = res_js.data.decode('utf-8')
assert 'fetchHealthStatus' in js_text, "fetchHealthStatus missing in main.js"
assert "fetch('/health'" in js_text, "fetch('/health') missing in main.js"
assert 'Backend Status: Healthy' in js_text, "Backend Status: Healthy missing"
assert 'Backend Status: Unavailable' in js_text, "Backend Status: Unavailable missing"
print("Static main.js Verification: PASS")

res_css = client.get('/static/css/style.css')
assert res_css.status_code == 200
css_text = res_css.data.decode('utf-8')
assert '.status-indicator-dot.healthy' in css_text, "Healthy CSS indicator missing"
assert '.status-indicator-dot.unavailable' in css_text, "Unavailable CSS indicator missing"
assert '@media (min-width: 768px)' in css_text
assert '.navbar,\n    footer,\n    .canteen-assistant,' in css_text, "Chat assistant must stay out of printed pickup receipts"
print("Static style.css Verification: PASS")

print("\n--- ALL HEALTH CHECK INTEGRATION TESTS PASSED ---")
