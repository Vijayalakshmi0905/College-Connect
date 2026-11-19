"""Explicit, idempotent bootstrap for a new Railway MySQL database.

This command creates missing application tables, adds missing sample menu
items, and creates the first administrator only when none exists. It never
drops tables, overwrites existing menu rows, creates a database/user, or reads
the local SQLite database. It is intentionally not called by app startup.

Run only after setting APP_ENV=production, RUN_INITIAL_BOOTSTRAP=true,
DATABASE_URL (or MYSQL_URL), BOOTSTRAP_ADMIN_USERNAME,
BOOTSTRAP_ADMIN_EMAIL, and BOOTSTRAP_ADMIN_PASSWORD in the target service.
Remove the one-time bootstrap variables after a successful run.
"""

import os
import sys


def main():
    if os.environ.get('APP_ENV', '').strip().lower() != 'production':
        raise RuntimeError('Bootstrap requires APP_ENV=production.')
    if os.environ.get('RUN_INITIAL_BOOTSTRAP', '').strip().lower() != 'true':
        raise RuntimeError('Set RUN_INITIAL_BOOTSTRAP=true to explicitly allow bootstrap writes.')
    if not (os.environ.get('DATABASE_URL', '').strip() or os.environ.get('MYSQL_URL', '').strip()):
        raise RuntimeError('Set DATABASE_URL or MYSQL_URL to the target Railway MySQL service.')

    admin_username = os.environ.get('BOOTSTRAP_ADMIN_USERNAME', '').strip()
    admin_email = os.environ.get('BOOTSTRAP_ADMIN_EMAIL', '').strip().lower()
    admin_password = os.environ.get('BOOTSTRAP_ADMIN_PASSWORD', '')
    if not admin_username or not admin_email or len(admin_password) < 12:
        raise RuntimeError(
            'Provide BOOTSTRAP_ADMIN_USERNAME, BOOTSTRAP_ADMIN_EMAIL, and '
            'a BOOTSTRAP_ADMIN_PASSWORD of at least 12 characters.'
        )

    from flask import Flask
    from db_config import get_active_database_uri
    from food_data import FOOD_ITEMS
    from models import db, FoodItem, User

    database_uri, engine_info = get_active_database_uri()
    if not database_uri.startswith('mysql+pymysql://'):
        raise RuntimeError('Bootstrap only supports the configured Railway MySQL database.')

    bootstrap_app = Flask(__name__)
    bootstrap_app.config['SQLALCHEMY_DATABASE_URI'] = database_uri
    bootstrap_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(bootstrap_app)

    with bootstrap_app.app_context():
        db.create_all()
        added_food_items = 0
        try:
            if not User.query.filter_by(role='ADMIN').first():
                collision = User.query.filter(
                    (User.username == admin_username) | (User.email == admin_email)
                ).first()
                if collision:
                    raise RuntimeError('Bootstrap administrator username or email is already in use.')
                administrator = User(
                    username=admin_username,
                    email=admin_email,
                    role='ADMIN',
                    is_active=True
                )
                administrator.set_password(admin_password)
                db.session.add(administrator)

            for item in FOOD_ITEMS:
                if not FoodItem.query.filter_by(name=item['name']).first():
                    db.session.add(FoodItem(
                        name=item['name'],
                        category=item['category'],
                        price=float(item['price']),
                        description=item['description'],
                        image=item['image'],
                        available=item.get('available', True),
                        is_veg=item.get('is_veg', True)
                    ))
                    added_food_items += 1

            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

    print(f'Bootstrap completed for {engine_info}; added {added_food_items} missing menu items.')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'Bootstrap failed: {error}', file=sys.stderr)
        raise SystemExit(1)
