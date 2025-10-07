import sqlite3
from datetime import datetime, timedelta

DB_PATH = "expenses.db"

# =====================================================
#  HỖ TRỢ: Tự động đảm bảo bảng và cột tồn tại
# =====================================================
def ensure_column_exists(table, column, col_type, default=None):
    """Tự động thêm cột vào bảng nếu chưa có."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in c.fetchall()]

    if column not in columns:
        default_clause = f" DEFAULT '{default}'" if default is not None else ""
        try:
            c.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}{default_clause}")
            print(f"✅ Đã thêm cột mới: {table}.{column}")
        except Exception as e:
            print(f"⚠️ Không thể thêm cột {column} vào {table}: {e}")

    conn.commit()
    conn.close()


# =====================================================
#  KHỞI TẠO CƠ SỞ DỮ LIỆU
# =====================================================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Bảng chi tiêu / thu nhập
    c.execute('''CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    amount REAL,
                    reason TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )''')

    # Bảng số dư
    c.execute('''CREATE TABLE IF NOT EXISTS balance (
                    user_id INTEGER PRIMARY KEY,
                    total REAL DEFAULT 0
                )''')

    # Bảng người dùng
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    full_name TEXT,
                    username TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )''')

    conn.commit()
    conn.close()

    # ✅ Đảm bảo cột mới tồn tại (auto migrate)
    ensure_column_exists("expenses", "type", "TEXT", default="chi")


# =====================================================
#  NGƯỜI DÙNG
# =====================================================
def ensure_user_exists(user_id, full_name=None, username=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''INSERT OR IGNORE INTO users (user_id, full_name, username)
                 VALUES (?, ?, ?)''', (user_id, full_name, username))
    c.execute("INSERT OR IGNORE INTO balance (user_id, total) VALUES (?, 0)", (user_id,))

    conn.commit()
    conn.close()


# =====================================================
#  GIAO DỊCH (CHI / THU)
# =====================================================
def add_expense(user_id, amount, reason, date=None, type="chi"):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if date:
        c.execute(
            "INSERT INTO expenses (user_id, amount, reason, created_at, type) VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, reason, date, type)
        )
    else:
        c.execute(
            "INSERT INTO expenses (user_id, amount, reason, type) VALUES (?, ?, ?, ?)",
            (user_id, amount, reason, type)
        )

    # Cập nhật số dư: chi thì trừ, thu thì cộng
    if type == "chi":
        c.execute("UPDATE balance SET total = total - ? WHERE user_id = ?", (amount, user_id))
    elif type == "thu":
        c.execute("UPDATE balance SET total = total + ? WHERE user_id = ?", (amount, user_id))

    conn.commit()
    conn.close()


def get_expenses(user_id, limit=10):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT amount, reason, created_at, type FROM expenses WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (user_id, limit)
    )
    data = c.fetchall()
    conn.close()
    return data


def get_sum_by_range(user_id, start_date, end_date, type_filter="chi"):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """SELECT SUM(amount) FROM expenses 
           WHERE user_id = ? AND type = ? AND DATE(created_at) BETWEEN ? AND ?""",
        (user_id, type_filter, start_date, end_date)
    )
    result = c.fetchone()[0]
    conn.close()
    return result or 0


# =====================================================
#  SỐ DƯ
# =====================================================
def get_balance(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT total FROM balance WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0


def set_balance(user_id, amount):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE balance SET total = ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()


def update_balance(user_id, amount):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE balance SET total = total + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()
