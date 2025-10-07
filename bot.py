import re
import os
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)
from database import (
    init_db, ensure_user_exists, add_expense, get_expenses,
    get_sum_by_range, get_balance, set_balance, update_balance
)

# ============================================
#  HÀM HỖ TRỢ
# ============================================
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

# ============================================
#  LỆNH BOT
# ============================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id
    ensure_user_exists(user_id)
    msg = (
        f"💰 *Bot Quản Lý Chi Tiêu của {user.full_name}*\n\n"
        "Các lệnh hỗ trợ:\n"
        "• /chi [số tiền] [lý do]\n"
        "• /thu [số tiền] [lý do]\n"
        "• /danhsach – xem chi gần đây\n"
        "• /tongchi [ngay|tuan|thang] – thống kê\n"
        "• /sodu – xem hoặc chỉnh số dư\n\n"
        "Hoặc nhắn tự nhiên: `ăn sáng 50k hôm qua`"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    ensure_user_exists(user_id)
    args = context.args

    if len(args) == 0:
        await update.message.reply_text("⚠️ Dùng cú pháp: /chi [số tiền] [lý do]")
        return

    amount = parse_amount(args[0])
    if not amount:
        await update.message.reply_text("⚠️ Không hiểu số tiền.")
        return

    text = " ".join(args[1:])
    date = parse_date_from_text(text)
    reason = re.sub(r"hôm\s?(nay|qua|kia)", "", text, flags=re.IGNORECASE).strip() or "Không ghi lý do"
    date_str = date.strftime("%Y-%m-%d %H:%M:%S") if date else None

    add_expense(user_id, amount, reason, date_str)
    bal = get_balance(user_id)
    await update.message.reply_text(f"✅ {reason}: {amount:,.0f}đ\n💵 Còn lại: {bal:,.0f}đ")

async def list_expenses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    ensure_user_exists(user_id)
    data = get_expenses(user_id)
    if not data:
        await update.message.reply_text("📭 Chưa có chi tiêu nào.")
        return
    msg = "📋 *Chi tiêu gần đây:*\n\n"
    for i, (amount, reason, created_at) in enumerate(data, 1):
        date = created_at.split(" ")[0]
        msg += f"{i}. 💵 {amount:,.0f}đ - {reason} ({date})\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    ensure_user_exists(user_id)
    now = datetime.now()
    arg = context.args[0].lower() if context.args else "ngay"

    if arg in ["ngay", "today"]:
        start = end = now.strftime("%Y-%m-%d")
        label = "hôm nay"
    elif arg in ["tuan", "week"]:
        start = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
        end = now.strftime("%Y-%m-%d")
        label = "tuần này"
    elif arg in ["thang", "month"]:
        start = now.replace(day=1).strftime("%Y-%m-%d")
        end = now.strftime("%Y-%m-%d")
        label = "tháng này"
    else:
        await update.message.reply_text("⚠️ Dùng: /tongchi [ngay|tuan|thang]")
        return

    total = get_sum_by_range(user_id, start, end)
    await update.message.reply_text(f"📊 Tổng chi {label}: {total:,.0f}đ")

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    ensure_user_exists(user_id)
    args = context.args

    if not args:
        await update.message.reply_text(f"💰 Số dư: {get_balance(user_id):,.0f}đ")
        return

    action = args[0].lower()
    if len(args) < 2:
        await update.message.reply_text("⚠️ /sodu [set|them|tru] [số tiền]")
        return

    amount = parse_amount(args[1])
    if not amount:
        await update.message.reply_text("⚠️ Không hiểu số tiền.")
        return

    if action == "set":
        set_balance(user_id, amount)
        msg = f"✅ Đặt lại số dư: {amount:,.0f}đ"
    elif action == "them":
        update_balance(user_id, amount)
        msg = f"💵 +{amount:,.0f}đ → {get_balance(user_id):,.0f}đ"
    elif action == "tru":
        update_balance(user_id, -amount)
        msg = f"💸 -{amount:,.0f}đ → {get_balance(user_id):,.0f}đ"
    else:
        msg = "⚠️ /sodu [set|them|tru] [số tiền]"

    await update.message.reply_text(msg)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    ensure_user_exists(user_id)
    text = update.message.text.lower()
    match = re.search(r"([\d\.]+)\s*(k|tr|ngan|ngàn|triệu|m|vnđ|đ)?", text)
    if not match:
        return

    amount = parse_amount(match.group())
    if not amount:
        return

    reason = re.sub(match.group(), "", text).strip() or "Không ghi lý do"
    date = parse_date_from_text(text)
    date_str = date.strftime("%Y-%m-%d %H:%M:%S") if date else None

    add_expense(user_id, amount, reason, date_str)
    bal = get_balance(user_id)
    await update.message.reply_text(f"✅ {reason}: {amount:,.0f}đ\n💵 Còn lại: {bal:,.0f}đ")

async def add_income(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    ensure_user_exists(user_id)
    args = context.args

    if len(args) == 0:
        await update.message.reply_text("⚠️ Dùng cú pháp: /thu [số tiền] [lý do]")
        return

    amount = parse_amount(args[0])
    if not amount:
        await update.message.reply_text("⚠️ Không hiểu số tiền.")
        return

    text = " ".join(args[1:])
    date = parse_date_from_text(text)
    reason = re.sub(r"hôm\s?(nay|qua|kia)", "", text, flags=re.IGNORECASE).strip() or "Không ghi lý do"
    date_str = date.strftime("%Y-%m-%d %H:%M:%S") if date else None

    add_expense(user_id, amount, reason, date_str, type="thu")
    bal = get_balance(user_id)
    await update.message.reply_text(f"✅ Thu nhập: {reason} +{amount:,.0f}đ\n💰 Số dư: {bal:,.0f}đ")

# ============================================
#  KHỞI ĐỘNG BOT
# ============================================
if __name__ == "__main__":
    init_db()
    TOKEN = os.environ.get("BOT_TOKEN", "8159142699:AAGxtGXKYICIF1mPRKzkI9Kn373BQd6XNBI")

    # ✅ Lấy hostname Render để đăng ký webhook
    render_hostname = os.environ.get("RENDER_EXTERNAL_HOSTNAME")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("chi", add))
    app.add_handler(CommandHandler("thu", add_income))
    app.add_handler(CommandHandler("danhsach", list_expenses))
    app.add_handler(CommandHandler("tongchi", stats))
    app.add_handler(CommandHandler("sodu", balance))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("🌐 Đang khởi động bot với webhook...")

    # ✅ Chạy webhook (Render yêu cầu phải lắng nghe port)
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        url_path=TOKEN,
        webhook_url=f"https://{render_hostname}/{TOKEN}",
    )
