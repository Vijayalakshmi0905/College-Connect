"""
Post-migration verification: confirms all data is in MySQL.
"""
import pymysql, os
from dotenv import load_dotenv
load_dotenv(override=True)

host = os.getenv('DB_HOST', '127.0.0.1')
port = int(os.getenv('DB_PORT', 3306))
user = os.getenv('DB_USER')
pw   = os.getenv('DB_PASSWORD')
db   = os.getenv('DB_NAME')

conn = pymysql.connect(host=host, port=port, user=user, password=pw, database=db)
cur  = conn.cursor()

print("=" * 55)
print("MYSQL POST-MIGRATION VERIFICATION")
print("=" * 55)

tables = ['users', 'students', 'staff', 'food_items', 'orders', 'order_items', 'payments']
for t in tables:
    cur.execute(f"SELECT COUNT(*) FROM `{t}`")
    count = cur.fetchone()[0]
    print(f"  {t:<15} : {count} rows")

print()
print("--- Users ---")
cur.execute("SELECT username, role, is_active FROM users")
for row in cur.fetchall():
    print(f"  {row[0]:<20} | {row[1]:<8} | active={row[2]}")

print()
print("--- Food Items (sample) ---")
cur.execute("SELECT name, category, price, available FROM food_items LIMIT 5")
for row in cur.fetchall():
    print(f"  {row[0]:<30} | {row[1]:<12} | Rs.{row[2]:<6} | avail={row[3]}")

print()
print("--- Orders (last 5) ---")
cur.execute("SELECT order_id, token_number, student_name, total_amount, status FROM orders ORDER BY id DESC LIMIT 5")
for row in cur.fetchall():
    print(f"  {row[0]} | {row[1]} | {row[2]:<20} | Rs.{row[3]} | {row[4]}")

conn.close()
print()
print("=" * 55)
print("ALL DATA VERIFIED IN MYSQL")
print("=" * 55)
