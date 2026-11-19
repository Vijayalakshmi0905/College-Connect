from unittest.mock import patch

from app import app, db

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
assert 'Check Health Status' in html, "Button text missing"
assert 'name="viewport" content="width=device-width, initial-scale=1.0"' in html
assert 'navbar-expand-lg' in html and 'data-bs-target="#navContent"' in html
assert 'href="/login"' in html and 'href="/register"' in html
print("Homepage Modal & Trigger Verification: PASS")

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
print("Static style.css Verification: PASS")

print("\n--- ALL HEALTH CHECK INTEGRATION TESTS PASSED ---")
