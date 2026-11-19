"""Test the active test database without ever using local MySQL credentials.

Live MySQL diagnostics are intentionally not part of the automated test suite.
Run this file only with APP_ENV=test and an in-memory SQLite URL.
"""

import os
import sys


if os.environ.get('APP_ENV', '').strip().lower() != 'test':
    print('SKIP: set APP_ENV=test to run the isolated database connectivity check.')
    raise SystemExit(0)

test_database_url = os.environ.get('TEST_DATABASE_URL', '')
if test_database_url != 'sqlite:///:memory:':
    print('FAIL: connectivity regression tests require TEST_DATABASE_URL=sqlite:///:memory:.', file=sys.stderr)
    raise SystemExit(1)

from sqlalchemy import text

from app import app, db, db_engine_info

assert app.config['SQLALCHEMY_DATABASE_URI'] == test_database_url
with app.app_context():
    result = db.session.execute(text('SELECT 1')).scalar_one()
    assert result == 1

print(f'PASS: isolated database query succeeded ({db_engine_info}).')
