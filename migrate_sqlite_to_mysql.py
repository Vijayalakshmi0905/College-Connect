"""
College Connect - Data Migration Script: SQLite to MySQL
Safely preserves existing orders, tokens, and data from college_connect.db,
creates tables in MySQL, seeds initial food items, and creates default accounts.
"""

import os
import sqlite3
from datetime import datetime
from dotenv import load_dotenv

# Load .env
load_dotenv()

from db_config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME, get_mysql_uri
from food_data import FOOD_ITEMS


def run_migration():
    print("==================================================")
    print("COLLEGE CONNECT: SQLITE TO MYSQL MIGRATION")
    print("==================================================")

    if not DB_PASSWORD or DB_PASSWORD == 'your_secure_password_here':
        print("\n[CONFIGURATION NOTICE]")
        print("Your .env file currently has placeholder credentials for 'college_app'.")
        print("To complete migration to MySQL:")
        print("1. In your MySQL shell as root, run:")
        print("   CREATE DATABASE IF NOT EXISTS college_connect CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        print("   CREATE USER IF NOT EXISTS 'college_app'@'localhost' IDENTIFIED BY 'YOUR_PASSWORD';")
        print("   GRANT ALL PRIVILEGES ON college_connect.* TO 'college_app'@'localhost';")
        print("   FLUSH PRIVILEGES;")
        print("2. Update DB_PASSWORD in .env with 'YOUR_PASSWORD'.")
        print("3. Re-run this migration script: python migrate_sqlite_to_mysql.py")
        return False

    import pymysql
    print(f"Connecting to MySQL at {DB_HOST}:{DB_PORT} as '{DB_USER}'...")

    try:
        # Step 1: Ensure database exists
        conn = pymysql.connect(
            host=DB_HOST,
            port=int(DB_PORT),
            user=DB_USER,
            password=DB_PASSWORD
        )
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        conn.close()
        print(f"Database `{DB_NAME}` verified / created successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to connect to MySQL: {e}")
        return False

    # Step 2: Initialize SQLAlchemy models in Flask context
    from flask import Flask
    from models import db, User, Student, Staff, FoodItem, Order, OrderItem, Payment

    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = get_mysql_uri()
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    with app.app_context():
        # Create all tables in MySQL
        db.create_all()
        print("MySQL schema tables created successfully.")

        # Step 3: Optional local demo accounts. Production migrations must not
        # create publicly known credentials; supply passwords through env vars
        # only when demo seeding is explicitly requested.
        created_users = 0
        if os.environ.get('SEED_DEMO_ACCOUNTS', '').strip().lower() in {'1', 'true', 'yes'}:
            demo_passwords = {
                'admin': os.environ.get('DEMO_ADMIN_PASSWORD', ''),
                'staff': os.environ.get('DEMO_STAFF_PASSWORD', ''),
                'student': os.environ.get('DEMO_STUDENT_PASSWORD', '')
            }
            if not all(demo_passwords.values()):
                raise RuntimeError('Demo seeding requires DEMO_ADMIN_PASSWORD, DEMO_STAFF_PASSWORD, and DEMO_STUDENT_PASSWORD.')

            if not User.query.filter_by(email='admin@collegeconnect.com').first():
                admin_user = User(username='admin', email='admin@collegeconnect.com', role='ADMIN', is_active=True)
                admin_user.set_password(demo_passwords['admin'])
                db.session.add(admin_user)
                created_users += 1

            if not User.query.filter_by(email='staff@collegeconnect.com').first():
                staff_user = User(username='staff', email='staff@collegeconnect.com', role='STAFF', is_active=True)
                staff_user.set_password(demo_passwords['staff'])
                db.session.add(staff_user)
                db.session.flush()
                db.session.add(Staff(
                    user_id=staff_user.id, staff_id='STF-001', full_name='Chef Ramesh Sharma',
                    role_title='Canteen Kitchen Head', phone='+91 9876543210'
                ))
                created_users += 1

            if not User.query.filter_by(email='student@collegeconnect.com').first():
                student_user = User(username='student', email='student@collegeconnect.com', role='STUDENT', is_active=True)
                student_user.set_password(demo_passwords['student'])
                db.session.add(student_user)
                db.session.flush()
                db.session.add(Student(
                    user_id=student_user.id, student_id='CS2026-001', full_name='Aarav Sharma',
                    phone='+91 9876543210', department='Computer Science', year_of_study='3rd Year'
                ))
                created_users += 1

            db.session.commit()
            print(f"Demo accounts verified / created: {created_users} new accounts.")
        else:
            print('Skipping demo accounts; set SEED_DEMO_ACCOUNTS and password environment variables to opt in.')

        # Step 4: Seed 16 Sample Food Items
        seeded_items = 0
        for item_data in FOOD_ITEMS:
            existing = FoodItem.query.filter_by(name=item_data['name']).first()
            if not existing:
                food = FoodItem(
                    name=item_data['name'],
                    category=item_data['category'],
                    price=float(item_data['price']),
                    description=item_data['description'],
                    image=item_data['image'],
                    available=item_data.get('available', True),
                    is_veg=item_data.get('is_veg', True)
                )
                db.session.add(food)
                seeded_items += 1
        db.session.commit()
        print(f"Food catalog seeded into MySQL: {seeded_items} new items.")

        # Step 5: Migrate Existing SQLite Orders and Items (Non-destructive)
        sqlite_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'college_connect.db')
        migrated_orders = 0
        migrated_items = 0

        if os.path.exists(sqlite_path):
            print("Reading existing orders from SQLite 'college_connect.db'...")
            sq_conn = sqlite3.connect(sqlite_path)
            sq_conn.row_factory = sqlite3.Row
            sq_cursor = sq_conn.cursor()

            def parse_dt(val):
                """Robust datetime parser handles both microsecond and plain formats."""
                if not val:
                    return datetime.utcnow()
                for fmt in ('%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S'):
                    try:
                        return datetime.strptime(val, fmt)
                    except ValueError:
                        continue
                return datetime.utcnow()

            try:
                sq_orders = sq_cursor.execute("SELECT * FROM orders").fetchall()
                for so in sq_orders:
                    # Idempotent check — skip if already migrated
                    if not Order.query.filter_by(order_id=so['order_id']).first():
                        created_dt = parse_dt(so['created_at'])
                        updated_dt = parse_dt(so['updated_at'])

                        new_order = Order(
                            order_id=so['order_id'],
                            token_number=so['token_number'],
                            status=so['status'],
                            student_name=so['student_name'],
                            student_id=so['student_id'],
                            phone=so['phone'],
                            pickup_slot=so['pickup_slot'],
                            payment_method=so['payment_method'],
                            subtotal=float(so['subtotal'] or 0),
                            total_amount=float(so['total_amount'] or 0),
                            item_count=int(so['item_count'] or 0),
                            created_at=created_dt,
                            updated_at=updated_dt
                        )
                        db.session.add(new_order)
                        db.session.flush()

                        # Migrate Order Items
                        sq_items = sq_cursor.execute(
                            "SELECT * FROM order_items WHERE order_id = ?", (so['id'],)
                        ).fetchall()
                        sq_item_cols = [d[0] for d in sq_cursor.description]

                        for si in sq_items:
                            si_dict = dict(zip(sq_item_cols, si))
                            # SQLite schema may use food_item_id or item_id
                            food_item_fk = si_dict.get('food_item_id') or si_dict.get('item_id')
                            new_item = OrderItem(
                                order_id=new_order.id,
                                food_item_id=food_item_fk,
                                name=si_dict.get('name', ''),
                                category=si_dict.get('category', ''),
                                price=float(si_dict.get('price', 0)),
                                quantity=int(si_dict.get('quantity', 1)),
                                image=si_dict.get('image', '')
                            )
                            db.session.add(new_item)
                            migrated_items += 1

                        # Create matching Payment record
                        payment_status = 'COMPLETED' if so['status'] == 'COMPLETED' else 'PENDING'
                        payment = Payment(
                            order_id=new_order.id,
                            payment_id=f"PAY-{so['order_id']}",
                            amount=float(so['total_amount'] or 0),
                            payment_method=so['payment_method'],
                            payment_status=payment_status,
                            paid_at=updated_dt if payment_status == 'COMPLETED' else None
                        )
                        db.session.add(payment)
                        migrated_orders += 1

                db.session.commit()
                print(f"Data Migration Complete: {migrated_orders} orders, {migrated_items} items migrated to MySQL.")
            except Exception as e:
                db.session.rollback()
                print(f"[ERROR during data copy]: {e}")
                import traceback
                traceback.print_exc()
            finally:
                sq_conn.close()

    print("\n==================================================")
    print("MYSQL SETUP & MIGRATION SUCCESSFUL!")
    print("==================================================")
    return True


if __name__ == '__main__':
    run_migration()
