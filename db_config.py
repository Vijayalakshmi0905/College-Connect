"""
College Connect - Database Configuration
Loads database connection parameters securely from environment variables (.env).
Constructs SQLAlchemy URI using PyMySQL.
"""

import os
import secrets
from dotenv import load_dotenv
from urllib.parse import quote_plus

# Load variables from .env file
load_dotenv()

DB_HOST = os.environ.get('DB_HOST', '127.0.0.1')
DB_PORT = os.environ.get('DB_PORT', '3306')
DB_USER = os.environ.get('DB_USER', 'college_app')
DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
DB_NAME = os.environ.get('DB_NAME', 'college_connect')
APP_ENV = os.environ.get('APP_ENV', 'development').strip().lower()
_railway_environment = any(os.environ.get(key) for key in (
    'RAILWAY_ENVIRONMENT_NAME', 'RAILWAY_ENVIRONMENT'
))
SECRET_KEY = os.environ.get('SECRET_KEY') or (
    '' if APP_ENV == 'production' or _railway_environment else secrets.token_urlsafe(48)
)


def is_production():
    """Recognize explicit production mode and Railway's documented marker."""
    if APP_ENV == 'test':
        return False
    return APP_ENV == 'production' or any(os.environ.get(key) for key in (
        'RAILWAY_ENVIRONMENT_NAME', 'RAILWAY_ENVIRONMENT'
    ))


def get_mysql_uri():
    """Builds the MySQL connection URI using PyMySQL."""
    encoded_password = quote_plus(DB_PASSWORD) if DB_PASSWORD else ''
    encoded_user = quote_plus(DB_USER)
    return f"mysql+pymysql://{encoded_user}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"


def get_sqlite_fallback_uri():
    """Returns local SQLite URI fallback."""
    basedir = os.path.abspath(os.path.dirname(__file__))
    return f"sqlite:///{os.path.join(basedir, 'college_connect.db')}"


def get_active_database_uri():
    """
    Checks if MySQL is reachable with configured .env credentials.
    If yes, returns MySQL URI.
    If credentials are placeholders or MySQL is not yet configured,
    safely falls back to local SQLite to prevent runtime crashes.
    """
    if APP_ENV == 'test':
        test_database_url = os.environ.get('TEST_DATABASE_URL', 'sqlite:///:memory:')
        return test_database_url, 'TEST DATABASE'

    # Railway and other hosts commonly inject a complete connection URL.
    database_url = (
        os.environ.get('DATABASE_URL', '').strip()
        or os.environ.get('MYSQL_URL', '').strip()
    )
    if database_url:
        if database_url.startswith('mysql://'):
            database_url = 'mysql+pymysql://' + database_url[len('mysql://'):]
        if not database_url.startswith('mysql+pymysql://'):
            raise RuntimeError('Production DATABASE_URL must use MySQL with PyMySQL.')
        source = 'DATABASE_URL' if os.environ.get('DATABASE_URL', '').strip() else 'MYSQL_URL'
        return database_url, f'MYSQL ({source})'

    if not DB_PASSWORD or DB_PASSWORD == 'your_secure_password_here':
        if is_production():
            raise RuntimeError('Production requires a valid MySQL DATABASE_URL or DB_PASSWORD configuration.')
        return get_sqlite_fallback_uri(), 'SQLITE (Placeholder credentials in .env)'

    try:
        import pymysql
        conn = pymysql.connect(
            host=DB_HOST,
            port=int(DB_PORT),
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            connect_timeout=2
        )
        conn.close()
        return get_mysql_uri(), 'MYSQL'
    except Exception as e:
        if is_production():
            raise RuntimeError('Production MySQL connection failed; SQLite fallback is disabled.') from e
        return get_sqlite_fallback_uri(), f'SQLITE (MySQL connection pending: {e})'
