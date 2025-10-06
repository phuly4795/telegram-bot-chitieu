import sqlite3
from datetime import datetime, timedelta

def init_db():
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()

    # Bảng chi tiêu
    c.execute('''CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    amount REAL,
                    reason TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )''')

    # Bảng lưu số dư hiện có
    c.execute('''CREATE TABLE IF NOT EXISTS balance (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    total REAL DEFAULT 0
                )''')

    # Khởi tạo số dư nếu chưa có
    c.execute("INSERT OR IGNORE INTO balance (id, total) VALUES (1, 0)")
    conn.commit()
    conn.close()

# ========== Chi tiêu ==========
def add_expense(amount, reason, date=None):
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    if date:
        c.execute("INSERT INTO expenses (amount, reason, created_at) VALUES (?, ?, ?)", (amount, reason, date))
    else:
        c.execute("INSERT INTO expenses (amount, reason) VALUES (?, ?)", (amount, reason))
    conn.commit()
    conn.close()
    update_balance(-amount)  # trừ tiền khỏi ví khi chi tiêu

def get_expenses(limit=10):
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    c.execute("SELECT amount, reason, created_at FROM expenses ORDER BY id DESC LIMIT ?", (limit,))
    data = c.fetchall()
    conn.close()
    return data

def get_sum_by_range(start_date, end_date):
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    c.execute("SELECT SUM(amount) FROM expenses WHERE DATE(created_at) BETWEEN ? AND ?", (start_date, end_date))
    result = c.fetchone()[0]
    conn.close()
    return result or 0

# ========== Số dư ==========
def get_balance():
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    c.execute("SELECT total FROM balance WHERE id = 1")
    total = c.fetchone()[0]
    conn.close()
    return total

def update_balance(amount):
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    c.execute("UPDATE balance SET total = total + ? WHERE id = 1", (amount,))
    conn.commit()
    conn.close()

def set_balance(amount):
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    c.execute("UPDATE balance SET total = ? WHERE id = 1", (amount,))
    conn.commit()
    conn.close()
