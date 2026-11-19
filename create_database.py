"""Provision the CollegeConnect MySQL database and app user from environment variables.

Required variables: MYSQL_ADMIN_USER, MYSQL_ADMIN_PASSWORD, DB_USER,
DB_PASSWORD, and DB_NAME. The administrator account is used only by this
one-time provisioning script; the Flask app uses DB_USER/DB_PASSWORD.
"""

import os
import re
import sys

import pymysql
from dotenv import load_dotenv

load_dotenv()


def main():
    admin_user = os.environ.get('MYSQL_ADMIN_USER', '').strip()
    admin_password = os.environ.get('MYSQL_ADMIN_PASSWORD', '')
    app_user = os.environ.get('DB_USER', '').strip()
    app_password = os.environ.get('DB_PASSWORD', '')
    database = os.environ.get('DB_NAME', '').strip()
    host = os.environ.get('DB_HOST', '127.0.0.1').strip()
    port = int(os.environ.get('DB_PORT', '3306'))
    app_host = os.environ.get('DB_APP_HOST', 'localhost').strip()

    missing = [key for key, value in (
        ('MYSQL_ADMIN_USER', admin_user), ('MYSQL_ADMIN_PASSWORD', admin_password),
        ('DB_USER', app_user), ('DB_PASSWORD', app_password), ('DB_NAME', database)
    ) if not value]
    if missing:
        raise ValueError('Missing required environment variables: ' + ', '.join(missing))
    if not re.fullmatch(r'[A-Za-z0-9_]+', database):
        raise ValueError('DB_NAME may contain only letters, digits, and underscores.')

    connection = pymysql.connect(
        host=host, port=port, user=admin_user, password=admin_password,
        connect_timeout=5, charset='utf8mb4'
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{database}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            # PyMySQL safely quotes parameter values before sending the DDL.
            cursor.execute(
                'CREATE USER IF NOT EXISTS %s@%s IDENTIFIED BY %s',
                (app_user, app_host, app_password)
            )
            cursor.execute(
                'ALTER USER %s@%s IDENTIFIED BY %s',
                (app_user, app_host, app_password)
            )
            cursor.execute(
                f'GRANT ALL PRIVILEGES ON `{database}`.* TO %s@%s',
                (app_user, app_host)
            )
        connection.commit()
        print(f"Provisioned database '{database}' and application user '{app_user}'.")
    finally:
        connection.close()


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'Provisioning failed: {error}', file=sys.stderr)
        raise SystemExit(1)
