-- ============================================================
-- College Connect - MySQL Setup Notes
-- Database credentials must be supplied through environment variables.
-- This SQL file intentionally contains no application password.
-- ============================================================

-- Provision the database and least-privilege application user with:
--   MYSQL_ADMIN_USER, MYSQL_ADMIN_PASSWORD  (administrator credentials)
--   DB_USER, DB_PASSWORD, DB_NAME           (application credentials)
--   python create_database.py
-- Do not put credential values in this file or commit them to source control.

-- Optional: create the database manually if you are already connected as an admin.
CREATE DATABASE IF NOT EXISTS college_connect
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

SHOW DATABASES LIKE 'college_connect';
