import sqlite3
from datetime import datetime, timedelta

def init_db():
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()

    # Bảng chi tiêu
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

    conn.commit()
    conn.close()

def ensure_user_exists(user_id):
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO balance (user_id, total) VALUES (?, 0)", (user_id,))
    conn.commit()
    conn.close()

# ---------- Chi tiêu ----------
def add_expense(user_id, amount, reason, date=None):
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    if date:
        c.execute("INSERT INTO expenses (user_id, amount, reason, created_at) VALUES (?, ?, ?, ?)",
                  (user_id, amount, reason, date))
    else:
        c.execute("INSERT INTO expenses (user_id, amount, reason) VALUES (?, ?, ?)",
                  (user_id, amount, reason))
    c.execute("UPDATE balance SET total = total - ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def get_expenses(user_id, limit=10):
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    c.execute("SELECT amount, reason, created_at FROM expenses WHERE user_id = ? ORDER BY id DESC LIMIT ?",
              (user_id, limit))
    data = c.fetchall()
    conn.close()
    return data

def get_sum_by_range(user_id, start_date, end_date):
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    c.execute("SELECT SUM(amount) FROM expenses WHERE user_id = ? AND DATE(created_at) BETWEEN ? AND ?",
              (user_id, start_date, end_date))
    result = c.fetchone()[0]
    conn.close()
    return result or 0

# ---------- Số dư ----------
def get_balance(user_id):
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    c.execute("SELECT total FROM balance WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

def set_balance(user_id, amount):
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    c.execute("UPDATE balance SET total = ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def update_balance(user_id, amount):
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    c.execute("UPDATE balance SET total = total + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()
