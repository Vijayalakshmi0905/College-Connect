"""Create missing tables and insert missing catalog entries in production MySQL.

Run explicitly after setting the Railway production environment variables.
This script does not migrate existing schemas or modify existing catalog,
order, user, or payment rows; it only adds absent tables and menu entries.
"""

from db_config import is_production
from app import app
from food_data import FOOD_ITEMS
from models import db, User, Student, Staff, FoodItem, Order, OrderItem, Payment

# Keep explicit model imports above: importing each model registers its table
# with the shared SQLAlchemy metadata used by db.create_all().
_REGISTERED_MODELS = (User, Student, Staff, FoodItem, Order, OrderItem, Payment)


def seed_missing_food_items():
    """Insert catalog entries that are absent, preserving every existing row."""
    existing_names = {
        name.strip().casefold()
        for (name,) in db.session.query(FoodItem.name).all()
        if isinstance(name, str)
    }
    added_count = 0

    for item in FOOD_ITEMS:
        normalized_name = item['name'].strip().casefold()
        if normalized_name in existing_names:
            continue

        db.session.add(FoodItem(
            name=item['name'],
            category=item['category'],
            price=float(item['price']),
            description=item['description'],
            image=item['image'],
            available=item.get('available', True),
            is_veg=item.get('is_veg', True)
        ))
        existing_names.add(normalized_name)
        added_count += 1

    db.session.commit()
    return added_count


def main():
    if not is_production() or app.config.get('APP_ENV') != 'production':
        raise RuntimeError('Refusing to initialize tables outside production mode.')

    database_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if not database_uri.startswith('mysql+pymysql://'):
        raise RuntimeError('Refusing to initialize tables: configured database is not MySQL.')

    with app.app_context():
        db.create_all()
        added_food_count = seed_missing_food_items()
        table_names = sorted(db.metadata.tables.keys())

    print('Database table initialization completed successfully.')
    print('Tables: ' + ', '.join(table_names))
    print(f'Added {added_food_count} missing menu items; existing menu rows were preserved.')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        # Avoid printing connection details or credentials from driver errors.
        raise SystemExit(
            'Database initialization failed. Check Railway production settings '
            'and database connectivity.'
        ) from None
