"""Create any missing CollegeConnect tables in the configured production MySQL DB.

Run this explicitly from the project directory after setting the Railway
production environment variables. This script creates tables only; it does not
migrate existing schemas, seed menu data, or modify existing database rows.
"""

from db_config import is_production
from app import app
from models import db, User, Student, Staff, FoodItem, Order, OrderItem, Payment

# Keep explicit model imports above: importing each model registers its table
# with the shared SQLAlchemy metadata used by db.create_all().
_REGISTERED_MODELS = (User, Student, Staff, FoodItem, Order, OrderItem, Payment)


def main():
    if not is_production() or app.config.get('APP_ENV') != 'production':
        raise RuntimeError('Refusing to initialize tables outside production mode.')

    database_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if not database_uri.startswith('mysql+pymysql://'):
        raise RuntimeError('Refusing to initialize tables: configured database is not MySQL.')

    with app.app_context():
        db.create_all()
        table_names = sorted(db.metadata.tables.keys())

    print('Database table initialization completed successfully.')
    print('Tables: ' + ', '.join(table_names))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        # Avoid printing connection details or credentials from driver errors.
        raise SystemExit(
            'Database initialization failed. Check Railway production settings '
            'and database connectivity.'
        ) from None
