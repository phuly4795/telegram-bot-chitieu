from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from datetime import datetime, timedelta
from database import (
    init_db, add_expense, get_expenses, get_sum_by_range,
    get_balance, update_balance, set_balance
)
import re
import os

TOKEN = os.environ.get("BOT_TOKEN")
# TOKEN = "8159142699:AAGxtGXKYICIF1mPRKzkI9Kn373BQd6XNBI"

init_db()

# ---- Hàm hỗ trợ ----
def parse_amount(text):
    text = text.lower().replace(',', '').strip()
    match = re.search(r"([\d\.]+)\s*(k|tr|ngan|ngàn|triệu|m|vnđ|đ)?", text)
    if not match:
        return None
    value, unit = match.groups()
    value = float(value)
    if not unit:
        return value
    if unit in ['k', 'ngan', 'ngàn']:
        return value * 1000
    if unit in ['tr', 'triệu', 'm']:
        return value * 1_000_000
    return value

def parse_date_from_text(text):
    text = text.lower()
    today = datetime.now()
    if "hôm qua" in text:
        return today - timedelta(days=1)
    elif "hôm kia" in text:
        return today - timedelta(days=2)
    elif "hôm nay" in text or "nay" in text:
        return today
    return None

# ---- Các lệnh Bot ----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "💰 *Bot Quản Lý Chi Tiêu*\n\n"
        "Bạn có thể dùng:\n"
        "• /them [số tiền] [lý do]\n"
        "   👉 Ví dụ: `/them 50k ăn sáng hôm nay`\n\n"
        "• Hoặc chỉ cần nhắn tự nhiên: `ăn sáng 50k`\n\n"
        "• /danhsach – xem chi tiêu gần đây\n"
        "• /tongchi [ngay|tuan|thang] – xem tổng chi\n"
        "• /sodu – xem hoặc chỉnh số dư\n"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        if len(args) == 0:
            raise ValueError
        amount_raw = args[0]
        amount = parse_amount(amount_raw)
        if amount is None:
            await update.message.reply_text("⚠️ Không hiểu số tiền bạn nhập.")
            return
        text = " ".join(args[1:])
        date = parse_date_from_text(text)
        reason = re.sub(r"hôm\s?(nay|qua|kia)", "", text, flags=re.IGNORECASE).strip()
        add_expense(amount, reason or "Không ghi lý do", date.strftime("%Y-%m-%d %H:%M:%S") if date else None)
        update_balance(-amount)  # tự trừ số dư
        bal = get_balance()
        await update.message.reply_text(f"✅ Đã ghi: {amount:,.0f}đ cho '{reason or 'Không lý do'}'\n💵 Số dư còn lại: {bal:,.0f}đ")
    except Exception:
        await update.message.reply_text("⚠️ Dùng cú pháp: /them [số tiền] [lý do]\nVí dụ: /them 50k ăn sáng hôm nay")

async def list_expenses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = get_expenses()
    if not data:
        await update.message.reply_text("📭 Chưa có chi tiêu nào")
        return
    msg = "📋 Chi tiêu gần đây:\n\n"
    for amount, reason, created_at in data:
        msg += f"💵 {amount:,.0f}đ - {reason} ({created_at})\n"
    await update.message.reply_text(msg)

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()
    arg = context.args[0].lower() if context.args else "today"

    if arg in ["today", "ngay"]:
        start = end = now.strftime("%Y-%m-%d")
        label = "hôm nay"
    elif arg in ["week", "tuan"]:
        start = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
        end = now.strftime("%Y-%m-%d")
        label = "tuần này"
    elif arg in ["month", "thang"]:
        start = now.replace(day=1).strftime("%Y-%m-%d")
        end = now.strftime("%Y-%m-%d")
        label = "tháng này"
    else:
        await update.message.reply_text("⚠️ Dùng: /tongchi [ngay|tuan|thang]")
        return

    total = get_sum_by_range(start, end)
    await update.message.reply_text(f"📊 Tổng chi {label}: {total:,.0f}đ")

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        total = get_balance()
        await update.message.reply_text(f"💰 Số dư hiện có: {total:,.0f}đ")
        return

    action = args[0].lower()
    if len(args) < 2:
        await update.message.reply_text("⚠️ Cú pháp: /sodu [set|them|tru] [số tiền]")
        return

    amount = parse_amount(args[1])
    if amount is None:
        await update.message.reply_text("⚠️ Không hiểu số tiền bạn nhập.")
        return

    if action == "set":
        set_balance(amount)
        msg = f"✅ Đặt lại số dư: {amount:,.0f}đ"
    elif action == "them":
        update_balance(amount)
        msg = f"💵 Cộng thêm {amount:,.0f}đ → Số dư mới: {get_balance():,.0f}đ"
    elif action == "tru":
        update_balance(-amount)
        msg = f"💸 Trừ {amount:,.0f}đ → Số dư mới: {get_balance():,.0f}đ"
    else:
        msg = "⚠️ Dùng: /sodu [set|them|tru] [số tiền]"

    await update.message.reply_text(msg)

# ---- Nhận tin nhắn tự nhiên ----
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()

    # Tìm số tiền trong tin nhắn
    match = re.search(r"([\d\.]+)\s*(k|tr|ngan|ngàn|triệu|m|vnđ|đ)?", text)
    if not match:
        return  # không chứa số tiền, bỏ qua

    amount = parse_amount(match.group())
    if amount is None:
        return

    reason = re.sub(match.group(), "", text).strip()
    date = parse_date_from_text(text)

    add_expense(amount, reason or "Không ghi lý do", date.strftime("%Y-%m-%d %H:%M:%S") if date else None)
    update_balance(-amount)

    bal = get_balance()
    await update.message.reply_text(f"✅ Đã ghi: {amount:,.0f}đ cho '{reason or 'Không lý do'}'\n💵 Số dư còn lại: {bal:,.0f}đ")

# ---- Chạy bot ----
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("them", add))
app.add_handler(CommandHandler("danhsach", list_expenses))
app.add_handler(CommandHandler("tongchi", stats))
app.add_handler(CommandHandler("sodu", balance))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

if __name__ == "__main__":
    print("🤖 Bot đang chạy...")
    app.run_polling()
