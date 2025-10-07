import os
import psycopg2
from psycopg2.extras import RealDictCursor

DB_URL = os.environ.get("DB_URL")

def get_connection():
    return psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)

def ensure_column_exists(table, column, column_def):
    """Kiểm tra và tự thêm cột nếu chưa có"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = %s AND column_name = %s
    """, (table, column))
    exists = cur.fetchone()
    if not exists:
        print(f"🧱 Thêm cột mới: {table}.{column}")
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_def}")
        conn.commit()
    conn.close()

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # Tạo bảng users
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            full_name TEXT,
            username TEXT,
            balance NUMERIC DEFAULT 0
        )
    """)

    # Tạo bảng expenses
    cur.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id SERIAL PRIMARY KEY,
            user_id BIGINT REFERENCES users(user_id),
            amount NUMERIC,
            reason TEXT,
            date TIMESTAMP DEFAULT NOW(),
            type TEXT DEFAULT 'chi'
        )
    """)

    conn.commit()
    conn.close()

    # Đảm bảo có đủ các cột mới
    ensure_column_exists("expenses", "type", "TEXT DEFAULT 'chi'")

def ensure_user_exists(user_id, full_name=None, username=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO users (user_id, full_name, username)
        VALUES (%s, %s, %s)
        ON CONFLICT (user_id) DO NOTHING
    """, (user_id, full_name, username))
    conn.commit()
    conn.close()

def add_expense(user_id, amount, reason, date=None, type="chi"):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO expenses (user_id, amount, reason, date, type)
        VALUES (%s, %s, %s, %s, %s)
    """, (user_id, amount, reason, date, type))
    delta = -amount if type == "chi" else amount
    cur.execute("UPDATE users SET balance = balance + %s WHERE user_id=%s", (delta, user_id))
    conn.commit()
    conn.close()

def get_expenses(user_id, limit=10):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT amount, reason, to_char(date, 'YYYY-MM-DD HH24:MI') AS date
        FROM expenses
        WHERE user_id=%s
        ORDER BY id DESC
        LIMIT %s
    """, (user_id, limit))
    data = cur.fetchall()
    conn.close()
    return [(d['amount'], d['reason'], d['date']) for d in data]

def get_sum_by_range(user_id, start, end):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM expenses
        WHERE user_id=%s AND date::date BETWEEN %s AND %s AND type='chi'
    """, (user_id, start, end))
    total = cur.fetchone()[0] or 0
    conn.close()
    return total

def get_balance(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT balance FROM users WHERE user_id=%s", (user_id,))
    result = cur.fetchone()
    conn.close()
    return result[0] if result else 0

def set_balance(user_id, amount):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET balance=%s WHERE user_id=%s", (amount, user_id))
    conn.commit()
    conn.close()

def update_balance(user_id, delta):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET balance = balance + %s WHERE user_id=%s", (delta, user_id))
    conn.commit()
    conn.close()