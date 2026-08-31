# ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
#  ★彡 MESTRAX RESELLER BOT ★彡
#  Professional Telegram Reseller Bot with Premium Design
#  Powered by pyTelegramBotAPI + Flask (Render Ready)
# ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════

import telebot
import json
import os
import random
import string
import threading
import logging
from datetime import datetime, timedelta
from flask import Flask, request
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from apscheduler.schedulers.background import BackgroundScheduler

# ═════════════════════════════════════════════════════════════════════════════════════════════════════════
#  ⚙️  CONFIGURATION
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════

BOT_TOKEN = "8955914962:AAGaKX_67-xro2dGsRzPiLxv2hdBnB6-HfA"
ADMIN_IDS = [8254258071]
DATA_FILE = "reseller_data.json"

# ═════════════════════════════════════════════════════════════════════════════════════════════════════════
#  ⚙️  FLASK + WEBHOOK CONFIG (Render)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════

app = Flask(__name__)

RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL", "")
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"{RENDER_URL}{WEBHOOK_PATH}" if RENDER_URL else ""

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(BOT_TOKEN)

# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
#  ⏰  CRON / SCHEDULED TASKS (APScheduler)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════

scheduler = BackgroundScheduler()


def cron_reset_daily_limits():
    """Reset daily generation limits for all resellers - runs at midnight"""
    today_str = datetime.now().strftime("%Y-%m-%d")
    reset_count = 0
    for uid, rdata in data["resellers"].items():
        if rdata.get("last_gen_date") != today_str:
            data["resellers"][uid]["today_generated"] = 0
            data["resellers"][uid]["last_gen_date"] = today_str
            reset_count += 1
    if reset_count > 0:
        save_data(data)
        logger.info(f"[CRON] Reset daily limits for {reset_count} resellers")


def cron_clean_expired_codes():
    """Clean used codes older than 30 days - runs daily at 3 AM"""
    thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
    to_remove = [k for k, v in data["codes"].items()
                  if v.get("status") == "used" and v.get("used_date", "") < thirty_days_ago]
    for k in to_remove:
        del data["codes"][k]
    if to_remove:
        save_data(data)
        logger.info(f"[CRON] Cleaned {len(to_remove)} expired codes")


def cron_auto_backup():
    """Auto backup data every 6 hours, keep last 5 backups"""
    backup_file = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    try:
        with open(backup_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        backups = sorted([f for f in os.listdir(".") if f.startswith("backup_") and f.endswith(".json")])
        for old_bak in backups[:-5]:
            os.remove(old_bak)
        logger.info(f"[CRON] Auto backup saved: {backup_file}")
    except Exception as e:
        logger.error(f"[CRON] Backup failed: {e}")


scheduler.add_job(cron_reset_daily_limits, 'cron', hour=0, minute=0, id='reset_daily')
scheduler.add_job(cron_clean_expired_codes, 'cron', hour=3, minute=0, id='clean_codes')
scheduler.add_job(cron_auto_backup, 'interval', hours=6, id='auto_backup')

# Premium Emojis
E = {
    "star": "\u2b50", "crown": "\U0001f451", "diamond": "\U0001f48e",
    "fire": "\U0001f525", "bolt": "\u26a1", "check": "\u2705",
    "x": "\u274c", "warn": "\u26a0\ufe0f", "lock": "\U0001f512",
    "key": "\U0001f511", "coin": "\U0001fa99", "money": "\U0001f4b0",
    "gift": "\U0001f381", "rocket": "\U0001f680", "trophy": "\U0001f3c6",
    "sparkles": "\u2728", "gem": "\U0001f48e", "shield": "\U0001f6e1\ufe0f",
    "chart": "\U0001f4c8", "user": "\U0001f464", "users": "\U0001f465",
    "gear": "\u2699\ufe0f", "plus": "\u2795", "minus": "\u2796",
    "box": "\U0001f4e6", "card": "\U0001f4b3", "bank": "\U0001f3e6",
    "clock": "\u23f0", "cal": "\U0001f4c5", "info": "\u2139\ufe0f",
    "pin": "\U0001f4cc", "bell": "\U0001f514", "heart": "\u2764\ufe0f",
    "medal": "\U0001f3c5", "bulb": "\U0001f4a1", "tool": "\U0001f527",
    "eye": "\U0001f441", "stats": "\U0001f4ca", "zap": "\u26a1",
    "store": "\U0001f3ea", "tag": "\U0001f3f7\ufe0f", "ticket": "\U0001f3ab",
    "infinity": "\u267e\ufe0f", " recycle": "\u267b\ufe0f",
    "arrow": "\u27a1\ufe0f", "back": "\u2b05\ufe0f", "home": "\U0001f3e0",
    "menu": "\U0001f5d2\ufe0f", "exit": "\U0001f6aa",
    "success": "\U0001f7e2", "fail": "\U0001f534",
    "online": "\U0001f7e2", "offline": "\U0001f534",
    "admin": "\U0001f451", "reseller": "\U0001f451",
}

# ═════════════════════════════════════════════════════════════════════════════════════════════════════════
#  \U0001f4be  DATA MANAGEMENT (JSON)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════

def load_data():
    default = {
        "admins": {str(aid): {"name": "Owner", "created": datetime.now().isoformat()} for aid in ADMIN_IDS},
        "resellers": {},
        "products": {},
        "keys": {},
        "transactions": [],
        "settings": {
            "bot_name": "MESTRAX RESELLER",
            "currency": "$",
            "welcome_msg": "",
            "max_daily_gen": 50,
        },
        "bans": {},
        "codes": {},
    }
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for key in default:
                if key not in data:
                    data[key] = default[key]
            return data
        except Exception:
            return default
    return default


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


data = load_data()

# Temporary states for multi-step inputs
user_states = {}

# ═════════════════════════════════════════════════════════════════════════════════════════════════════════
#  \U0001f6e1  ACCESS CONTROL
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════

def is_admin(user_id):
    return str(user_id) in data.get("admins", {}) or user_id in ADMIN_IDS


def is_reseller(user_id):
    return str(user_id) in data.get("resellers", {})


def is_banned(user_id):
    return str(user_id) in data.get("bans", {})


def has_access(user_id):
    return is_admin(user_id) or is_reseller(user_id)

# ═════════════════════════════════════════════════════════════════════════════════════════════════════════
#  \U0001f3a8  PREMIUM TEXT FORMATTING
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════

def bold(text):
    return f"<b>{text}</b>"


def italic(text):
    return f"<i>{text}</i>"


def code(text):
    return f"<code>{text}</code>"


def spoiler(text):
    return f"<tg-spoiler>{text}</tg-spoiler>"


def underline(text):
    return f"<u>{text}</u>"


def strike(text):
    return f"<s>{text}</s>"


def separator():
    return f"\n{E['sparkles']} {'━' * 22} {E['sparkles']}\n"


def header(text):
    return f"\n{E['crown']} {bold(text)} {E['crown']}\n"


def currency(amount):
    cur = data["settings"]["currency"]
    return f"{amount}{cur}"


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════
#  \U0001f527  KEY GENERATOR
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════

def gen_key(prefix="MESTRAX", length=16):
    chars = string.ascii_uppercase + string.digits
    mid = ''.join(random.choices(chars, k=length))
    return f"{prefix}-{mid}"


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════
#  \U0001f4b0  BALANCE & TRANSACTION HELPERS
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════

def get_balance(user_id):
    uid = str(user_id)
    if uid in data["resellers"]:
        return data["resellers"][uid].get("balance", 0)
    if uid in data["admins"]:
        return data["admins"][uid].get("balance", 0)
    return 0


def set_balance(user_id, amount):
    uid = str(user_id)
    if uid in data["resellers"]:
        data["resellers"][uid]["balance"] = amount
    elif uid in data["admins"]:
        data["admins"][uid]["balance"] = amount
    save_data(data)


def add_balance(user_id, amount):
    new_bal = get_balance(user_id) + amount
    set_balance(user_id, new_bal)
    return new_bal


def sub_balance(user_id, amount):
    new_bal = get_balance(user_id) - amount
    set_balance(user_id, new_bal)
    return new_bal


def add_transaction(user_id, action, details, amount=0):
    data["transactions"].append({
        "user_id": str(user_id),
        "action": action,
        "details": details,
        "amount": amount,
        "date": datetime.now().isoformat(),
    })
    if len(data["transactions"]) > 500:
        data["transactions"] = data["transactions"][-500:]
    save_data(data)

# ═════════════════════════════════════════════════════════════════════════════════════════════════════════
#  \U0001f3ea  STOCK HELPERS
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════

def get_product_stock(pid):
    return [k for k, v in data["keys"].items() if v.get("product_id") == pid and v.get("status") == "available"]


def get_total_sold(pid):
    return len([k for k, v in data["keys"].items() if v.get("product_id") == pid and v.get("status") == "sold"])


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════
#  \u2328\ufe0f  INLINE KEYBOARD BUILDER
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════

def build_menu(buttons, n_cols=2):
    menu = []
    for i in range(0, len(buttons), n_cols):
        menu.append(buttons[i:i + n_cols])
    return menu


def btn(text, callback_data):
    return InlineKeyboardButton(text, callback_data=callback_data)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════
#  \U0001f3e0  START / MAIN MENU
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════

@bot.message_handler(commands=['start'])
def cmd_start(message):
    uid = message.from_user.id
    uname = message.from_user.first_name or "User"

    if is_banned(uid):
        bot.reply_to(message, f"{E['lock']} {bold('محظور')} \n\n"
                           f"عذراً {uname}، حسابك محظور من استخدام البوت.\n"
                           f"{E['warn']} تواصل مع الإدارة إذا كنت تعتقد أن هذا خطأ.")
        return

    if not has_access(uid):
        bot.reply_to(message,
            f"{E['lock']} {bold('غير مصرح')}\n\n"
            f"{E['shield']} مرحباً {bold(uname)}\n\n"
            f"{E['x']} هذا البوت يعمل فقط على الحسابات المُنشأة من قبل الإدارة.\n"
            f"{E['warn']} لا يمكنك استخدام البوت بدون صلاحية.\n\n"
            f"{E['info']} {italic('تواصل مع المالك للحصول على حساب ريسيلر.')}")
        return

    # Register user activity
    add_transaction(uid, "login", f"{uname} دخل البوت")

    if is_admin(uid):
        show_admin_panel(message)
    else:
        show_reseller_panel(message)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════
#  \U0001f451  ADMIN PANEL
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════

def show_admin_panel(message):
    uid = str(message.from_user.id)
    admin_name = data["admins"].get(uid, {}).get("name", "Owner")
    total_resellers = len(data["resellers"])
    total_products = len(data["products"])
    total_keys = len(data["keys"])
    available_keys = len([k for k, v in data["keys"].items() if v.get("status") == "available"])
    total_balance = sum(get_balance(int(r)) for r in data["resellers"])

    text = (
        f"{E['sparkles']}{'━' * 30}{E['sparkles']}\n"
        f"{E['crown']}  {bold('MESTRAX ADMIN PANEL')}  {E['crown']}\n"
        f"{E['sparkles']}{'━' * 30}{E['sparkles']}\n\n"
        f"{E['user']}  {bold('مرحباً')} {italic(admin_name)}\n"
        f"{E['shield']}  {bold('الصلاحية:')} {bold('المدير')} {E['crown']}\n\n"
        f"{E['stats']}  {bold('─── الإحصائيات ───')}\n"
        f"{E['users']}  الريسيلرات: {bold(str(total_resellers))}\n"
        f"{E['box']}  المنتجات: {bold(str(total_products))}\n"
        f"{E['key']}  المفاتيح: {bold(str(total_keys))}  |  متاح: {bold(str(available_keys))}\n"
        f"{E['bank']}  إجمالي أرصدة الريسيلرات: {bold(currency(total_balance))}\n"
        f"{E['chart']}  المعاملات: {bold(str(len(data['transactions'])))}\n\n"
        f"{E['gear']}  {bold('─── لوحة التحكم ───')}"
    )

    buttons = [
        [btn(f"{E['users']}  إدارة الريسيلرات", "admin_resellers"),
         btn(f"{E['box']}  إدارة المنتجات", "admin_products")],
        [btn(f"{E['key']}  إدارة المفاتيح", "admin_keys"),
         btn(f"{E['money']}  إدارة الأرصدة", "admin_balance")],
        [btn(f"{E['chart']}  التقارير", "admin_reports"),
         btn(f"{E['ticket']}  أكواد الشحن", "admin_codes")],
        [btn(f"{E['gear']}  إعدادات البوت", "admin_settings"),
         btn(f"{E['shield']}  الحظر / الطرد", "admin_bans")],
        [btn(f"{E['recycle']}  أدوات متقدمة", "admin_tools")],
    ]

    bot.send_message(message.chat.id, text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")

# ═════════════════════════════════════════════════════════════════════════════════════════════════════════
#  \U0001f451  RESELLER PANEL
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════

def show_reseller_panel(message):
    uid = str(message.from_user.id)
    rdata = data["resellers"].get(uid, {})
    rname = rdata.get("name", "Reseller")
    balance = get_balance(int(uid))
    rlevel = rdata.get("level", "\u26aa سيلفر")
    daily_limit = rdata.get("daily_limit", data["settings"]["max_daily_gen"])
    today_gen = rdata.get("today_generated", 0)
    today_str = datetime.now().strftime("%Y-%m-%d")
    if rdata.get("last_gen_date") != today_str:
        today_gen = 0
        data["resellers"][uid]["today_generated"] = 0
        data["resellers"][uid]["last_gen_date"] = today_str
        save_data(data)

    text = (
        f"{E['sparkles']}{'━' * 30}{E['sparkles']}\n"
        f"{E['crown']}  {bold('MESTRAX RESELLER')}  {E['crown']}\n"
        f"{E['sparkles']}{'━' * 30}{E['sparkles']}\n\n"
        f"{E['user']}  {bold('مرحباً')} {italic(rname)}\n"
        f"{E['trophy']}  {bold('المستوى:')} {rlevel}\n"
        f"{E['bank']}  {bold('الرصيد:')} {bold(currency(balance))}\n\n"
        f"{E['stats']}  {bold('─── إحصائياتك ───')}\n"
        f"{E['key']}  مفاتيح اليوم: {bold(f'{today_gen}/{daily_limit}')}\n"
        f"{E['box']}  إجمالي المنتجات: {bold(str(len(data['products'])))}\n"
        f"{E['chart']}  معاملاتك: {bold(str(len([t for t in data['transactions'] if t['user_id'] == uid])))}\n"
    )

    buttons = [
        [btn(f"{E['store']}  المتجر", "reseller_shop"),
         btn(f"{E['key']}  مفاتيحي", "reseller_my_keys")],
        [btn(f"{E['money']}  رصيدي", "reseller_balance_info"),
         btn(f"{E['ticket']}  شحن رصيد", "reseller_recharge")],
        [btn(f"{E['chart']}  تقاريري", "reseller_stats"),
         btn(f"{E['user']}  حسابي", "reseller_profile")],
        [btn(f"{E['info']}  مساعدة", "reseller_help")],
    ]

    bot.send_message(message.chat.id, text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")

# ═════════════════════════════════════════════════════════════════════════════════════════════════════════
#  \U0001f3ea  ADMIN: RESELLER MANAGEMENT
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════

@bot.callback_query_handler(func=lambda c: c.data == "admin_resellers")
def admin_resellers(call):
    if not is_admin(call.from_user.id):
        return
    text = (
        f"{E['users']}  {bold('إدارة الريسيلرات')}\n\n"
        f"{E['info']} اختر عملية لإدارة الريسيلرات:\n"
        f"{E['users']} عدد الريسيلرات: {bold(str(len(data['resellers'])))}"
    )
    buttons = [
        [btn(f"{E['plus']}  إضافة ريسيلر", "admin_add_reseller")],
        [btn(f"{E['eye']}  عرض الريسيلرات", "admin_list_resellers")],
        [btn(f"{E['money']}  تعديل رصيد", "admin_edit_reseller_bal")],
        [btn(f"{E['gear']}  تعديل مستوى", "admin_edit_reseller_level")],
        [btn(f"{E['minus']}  حذف ريسيلر", "admin_del_reseller")],
        [btn(f"{E['back']}  رجوع", "admin_back")],
    ]
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                          reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")


@bot.callback_query_handler(func=lambda c: c.data == "admin_add_reseller")
def admin_add_reseller(call):
    if not is_admin(call.from_user.id):
        return
    user_states[call.from_user.id] = {"step": "add_reseller_id"}
    bot.edit_message_text(
        f"{E['plus']}  {bold('إضافة ريسيلر جديد')}\n\n"
        f"{E['info']} أرسل {bold('معرف التليجرام ID')} للحساب الذي تريد إضافته:\n\n"
        f"{E['warn']} {italic('مثال: 123456789')}",
        call.message.chat.id, call.message.message_id, parse_mode="HTML")


@bot.callback_query_handler(func=lambda c: c.data == "admin_list_resellers")
def admin_list_resellers(call):
    if not is_admin(call.from_user.id):
        return
    if not data["resellers"]:
        bot.answer_callback_query(call.id, "\u274c لا يوجد ريسيلرات!", show_alert=True)
        return
    text = f"{E['users']}  {bold('قائمة الريسيلرات')}\n\n"
    for uid, rdata in data["resellers"].items():
        name = rdata.get("name", "Unknown")
        balance = rdata.get("balance", 0)
        level = rdata.get("level", "\u26aa سيلفر")
        status = "\U0001f7e2 نشط" if not rdata.get("banned") else "\U0001f534 محظور"
        text += (
            f"{E['crown']} {bold(name)} \n"
            f"  {E['user']} ID: {code(uid)}\n"
            f"  {E['bank']} الرصيد: {bold(currency(balance))}\n"
            f"  {E['trophy']} المستوى: {level}\n"
            f"  {E['check']} الحالة: {status}\n\n"
        )
    buttons = [[btn(f"{E['back']}  رجوع", "admin_resellers")]]
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                          reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")


@bot.callback_query_handler(func=lambda c: c.data == "admin_edit_reseller_bal")
def admin_edit_reseller_bal(call):
    if not is_admin(call.from_user.id):
        return
    user_states[call.from_user.id] = {"step": "edit_bal_uid"}
    bot.edit_message_text(
        f"{E['money']}  {bold('تعديل رصيد ريسيلر')}\n\n"
        f"{E['info']} أرسل {bold('ID')} الريسيلر:\n\n"
        f"{E['warn']} {italic('مثال: 123456789')}",
        call.message.chat.id, call.message.message_id, parse_mode="HTML")


@bot.callback_query_handler(func=lambda c: c.data == "admin_edit_reseller_level")
def admin_edit_reseller_level(call):
    if not is_admin(call.from_user.id):
        return
    user_states[call.from_user.id] = {"step": "edit_level_uid"}
    bot.edit_message_text(
        f"{E['trophy']}  {bold('تعديل مستوى ريسيلر')}\n\n"
        f"{E['info']} أرسل {bold('ID')} الريسيلر:\n\n"
        f"{E['warn']} {italic('مثال: 123456789')}",
        call.message.chat.id, call.message.message_id, parse_mode="HTML")


@bot.callback_query_handler(func=lambda c: c.data == "admin_del_reseller")
def admin_del_reseller(call):
    if not is_admin(call.from_user.id):
        return
    user_states[call.from_user.id] = {"step": "del_reseller_uid"}
    bot.edit_message_text(
        f"{E['minus']}  {bold('حذف ريسيلر')}\n\n"
        f"{E['warn']} أرسل {bold('ID')} الريسيلر الذي تريد حذفه:\n\n"
        f"{E['x']} {italic('سيتم حذف الحساب وجميع بياناته نهائياً!')}",
        call.message.chat.id, call.message.message_id, parse_mode="HTML")

# ═════════════════════════════════════════════════════════════════════════════════════════════════════════
#  \U0001f4e6  ADMIN: PRODUCT MANAGEMENT
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════

@bot.callback_query_handler(func=lambda c: c.data == "admin_products")
def admin_products(call):
    if not is_admin(call.from_user.id):
        return
    text = (
        f"{E['box']}  {bold('إدارة المنتجات')}\n\n"
        f"{E['info']} اختر عملية لإدارة المنتجات:\n"
        f"{E['box']} عدد المنتجات: {bold(str(len(data['products'])))}"
    )
    buttons = [
        [btn(f"{E['plus']}  إضافة منتج", "admin_add_product")],
        [btn(f"{E['eye']}  عرض المنتجات", "admin_list_products")],
        [btn(f"{E['gear']}  تعديل منتج", "admin_edit_product")],
        [btn(f"{E['minus']}  حذف منتج", "admin_del_product")],
        [btn(f"{E['back']}  رجوع", "admin_back")],
    ]
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                          reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")


@bot.callback_query_handler(func=lambda c: c.data == "admin_add_product")
def admin_add_product(call):
    if not is_admin(call.from_user.id):
        return
    user_states[call.from_user.id] = {"step": "add_product_name"}
    bot.edit_message_text(
        f"{E['plus']}  {bold('إضافة منتج جديد')}\n\n"
        f"{E['info']} أرسل {bold('اسم المنتج')}:\n\n"
        f"{E['warn']} {italic('مثال: Telegram Premium')}",
        call.message.chat.id, call.message.message_id, parse_mode="HTML")


@bot.callback_query_handler(func=lambda c: c.data == "admin_list_products")
def admin_list_products(call):
    if not is_admin(call.from_user.id):
        return
    if not data["products"]:
        bot.answer_callback_query(call.id, "\u274c لا يوجد منتجات!", show_alert=True)
        return
    text = f"{E['box']}  {bold('قائمة المنتجات')}\n\n"
    for pid, pdata in data["products"].items():
        name = pdata.get("name", "Unknown")
        price = pdata.get("price", 0)
        duration = pdata.get("duration", "N/A")
        stock = len(get_product_stock(pid))
        sold = get_total_sold(pid)
        status = "\U0001f7e2 متاح" if pdata.get("active", True) else "\U0001f534 معطل"
        text += (
            f"{E['tag']} {bold(name)} \n"
            f"  {E['key']} ID: {code(pid)}\n"
            f"  {E['money']} السعر: {bold(currency(price))}\n"
            f"  {E['clock']} المدة: {bold(duration)}\n"
            f"  {E['box']} المخزون: {bold(str(stock))}  |  مباع: {bold(str(sold))}\n"
            f"  {E['check']} الحالة: {status}\n\n"
        )
    buttons = [[btn(f"{E['back']}  رجوع", "admin_products")]]
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                          reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")


@bot.callback_query_handler(func=lambda c: c.data == "admin_edit_product")
def admin_edit_product(call):
    if not is_admin(call.from_user.id):
        return
    if not data["products"]:
        bot.answer_callback_query(call.id, "\u274c لا يوجد منتجات!", show_alert=True)
        return
    buttons = []
    for pid, pdata in data["products"].items():
        name = pdata.get("name", pid)[:20]
        buttons.append([btn(f"{E['gear']}  {name}", f"admin_edit_product_{pid}")])
    buttons.append([btn(f"{E['back']}  رجوع", "admin_products")])
    text = f"{E['gear']}  {bold('اختر منتجاً لتعديله:')}"
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                          reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")


@bot.callback_query_handler(func=lambda c: c.data.startswith("admin_edit_product_"))
def admin_edit_product_menu(call):
    if not is_admin(call.from_user.id):
        return
    pid = call.data.replace("admin_edit_product_", "")
    if pid not in data["products"]:
        bot.answer_callback_query(call.id, "\u274c المنتج غير موجود!", show_alert=True)
        return
    pdata = data["products"][pid]
    text = (
        f"{E['gear']}  {bold(f'تعديل: {pdata["name"]}')}\n\n"
        f"{E['money']} السعر: {bold(currency(pdata.get('price', 0)))}\n"
        f"{E['clock']} المدة: {bold(pdata.get('duration', 'N/A'))}\n"
        f"{E['check']} الحالة: {'\U0001f7e2 متاح' if pdata.get('active', True) else '\U0001f534 معطل'}\n"
    )
    buttons = [
        [btn(f"{E['tag']}  تعديل الاسم", f"ep_name_{pid}"),
         btn(f"{E['money']}  تعديل السعر", f"ep_price_{pid}")],
        [btn(f"{E['clock']}  تعديل المدة", f"ep_dur_{pid}"),
         btn(f"{E['check']}  تبديل الحالة", f"ep_toggle_{pid}")],
        [btn(f"{E['back']}  رجوع", "admin_products")],
    ]
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                          reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")


@bot.callback_query_handler(func=lambda c: c.data.startswith("ep_toggle_"))
def admin_toggle_product(call):
    if not is_admin(call.from_user.id):
        return
    pid = call.data.replace("ep_toggle_", "")
    if pid in data["products"]:
        data["products"][pid]["active"] = not data["products"][pid].get("active", True)
        save_data(data)
        status = "\U0001f7e2 متاح" if data["products"][pid]["active"] else "\U0001f534 معطل"
        bot.answer_callback_query(call.id, f"\u2705 الحالة: {status}", show_alert=True)
        admin_edit_product_menu(call)


@bot.callback_query_handler(func=lambda c: c.data.startswith("ep_name_"))
def admin_edit_pname(call):
    if not is_admin(call.from_user.id):
        return
    pid = call.data.replace("ep_name_", "")
    user_states[call.from_user.id] = {"step": "edit_pname", "pid": pid}
    bot.edit_message_text(
        f"{E['tag']}  {bold('تعديل اسم المنتج')}\n\n"
        f"{E['info']} أرسل الاسم الجديد:",
        call.message.chat.id, call.message.message_id, parse_mode="HTML")


@bot.callback_query_handler(func=lambda c: c.data.startswith("ep_price_"))
def admin_edit_pprice(call):
    if not is_admin(call.from_user.id):
        return
    pid = call.data.replace("ep_price_", "")
    user_states[call.from_user.id] = {"step": "edit_pprice", "pid": pid}
    bot.edit_message_text(
        f"{E['money']}  {bold('تعديل سعر المنتج')}\n\n"
        f"{E['info']} أرسل السعر الجديد:\n\n"
        f"{E['warn']} {italic('مثال: 10')}",
        call.message.chat.id, call.message.message_id, parse_mode="HTML")


@bot.callback_query_handler(func=lambda c: c.data.startswith("ep_dur_"))
def admin_edit_pdur(call):
    if not is_admin(call.from_user.id):
        return
    pid = call.data.replace("ep_dur_", "")
    user_states[call.from_user.id] = {"step": "edit_pdur", "pid": pid}
    bot.edit_message_text(
        f"{E['clock']}  {bold('تعديل مدة المنتج')}\n\n"
        f"{E['info']} أرسل المدة الجديدة:\n\n"
        f"{E['warn']} {italic('مثال: 1 day, 7 days, 30 days, 1 year, lifetime')}",
        call.message.chat.id, call.message.message_id, parse_mode="HTML")


@bot.callback_query_handler(func=lambda c: c.data == "admin_del_product")
def admin_del_product(call):
    if not is_admin(call.from_user.id):
        return
    if not data["products"]:
        bot.answer_callback_query(call.id, "\u274c لا يوجد منتجات!", show_alert=True)
        return
    buttons = []
    for pid, pdata in data["products"].items():
        name = pdata.get("name", pid)[:20]
        buttons.append([btn(f"{E['minus']}  {name}", f"admin_del_product_{pid}")])
    buttons.append([btn(f"{E['back']}  رجوع", "admin_products")])
    text = f"{E['minus']}  {bold('اختر منتجاً لحذفه:')}",
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                          reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")


@bot.callback_query_handler(func=lambda c: c.data.startswith("admin_del_product_"))
def admin_confirm_del_product(call):
    if not is_admin(call.from_user.id):
        return
    pid = call.data.replace("admin_del_product_", "")
    if pid in data["products"]:
        pname = data["products"][pid].get("name", pid)
        # Remove associated keys
        keys_to_remove = [k for k, v in data["keys"].items() if v.get("product_id") == pid]
        for k in keys_to_remove:
            del data["keys"][k]
        del data["products"][pid]
        save_data(data)
        add_transaction(call.from_user.id, "delete_product", f"حذف منتج: {pname}")
        bot.answer_callback_query(call.id, f"\u2705 تم حذف {pname}", show_alert=True)
        admin_products(call)

# ═════════════════════════════════════════════════════════════════════════════════════════════════════════
#  \U0001f511  ADMIN: KEY MANAGEMENT
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════

@bot.callback_query_handler(func=lambda c: c.data == "admin_keys")
def admin_keys(call):
    if not is_admin(call.from_user.id):
        return
    available = len([k for k, v in data["keys"].items() if v.get("status") == "available"])
    sold = len([k for k, v in data["keys"].items() if v.get("status") == "sold"])
    total = len(data["keys"])
    text = (
        f"{E['key']}  {bold('إدارة المفاتيح')}\n\n"
        f"{E['stats']}  {bold('─── الإحصائيات ───')}\n"
        f"{E['key']}  الإجمالي: {bold(str(total))}\n"
        f"{E['check']}  متاح: {bold(str(available))}\n"
        f"{E['money']}  مباع: {bold(str(sold))}\n"
    )
    buttons = [
        [btn(f"{E['plus']}  إضافة مفاتيح", "admin_add_keys"),
         btn(f"{E['bolt']}  توليد تلقائي", "admin_gen_keys")],
        [btn(f"{E['eye']}  عرض المفاتيح", "admin_list_keys")],
        [btn(f"{E['recycle']}  حذف مفاتيح غير مستخدمة", "admin_clean_keys")],
        [btn(f"{E['back']}  رجوع", "admin_back")],
    ]
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                          reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")


@bot.callback_query_handler(func=lambda c: c.data == "admin_add_keys")
def admin_add_keys(call):
    if not is_admin(call.from_user.id):
        return
    if not data["products"]:
        bot.answer_callback_query(call.id, "\u274c أنشئ منتجات أولاً!", show_alert=True)
        return
    buttons = []
    for pid, pdata in data["products"].items():
        name = pdata.get("name", pid)[:20]
        buttons.append([btn(f"{E['box']}  {name}", f"admin_add_keys_{pid}")])
    buttons.append([btn(f"{E['back']}  رجوع", "admin_keys")])
    text = f"{E['plus']}  {bold('اختر المنتج لإضافة مفاتيح:')}",
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                          reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")


@bot.callback_query_handler(func=lambda c: c.data.startswith("admin_add_keys_"))
def admin_add_keys_prompt(call):
    if not is_admin(call.from_user.id):
        return
    pid = call.data.replace("admin_add_keys_", "")
    user_states[call.from_user.id] = {"step": "add_keys_input", "pid": pid}
    pname = data["products"].get(pid, {}).get("name", pid)
    bot.edit_message_text(
        f"{E['plus']}  {bold(f'إضافة مفاتيح - {pname}')}\n\n"
        f"{E['info']} أرسل المفاتيح (مفتاح واحد في كل سطر):\n\n"
        f"{E['warn']} {italic('مثال:\nKEY-ABC-123\nKEY-DEF-456\nKEY-GHI-789')}",
        call.message.chat.id, call.message.message_id, parse_mode="HTML")


@bot.callback_query_handler(func=lambda c: c.data == "admin_gen_keys")
def admin_gen_keys(call):
    if not is_admin(call.from_user.id):
        return
    if not data["products"]:
        bot.answer_callback_query(call.id, "\u274c أنشئ منتجات أولاً!", show_alert=True)
        return
    buttons = []
    for pid, pdata in data["products"].items():
        name = pdata.get("name", pid)[:20]
        buttons.append([btn(f"{E['box']}  {name}", f"admin_gen_keys_{pid}")])
    buttons.append([btn(f"{E['back']}  رجوع", "admin_keys")])
    text = f"{E['bolt']}  {bold('اختر المنتج لتوليد مفاتيح تلقائياً:')}",
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                          reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")


@bot.callback_query_handler(func=lambda c: c.data.startswith("admin_gen_keys_"))
def admin_gen_keys_prompt(call):
    if not is_admin(call.from_user.id):
        return
    pid = call.data.replace("admin_gen_keys_", "")
    user_states[call.from_user.id] = {"step": "gen_keys_count", "pid": pid}
    pname = data["products"].get(pid, {}).get("name", pid)
    bot.edit_message_text(
        f"{E['bolt']}  {bold(f'توليد مفاتيح - {pname}')}\n\n"
        f"{E['info']} أرسل {bold('عدد')} المفاتيح التي تريد توليدها:\n\n"
        f"{E['warn']} {italic('مثال: 10')}",
        call.message.chat.id, call.message.message_id, parse_mode="HTML")


@bot.callback_query_handler(func=lambda c: c.data == "admin_list_keys")
def admin_list_keys(call):
    if not is_admin(call.from_user.id):
        return
    if not data["keys"]:
        bot.answer_callback_query(call.id, "\u274c لا يوجد مفاتيح!", show_alert=True)
        return
    available = {k: v for k, v in data["keys"].items() if v.get("status") == "available"}
    text = f"{E['key']}  {bold('المفاتيح المتاحة')}  ({bold(str(len(available)))})\n\n"
    for key, kdata in list(available.items())[:30]:  # Show max 30
        pname = data["products"].get(kdata.get("product_id", ""), {}).get("name", "Unknown")
        text += f"{E['check']} {code(key)}  {E['tag']} {pname}\n"
    if len(available) > 30:
        text += f"\n{E['info']} ... و {len(available) - 30} مفتاح آخر"
    buttons = [[btn(f"{E['back']}  رجوع", "admin_keys")]]
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                          reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")


@bot.callback_query_handler(func=lambda c: c.data == "admin_clean_keys")
def admin_clean_keys(call):
    if not is_admin(call.from_user.id):
        return
    available_keys = [k for k, v in data["keys"].items() if v.get("status") == "available"]
    if not available_keys:
        bot.answer_callback_query(call.id, "\u274c لا يوجد مفاتيح متاحة للحذف!", show_alert=True)
        return
    for k in available_keys:
        del data["keys"][k]
    save_data(data)
    add_transaction(call.from_user.id, "clean_keys", f"حذف {len(available_keys)} مفتاح متاح")
    bot.answer_callback_query(call.id, f"\u2705 تم حذف {len(available_keys)} مفتاح", show_alert=True)
    admin_keys(call)

# ═════════════════════════════════════════════════════════════════════════════════════════════════════════
#  \U0001f4b0  ADMIN: BALANCE MANAGEMENT
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════

@bot.callback_query_handler(func=lambda c: c.data == "admin_balance")
def admin_balance(call):
    if not is_admin(call.from_user.id):
        return
    text = (
        f"{E['bank']}  {bold('إدارة الأرصدة')}\n\n"
        f"{E['info']} اختر عملية لإدارة الأرصدة."
    )
    buttons = [
        [btn(f"{E['plus']}  إضافة رصيد", "admin_add_bal"),
         btn(f"{E['minus']}  خصم رصيد", "admin_sub_bal")],
        [btn(f"{E['gear']}  تعيين رصيد", "admin_set_bal")],
        [btn(f"{E['eye']}  عرض أرصدة الجميع", "admin_view_bals")],
        [btn(f"{E['back']}  رجوع", "admin_back")],
    ]
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                          reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")


@bot.callback_query_handler(func=lambda c: c.data == "admin_add_bal")
def admin_add_bal(call):
    if not is_admin(call.from_user.id):
        return
    user_states[call.from_user.id] = {"step": "add_bal_uid"}
    bot.edit_message_text(
        f"{E['plus']}  {bold('إضافة رصيد')}\n\n"
        f"{E['info']} أرسل {bold('ID')} المستخدم:\n\n"
        f"{E['warn']} {italic('مثال: 123456789')}",
        call.message.chat.id, call.message.message_id, parse_mode="HTML")


@bot.callback_query_handler(func=lambda c: c.data == "admin_sub_bal")
def admin_sub_bal(call):
    if not is_admin(call.from_user.id):
        return
    user_states[call.from_user.id] = {"step": "sub_bal_uid"}
    bot.edit_message_text(
        f"{E['minus']}  {bold('خصم رصيد')}\n\n"
        f"{E['info']} أرسل {bold('ID')} المستخدم:\n\n"
        f"{E['warn']} {italic('مثال: 123456789')}",
        call.message.chat.id, call.message.message_id, parse_mode="HTML")


@bot.callback_query_handler(func=lambda c: c.data == "admin_set_bal")
def admin_set_bal(call):
    if not is_admin(call.from_user.id):
        return
    user_states[call.from_user.id] = {"step": "set_bal_uid"}
    bot.edit_message_text(
        f"{E['gear']}  {bold('تعيين رصيد')}\n\n"
        f"{E['info']} أرسل {bold('ID')} المستخدم:\n\n"
        f"{E['warn']} {italic('مثال: 123456789')}",
        call.message.chat.id, call.message.message_id, parse_mode="HTML")


@bot.callback_query_handler(func=lambda c: c.data == "admin_view_bals")
def admin_view_bals(call):
    if not is_admin(call.from_user.id):
        return
    text = f"{E['bank']}  {bold('أرصدة جميع الريسيلرات')}\n\n"
    if not data["resellers"]:
        text += f"{E['x']} لا يوجد ريسيلرات."
    else:
        sorted_r = sorted(data["resellers"].items(), key=lambda x: x[1].get("balance", 0), reverse=True)
        for i, (uid, rdata) in enumerate(sorted_r, 1):
            name = rdata.get("name", "Unknown")
            balance = rdata.get("balance", 0)
            text += f"{E['medal']} {bold(str(i))}. {bold(name)}  {E['bank']} {bold(currency(balance))}\n"
    buttons = [[btn(f"{E['back']}  رجوع", "admin_balance")]]
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                          reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")

# ═════════════════════════════════════════════════════════════════════════════════════════════════════════
#  \U0001f4ca  ADMIN: REPORTS
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════

@bot.callback_query_handler(func=lambda c: c.data == "admin_reports")
def admin_reports(call):
    if not is_admin(call.from_user.id):
        return
    total_revenue = sum(t.get("amount", 0) for t in data["transactions"] if t.get("action") == "purchase")
    total_topups = sum(t.get("amount", 0) for t in data["transactions"] if t.get("action") == "topup")
    total_keys_sold = len([t for t in data["transactions"] if t.get("action") == "purchase"])
    total_resellers = len(data["resellers"])
    total_products = len(data["products"])

    text = (
        f"{E['chart']}  {bold('التقارير والإحصائيات')}\n\n"
        f"{E['trophy']}  {bold('─── الملخص العام ───')}\n"
        f"{E['money']}  إجمالي المبيعات: {bold(currency(total_revenue))}\n"
        f"{E['bank']}  إجمالي الشحنات: {bold(currency(total_topups))}\n"
        f"{E['key']}  مفاتيح مباعة: {bold(str(total_keys_sold))}\n"
        f"{E['users']}  الريسيلرات: {bold(str(total_resellers))}\n"
        f"{E['box']}  المنتجات: {bold(str(total_products))}\n\n"
        f"{E['stats']}  {bold('─── أعلى المنتجات مبيعاً ───')}\n"
    )
    product_sales = {}
    for t in data["transactions"]:
        if t.get("action") == "purchase":
            pname = t.get("details", "Unknown")
            product_sales[pname] = product_sales.get(pname, 0) + 1
    if product_sales:
        for i, (pname, count) in enumerate(sorted(product_sales.items(), key=lambda x: x[1], reverse=True)[:5], 1):
            text += f"  {E['medal']} {bold(str(i))}. {pname}: {bold(str(count))} مفتاح\n"
    else:
        text += f"  {E['info']} لا توجد مبيعات بعد.\n"

    text += f"\n{E['stats']}  {bold('─── آخر المعاملات ───')}\n"
    recent = data["transactions"][-10:][::-1]
    if recent:
        for t in recent:
            date = t.get("date", "N/A")[:16]
            text += f"  {E['clock']} {date} | {t.get('action', '')} | {t.get('details', '')}\n"
    else:
        text += f"  {E['info']} لا توجد معاملات بعد.\n"

    buttons = [
        [btn(f"{E['eye']}  معاملات مفصلة", "admin_full_transactions")],
        [btn(f"{E['back']}  رجوع", "admin_back")],
    ]
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                          reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")


@bot.callback_query_handler(func=lambda c: c.data == "admin_full_transactions")
def admin_full_transactions(call):
    if not is_admin(call.from_user.id):
        return
    transactions = data["transactions"]
    if not transactions:
        bot.answer_callback_query(call.id, "\u274c لا توجد معاملات!", show_alert=True)
        return
    text = f"{E['chart']}  {bold('جميع المعاملات')}  ({bold(str(len(transactions)))})\n\n"
    for t in transactions[-50:][::-1]:
        date = t.get("date", "N/A")[:16]
        action = t.get("action", "")
        details = t.get("details", "")
        amount = t.get("amount", 0)
        text += f"{E['clock']} {date}\n  {E['bolt']} {action} | {details}\n  {E['money']} {currency(amount)}\n\n"
    buttons = [[btn(f"{E['back']}  رجوع", "admin_reports")]]
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                          reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")

# ═════════════════════════════════════════════════════════════════════════════════════════════════════════
#  \U0001f3ab  ADMIN: RECHARGE CODES
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════

@bot.callback_query_handler(func=lambda c: c.data == "admin_codes")
def admin_codes(call):
    if not is_admin(call.from_user.id):
        return
    active_codes = {c2: v for c2, v in data["codes"].items() if v.get("status") == "active"}
    text = (
        f"{E['ticket']}  {bold('أكواد الشحن')}\n\n"
        f"{E['info']} أكواد نشطة: {bold(str(len(active_codes)))}\n"
        f"{E['info']} الريسيلرات يمكنهم استخدام هذه الأكواد لشحن رصيدهم."
    )
    buttons = [
        [btn(f"{E['plus']}  إنشاء كود شحن", "admin_create_code")],
        [btn(f"{E['eye']}  عرض الأكواد", "admin_list_codes")],
        [btn(f"{E['recycle']}  حذف أكواد مستخدمة", "admin_clean_codes")],
        [btn(f"{E['back']}  رجوع", "admin_back")],
    ]
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                          reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")


@bot.callback_query_handler(func=lambda c: c.data == "admin_create_code")
def admin_create_code(call):
    if not is_admin(call.from_user.id):
        return
    user_states[call.from_user.id] = {"step": "create_code_amount"}
    bot.edit_message_text(
        f"{E['plus']}  {bold('إنشاء كود شحن')}\n\n"
        f"{E['info']} أرسل {bold('قيمة الكود')} (المبلغ):\n\n"
        f"{E['warn']} {italic('مثال: 50')}",
        call.message.chat.id, call.message.message_id, parse_mode="HTML")


@bot.callback_query_handler(func=lambda c: c.data == "admin_list_codes")
def admin_list_codes(call):
    if not is_admin(call.from_user.id):
        return
    if not data["codes"]:
        bot.answer_callback_query(call.id, "\u274c لا توجد أكواد!", show_alert=True)
        return
    text = f"{E['ticket']}  {bold('جميع الأكواد')}\n\n"
    for code_key, cdata in data["codes"].items():
        status = "\U0001f7e2 نشط" if cdata.get("status") == "active" else "\U0001f534 مستخدم"
        used_by = cdata.get("used_by", "N/A")
        text += (
            f"{E['ticket']} {code(code_key)}\n"
            f"  {E['money']} القيمة: {bold(currency(cdata.get('amount', 0)))}\n"
            f"  {E['check']} الحالة: {status}\n"
        )
        if cdata.get("status") == "used":
            text += f"  {E['user']} استخدمه: {code(used_by)}\n"
        text += "\n"
    buttons = [[btn(f"{E['back']}  رجوع", "admin_codes")]]
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                          reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")


@bot.callback_query_handler(func=lambda c: c.data == "admin_clean_codes")
def admin_clean_codes(call):
    if not is_admin(call.from_user.id):
        return
    used_codes = [k for k, v in data["codes"].items() if v.get("status") == "used"]
    if not used_codes:
        bot.answer_callback_query(call.id, "\u274c لا توجد أكواد مستخدمة!", show_alert=True)
        return
    for k in used_codes:
        del data["codes"][k]
    save_data(data)
    bot.answer_callback_query(call.id, f"\u2705 تم حذف {len(used_codes)} كود", show_alert=True)
    admin_codes(call)

# ═════════════════════════════════════════════════════════════════════════════════════════════════════════
#  \u2699\ufe0f  ADMIN: SETTINGS
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════

@bot.callback_query_handler(func=lambda c: c.data == "admin_settings")
def admin_settings(call):
    if not is_admin(call.from_user.id):
        return
    s = data["settings"]
    text = (
        f"{E['gear']}  {bold('إعدادات البوت')}\n\n"
        f"{E['tag']}  اسم البوت: {bold(s.get('bot_name', 'N/A'))}\n"
        f"{E['money']}  العملة: {bold(s.get('currency', '$'))}\n"
        f"{E['key']}  الحد اليومي: {bold(str(s.get('max_daily_gen', 50)))}\n"
    )
    buttons = [
        [btn(f"{E['tag']}  تغيير اسم البوت", "admin_set_botname"),
         btn(f"{E['money']}  تغيير العملة", "admin_set_currency")],
        [btn(f"{E['key']}  تغيير الحد اليومي", "admin_set_daily_limit")],
        [btn(f"{E['recycle']}  مسح جميع البيانات", "admin_reset_data")],
        [btn(f"{E['back']}  رجوع", "admin_back")],
    ]
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                          reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")


@bot.callback_query_handler(func=lambda c: c.data == "admin_set_botname")
def admin_set_botname(call):
    if not is_admin(call.from_user.id):
        return
    user_states[call.from_user.id] = {"step": "set_botname"}
    bot.edit_message_text(
        f"{E['tag']}  {bold('تغيير اسم البوت')}\n\n"
        f"{E['info']} أرسل الاسم الجديد:",
        call.message.chat.id, call.message.message_id, parse_mode="HTML")


@bot.callback_query_handler(func=lambda c: c.data == "admin_set_currency")
def admin_set_currency(call):
    if not is_admin(call.from_user.id):
        return
    user_states[call.from_user.id] = {"step": "set_currency"}
    bot.edit_message_text(
        f"{E['money']}  {bold('تغيير العملة')}\n\n"
        f"{E['info']} أرسل رمز العملة الجديد:\n\n"
        f"{E['warn']} {italic('مثال: $, \u062f.إ, \u20ac, \u00a3')}",
        call.message.chat.id, call.message.message_id, parse_mode="HTML")


@bot.callback_query_handler(func=lambda c: c.data == "admin_set_daily_limit")
def admin_set_daily_limit(call):
    if not is_admin(call.from_user.id):
        return
    user_states[call.from_user.id] = {"step": "set_daily_limit"}
    bot.edit_message_text(
        f"{E['key']}  {bold('تغيير الحد اليومي لتوليد المفاتيح')}\n\n"
        f"{E['info']} أرسل الرقم الجديد:\n\n"
        f"{E['warn']} {italic('مثال: 100')}",
        call.message.chat.id, call.message.message_id, parse_mode="HTML")


@bot.callback_query_handler(func=lambda c: c.data == "admin_reset_data")
def admin_reset_data(call):
    global data
    if not is_admin(call.from_user.id):
        return
    # Keep admins, reset everything else
    admins_backup = data["admins"]
    data = {
        "admins": admins_backup,
        "resellers": {},
        "products": {},
        "keys": {},
        "transactions": [],
        "settings": data["settings"],
        "bans": {},
        "codes": {},
    }
    save_data(data)
    bot.answer_callback_query(call.id, "\u2705 تم مسح جميع البيانات!", show_alert=True)
    show_admin_panel(call.message)

# ═════════════════════════════════════════════════════════════════════════════════════════════════════════
#  \U0001f6e1  ADMIN: BANS
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════

@bot.callback_query_handler(func=lambda c: c.data == "admin_bans")
def admin_bans(call):
    if not is_admin(call.from_user.id):
        return
    text = (
        f"{E['shield']}  {bold('الحظر والطرد')}\n\n"
        f"{E['info']} إدارة حظر المستخدمين من البوت."
    )
    buttons = [
        [btn(f"{E['lock']}  حظر مستخدم", "admin_ban_user"),
         btn(f"{E['key']}  فك حظر", "admin_unban_user")],
        [btn(f"{E['eye']}  عرض المحظورين", "admin_list_bans")],
        [btn(f"{E['back']}  رجوع", "admin_back")],
    ]
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                          reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")


@bot.callback_query_handler(func=lambda c: c.data == "admin_ban_user")
def admin_ban_user(call):
    if not is_admin(call.from_user.id):
        return
    user_states[call.from_user.id] = {"step": "ban_uid"}
    bot.edit_message_text(
        f"{E['lock']}  {bold('حظر مستخدم')}\n\n"
        f"{E['info']} أرسل {bold('ID')} المستخدم المراد حظره:\n\n"
        f"{E['warn']} {italic('مثال: 123456789')}",
        call.message.chat.id, call.message.message_id, parse_mode="HTML")


@bot.callback_query_handler(func=lambda c: c.data == "admin_unban_user")
def admin_unban_user(call):
    if not is_admin(call.from_user.id):
        return
    user_states[call.from_user.id] = {"step": "unban_uid"}
    bot.edit_message_text(
        f"{E['key']}  {bold('فك حظر مستخدم')}\n\n"
        f"{E['info']} أرسل {bold('ID')} المستخدم:\n\n"
        f"{E['warn']} {italic('مثال: 123456789')}",
        call.message.chat.id, call.message.message_id, parse_mode="HTML")


@bot.callback_query_handler(func=lambda c: c.data == "admin_list_bans")
def admin_list_bans(call):
    if not is_admin(call.from_user.id):
        return
    if not data["bans"]:
        bot.answer_callback_query(call.id, "\u274c لا يوجد محظورين!", show_alert=True)
        return
    text = f"{E['lock']}  {bold('قائمة المحظورين')}\n\n"
    for uid, bdata in data["bans"].items():
        reason = bdata.get("reason", "غير محدد")
        text += f"{E['x']} {code(uid)} - {reason}\n"
    buttons = [[btn(f"{E['back']}  رجوع", "admin_bans")]]
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                          reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")

# ═════════════════════════════════════════════════════════════════════════════════════════════════════════
#  \U0001f527  ADMIN: TOOLS
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════

@bot.callback_query_handler(func=lambda c: c.data == "admin_tools")
def admin_tools(call):
    if not is_admin(call.from_user.id):
        return
    text = (
        f"{E['tool']}  {bold('أدوات متقدمة')}\n\n"
        f"{E['info']} أدوات إضافية لإدارة البوت."
    )
    buttons = [
        [btn(f"{E['bell']}  إرسال إشعار للجميع", "admin_broadcast")],
        [btn(f"{E['recycle']}  تصدير البيانات", "admin_export")],
        [btn(f"{E['gear']}  إعدادات عامة", "admin_settings")],
        [btn(f"{E['back']}  رجوع", "admin_back")],
    ]
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                          reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")


@bot.callback_query_handler(func=lambda c: c.data == "admin_broadcast")
def admin_broadcast(call):
    if not is_admin(call.from_user.id):
        return
    user_states[call.from_user.id] = {"step": "broadcast_msg"}
    bot.edit_message_text(
        f"{E['bell']}  {bold('إرسال إشعار للجميع')}\n\n"
        f"{E['info']} أرسل الرسالة التي تريد بثها لجميع الريسيلرات:\n\n"
        f"{E['warn']} {italic('سيتم إرسالها لجميع الريسيلرات النشطين.')}",
        call.message.chat.id, call.message.message_id, parse_mode="HTML")


@bot.callback_query_handler(func=lambda c: c.data == "admin_export")
def admin_export(call):
    if not is_admin(call.from_user.id):
        return
    export_file = "reseller_export.json"
    with open(export_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    with open(export_file, "rb") as f:
        bot.send_document(call.message.chat.id, f,
                          caption=f"{E['recycle']}  {bold('تصدير البيانات')}\n\n"
                                  f"{E['check']} تم تصدير جميع بيانات البوت بنجاح.",
                          parse_mode="HTML")
    os.remove(export_file)

# ═════════════════════════════════════════════════════════════════════════════════════════════════════════
#  \U0001f3ea  RESELLER: SHOP
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════

@bot.callback_query_handler(func=lambda c: c.data == "reseller_shop")
def reseller_shop(call):
    uid = str(call.from_user.id)
    if not is_reseller(call.from_user.id) and not is_admin(call.from_user.id):
        return
    active_products = {k: v for k, v in data["products"].items() if v.get("active", True)}
    if not active_products:
        bot.edit_message_text(
            f"{E['store']}  {bold('المتجر')}\n\n"
            f"{E['info']} لا توجد منتجات متاحة حالياً.\n"
            f"{E['warn']} تواصل مع الإدارة.",
            call.message.chat.id, call.message.message_id, parse_mode="HTML")
        return

    balance = get_balance(call.from_user.id)
    text = (
        f"{E['store']}  {bold('المتجر')}\n"
        f"{E['bank']}  رصيدك: {bold(currency(balance))}\n\n"
    )
    buttons = []
    for pid, pdata in active_products.items():
        name = pdata.get("name", "Unknown")
        price = pdata.get("price", 0)
        duration = pdata.get("duration", "N/A")
        stock = len(get_product_stock(pid))
        can_afford = balance >= price and stock > 0
        label = f"{E['tag']} {name}\n{E['money']} {currency(price)} | {E['clock']} {duration} | {E['box']} {stock}"
        if not can_afford:
            label = f"\U0001f512 {name} (رصيد غير كافٍ)" if stock > 0 else f"\U0001f534 {name} (نفذ المخزون)"
        buttons.append([btn(label, f"buy_{pid}")])
    buttons.append([btn(f"{E['back']}  رجوع", "reseller_back")])
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                          reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")


@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_"))
def reseller_buy(call):
    uid = str(call.from_user.id)
    pid = call.data.replace("buy_", "")

    if pid not in data["products"]:
        bot.answer_callback_query(call.id, "\u274c المنتج غير موجود!", show_alert=True)
        return

    pdata = data["products"][pid]
    if not pdata.get("active", True):
        bot.answer_callback_query(call.id, "\u274c هذا المنتج غير متاح!", show_alert=True)
        return

    price = pdata.get("price", 0)
    balance = get_balance(call.from_user.id)

    if balance < price:
        bot.answer_callback_query(call.id, f"\u274c رصيدك غير كافٍ! تحتاج {currency(price)}", show_alert=True)
        return

    # Check daily limit
    rdata = data["resellers"].get(uid, {})
    today_str = datetime.now().strftime("%Y-%m-%d")
    if rdata.get("last_gen_date") != today_str:
        rdata["today_generated"] = 0
        rdata["last_gen_date"] = today_str
    daily_limit = rdata.get("daily_limit", data["settings"]["max_daily_gen"])
    if rdata.get("today_generated", 0) >= daily_limit:
        bot.answer_callback_query(call.id, f"\u274c وصلت للحد اليومي ({daily_limit})!", show_alert=True)
        return

    # Get available key
    stock = get_product_stock(pid)
    if not stock:
        bot.answer_callback_query(call.id, "\u274c نفذ المخزون!", show_alert=True)
        return

    key = stock[0]
    data["keys"][key]["status"] = "sold"
    data["keys"][key]["sold_to"] = uid
    data["keys"][key]["sold_date"] = datetime.now().isoformat()

    new_balance = sub_balance(call.from_user.id, price)
    rdata["today_generated"] = rdata.get("today_generated", 0) + 1
    data["resellers"][uid] = rdata

    add_transaction(call.from_user.id, "purchase", f"شراء {pdata['name']}", price)
    save_data(data)

    # Send key to user
    text = (
        f"{E['sparkles']}{'━' * 30}{E['sparkles']}\n"
        f"{E['check']}  {bold('تم الشراء بنجاح!')}\n"
        f"{E['sparkles']}{'━' * 30}{E['sparkles']}\n\n"
        f"{E['tag']}  المنتج: {bold(pdata['name'])}\n"
        f"{E['clock']}  المدة: {bold(pdata.get('duration', 'N/A'))}\n"
        f"{E['money']}  السعر: {bold(currency(price))}\n"
        f"{E['bank']}  الرصيد المتبقي: {bold(currency(new_balance))}\n\n"
        f"{E['key']}  {bold('مفتاحك:')}",
    )
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                          reply_markup=InlineKeyboardMarkup([[btn(f"{E['store']}  المتجر", "reseller_shop"),
                                                            btn(f"{E['home']}  القائمة", "reseller_back")]]),
                          parse_mode="HTML")
    bot.send_message(call.message.chat.id, f"{E['key']}  {code(key)}")

# ═════════════════════════════════════════════════════════════════════════════════════════════════════════
#  \U0001f511  RESELLER: MY KEYS
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════

@bot.callback_query_handler(func=lambda c: c.data == "reseller_my_keys")
def reseller_my_keys(call):
    uid = str(call.from_user.id)
    my_keys = {k: v for k, v in data["keys"].items() if v.get("sold_to") == uid}
    if not my_keys:
        text = f"{E['key']}  {bold('مفاتيحي')}\n\n{E['info']} لم تشترِ أي مفاتيح بعد."
    else:
        text = f"{E['key']}  {bold('مفاتيحي')}  ({bold(str(len(my_keys)))})\n\n"
        for key, kdata in my_keys.items():
            pname = data["products"].get(kdata.get("product_id", ""), {}).get("name", "Unknown")
            sold_date = kdata.get("sold_date", "N/A")[:16]
            text += (
                f"{E['key']} {code(key)}\n"
                f"  {E['tag']} {pname} | {E['clock']} {sold_date}\n\n"
            )
    buttons = [[btn(f"{E['back']}  رجوع", "reseller_back")]]
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                          reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")

# ═════════════════════════════════════════════════════════════════════════════════════════════════════════
#  \U0001f4b0  RESELLER: BALANCE INFO
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════

@bot.callback_query_handler(func=lambda c: c.data == "reseller_balance_info")
def reseller_balance_info(call):
    uid = call.from_user.id
    balance = get_balance(uid)
    transactions = [t for t in data["transactions"] if t.get("user_id") == str(uid)]
    total_spent = sum(t.get("amount", 0) for t in transactions if t.get("action") == "purchase")
    total_topup = sum(t.get("amount", 0) for t in transactions if t.get("action") == "topup")

    text = (
        f"{E['bank']}  {bold('معلومات الرصيد')}\n\n"
        f"{E['money']}  {bold('الرصيد الحالي:')} {bold(currency(balance))}\n\n"
        f"{E['stats']}  {bold('─── الملخص ───')}\n"
        f"{E['plus']}  إجمالي الشحن: {bold(currency(total_topup))}\n"
        f"{E['minus']}  إجمالي المشتريات: {bold(currency(total_spent))}\n"
        f"{E['chart']}  عدد المعاملات: {bold(str(len(transactions)))}\n"
    )
    buttons = [[btn(f"{E['back']}  رجوع", "reseller_back")]]
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                          reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")

# ═════════════════════════════════════════════════════════════════════════════════════════════════════════
#  \U0001f3ab  RESELLER: RECHARGE
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════

@bot.callback_query_handler(func=lambda c: c.data == "reseller_recharge")
def reseller_recharge(call):
    uid = str(call.from_user.id)
    if not is_reseller(call.from_user.id) and not is_admin(call.from_user.id):
        return
    text = (
        f"{E['ticket']}  {bold('شحن الرصيد')}\n\n"
        f"{E['bank']}  رصيدك الحالي: {bold(currency(get_balance(call.from_user.id)))}\n\n"
        f"{E['info']} اختر طريقة الشحن:"
    )
    buttons = [
        [btn(f"{E['ticket']}  استخدم كود شحن", "reseller_use_code")],
        [btn(f"{E['back']}  رجوع", "reseller_back")],
    ]
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                          reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")


@bot.callback_query_handler(func=lambda c: c.data == "reseller_use_code")
def reseller_use_code(call):
    if not is_reseller(call.from_user.id) and not is_admin(call.from_user.id):
        return
    user_states[call.from_user.id] = {"step": "use_recharge_code"}
    bot.edit_message_text(
        f"{E['ticket']}  {bold('استخدام كود شحن')}\n\n"
        f"{E['info']} أرسل كود الشحن:\n\n"
        f"{E['warn']} {italic('مثال: MESTRAX-ABCD-1234')}",
        call.message.chat.id, call.message.message_id, parse_mode="HTML")

# ═════════════════════════════════════════════════════════════════════════════════════════════════════════
#  \U0001f4ca  RESELLER: STATS
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════

@bot.callback_query_handler(func=lambda c: c.data == "reseller_stats")
def reseller_stats(call):
    uid = str(call.from_user.id)
    transactions = [t for t in data["transactions"] if t.get("user_id") == uid]
    purchases = [t for t in transactions if t.get("action") == "purchase"]
    my_keys = [k for k, v in data["keys"].items() if v.get("sold_to") == uid]
    total_spent = sum(t.get("amount", 0) for t in purchases)

    text = (
        f"{E['chart']}  {bold('تقاريري')}\n\n"
        f"{E['stats']}  {bold('─── إحصائياتك ───')}\n"
        f"{E['key']}  المفاتيح المشتراة: {bold(str(len(my_keys)))}\n"
        f"{E['money']}  إجمالي الإنفاق: {bold(currency(total_spent))}\n"
        f"{E['chart']}  عدد المعاملات: {bold(str(len(transactions)))}\n\n"
    )
    if purchases:
        product_counts = {}
        for t in purchases:
            pname = t.get("details", "Unknown")
            product_counts[pname] = product_counts.get(pname, 0) + 1
        text += f"\n{E['box']}  {bold('─── المنتجات المشتراة ───')}\n"
        for pname, count in sorted(product_counts.items(), key=lambda x: x[1], reverse=True):
            text += f"  {E['tag']} {pname}: {bold(str(count))} مفتاح\n"

    buttons = [[btn(f"{E['back']}  رجوع", "reseller_back")]]
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                          reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")

# ═════════════════════════════════════════════════════════════════════════════════════════════════════════
#  \U0001f464  RESELLER: PROFILE
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════

@bot.callback_query_handler(func=lambda c: c.data == "reseller_profile")
def reseller_profile(call):
    uid = str(call.from_user.id)
    rdata = data["resellers"].get(uid, {})
    name = rdata.get("name", "Reseller")
    level = rdata.get("level", "\u26aa سيلفر")
    balance = get_balance(call.from_user.id)
    created = rdata.get("created", "N/A")[:10]
    daily_limit = rdata.get("daily_limit", data["settings"]["max_daily_gen"])

    text = (
        f"{E['user']}  {bold('حسابي')}\n\n"
        f"{E['crown']}  الاسم: {bold(name)}\n"
        f"{E['trophy']}  المستوى: {level}\n"
        f"{E['user']}  ID: {code(uid)}\n"
        f"{E['bank']}  الرصيد: {bold(currency(balance))}\n"
        f"{E['cal']}  تاريخ الإنشاء: {created}\n"
        f"{E['key']}  الحد اليومي: {bold(str(daily_limit))}\n"
    )
    buttons = [[btn(f"{E['back']}  رجوع", "reseller_back")]]
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                          reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")

# ═════════════════════════════════════════════════════════════════════════════════════════════════════════
#  \u2139\ufe0f  RESELLER: HELP
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════

@bot.callback_query_handler(func=lambda c: c.data == "reseller_help")
def reseller_help(call):
    text = (
        f"{E['info']}  {bold('مساعدة')}\n\n"
        f"{E['store']}  {bold('─── المتجر ───')}\n"
        f"  تصفح المنتجات المتاحة واشترِ المفاتيح.\n"
        f"  سيتم خصم السعر من رصيدك تلقائياً.\n\n"
        f"{E['key']}  {bold('─── المفاتيح ───')}\n"
        f"  عرض جميع المفاتيح التي اشتريتها.\n\n"
        f"{E['ticket']}  {bold('─── الشحن ───')}\n"
        f"  استخدم أكواد الشحن لزيادة رصيدك.\n"
        f"  يمكنك الحصول على الأكواد من الإدارة.\n\n"
        f"{E['chart']}  {bold('─── التقارير ───')}\n"
        f"  عرض إحصائيات مشترياتك وإنفاقك.\n\n"
        f"{E['warn']}  {bold('─── ملاحظات ───')}\n"
        f"  • يوجد حد يومي لتوليد المفاتيح.\n"
        f"  • تأكد من رصيدك قبل الشراء.\n"
        f"  • لأي مشكلة تواصل مع الإدارة.\n"
    )
    buttons = [[btn(f"{E['back']}  رجوع", "reseller_back")]]
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                          reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")

# ═════════════════════════════════════════════════════════════════════════════════════════════════════════
#  \u2b05\ufe0f  NAVIGATION
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════

@bot.callback_query_handler(func=lambda c: c.data == "admin_back")
def admin_back(call):
    if is_admin(call.from_user.id):
        show_admin_panel(call.message)


@bot.callback_query_handler(func=lambda c: c.data == "reseller_back")
def reseller_back(call):
    if is_admin(call.from_user.id):
        show_admin_panel(call.message)
    elif is_reseller(call.from_user.id):
        show_reseller_panel(call.message)

# ═════════════════════════════════════════════════════════════════════════════════════════════════════════
#  \u2328\ufe0f  MESSAGE HANDLER (Multi-step inputs)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════

@bot.message_handler(func=lambda m: True)
def handle_text(message):
    uid = message.from_user.id
    if uid not in user_states:
        return

    state = user_states[uid]
    step = state.get("step")
    text = message.text.strip()
    msg = message

    # ─── ADD RESELLER ───
    if step == "add_reseller_id":
        try:
            target_id = int(text)
        except ValueError:
            bot.reply_to(msg, f"{E['x']} {bold('خطأ!')} أرسل رقم ID صحيح.")
            return
        if str(target_id) in data["resellers"] or str(target_id) in data["admins"]:
            bot.reply_to(msg, f"{E['x']} هذا الحساب موجود بالفعل!")
            del user_states[uid]
            return
        user_states[uid] = {"step": "add_reseller_name", "target_id": target_id}
        bot.reply_to(msg, f"{E['check']} تم تحديد ID: {code(str(target_id))}\n\n"
                           f"{E['info']} الآن أرسل {bold('اسم')} الريسيلر:")

    elif step == "add_reseller_name":
        target_id = state["target_id"]
        name = text[:50]
        data["resellers"][str(target_id)] = {
            "name": name,
            "balance": 0,
            "level": "\u26aa سيلفر",
            "created": datetime.now().isoformat(),
            "daily_limit": data["settings"]["max_daily_gen"],
            "today_generated": 0,
            "last_gen_date": "",
            "banned": False,
        }
        save_data(data)
        add_transaction(uid, "add_reseller", f"إضافة ريسيلر: {name} ({target_id})")
        del user_states[uid]
        bot.reply_to(msg, f"{E['check']}  {bold('تم إضافة الريسيلر بنجاح!')}\n\n"
                           f"{E['user']} الاسم: {bold(name)}\n"
                           f"{E['user']} ID: {code(str(target_id))}\n"
                           f"{E['bank']} الرصيد: {bold(currency(0))}\n"
                           f"{E['trophy']} المستوى: \u26aa سيلفر")

    # ─── EDIT BALANCE (from admin panel) ───
    elif step == "edit_bal_uid":
        try:
            target_id = int(text)
        except ValueError:
            bot.reply_to(msg, f"{E['x']} أرسل رقم ID صحيح.")
            return
        if str(target_id) not in data["resellers"]:
            bot.reply_to(msg, f"{E['x']} هذا الريسيلر غير موجود!")
            del user_states[uid]
            return
        user_states[uid] = {"step": "edit_bal_amount", "target_id": target_id}
        current = get_balance(target_id)
        bot.reply_to(msg, f"{E['check']} الرصيد الحالي: {bold(currency(current))}\n\n"
                           f"{E['info']} أرسل {bold('المبلغ')} لإضافته (استخدم رقم سالب للخصم):\n\n"
                           f"{E['warn']} {italic('مثال: 50 (إضافة) أو -20 (خصم)')}")

    elif step == "edit_bal_amount":
        try:
            amount = float(text)
        except ValueError:
            bot.reply_to(msg, f"{E['x']} أرسل رقم صحيح!")
            return
        target_id = state["target_id"]
        new_bal = add_balance(target_id, amount)
        action_type = "إضافة" if amount >= 0 else "خصم"
        add_transaction(uid, "balance_edit", f"{action_type} رصيد {data['resellers'][str(target_id)]['name']}", abs(amount))
        del user_states[uid]
        bot.reply_to(msg, f"{E['check']}  {bold('تم تعديل الرصيد!')}\n\n"
                           f"{E['user']} الريسيلر: {bold(data['resellers'][str(target_id)]['name'])}\n"
                           f"{E['money']} {action_type}: {currency(abs(amount))}\n"
                           f"{E['bank']} الرصيد الجديد: {bold(currency(new_bal))}")

    # ─── EDIT LEVEL ───
    elif step == "edit_level_uid":
        try:
            target_id = int(text)
        except ValueError:
            bot.reply_to(msg, f"{E['x']} أرسل رقم ID صحيح.")
            return
        if str(target_id) not in data["resellers"]:
            bot.reply_to(msg, f"{E['x']} هذا الريسيلر غير موجود!")
            del user_states[uid]
            return
        user_states[uid] = {"step": "edit_level_val", "target_id": target_id}
        bot.reply_to(msg, f"{E['check']} اختر المستوى:\n\n"
                           f"{E['medal']} 1 - \u26aa سيلفر\n"
                           f"{E['medal']} 2 - \U0001f4b0 جولد\n"
                           f"{E['medal']} 3 - \U0001f48e دايموند\n"
                           f"{E['medal']} 4 - {E['crown']} فيب\n\n"
                           f"{E['info']} أرسل رقم المستوى (1-4):")

    elif step == "edit_level_val":
        levels = {"1": "\u26aa سيلفر", "2": "\U0001f4b0 جولد", "3": "\U0001f48e دايموند", "4": f"{E['crown']} فيب"}
        if text not in levels:
            bot.reply_to(msg, f"{E['x']} أرسل رقم من 1 إلى 4!")
            return
        target_id = state["target_id"]
        data["resellers"][str(target_id)]["level"] = levels[text]
        save_data(data)
        add_transaction(uid, "level_edit", f"تغيير مستوى {data['resellers'][str(target_id)]['name']} إلى {levels[text]}")
        del user_states[uid]
        bot.reply_to(msg, f"{E['check']}  {bold('تم تغيير المستوى!')}\n\n"
                           f"{E['user']} الريسيلر: {bold(data['resellers'][str(target_id)]['name'])}\n"
                           f"{E['trophy']} المستوى الجديد: {bold(levels[text])}")

    # ─── DELETE RESELLER ───
    elif step == "del_reseller_uid":
        try:
            target_id = int(text)
        except ValueError:
            bot.reply_to(msg, f"{E['x']} أرسل رقم ID صحيح.")
            return
        if str(target_id) not in data["resellers"]:
            bot.reply_to(msg, f"{E['x']} هذا الريسيلر غير موجود!")
            del user_states[uid]
            return
        rname = data["resellers"][str(target_id)].get("name", "Unknown")
        del data["resellers"][str(target_id)]
        save_data(data)
        add_transaction(uid, "delete_reseller", f"حذف ريسيلر: {rname} ({target_id})")
        del user_states[uid]
        bot.reply_to(msg, f"{E['check']}  {bold('تم حذف الريسيلر!')}\n\n"
                           f"{E['user']} الاسم: {bold(rname)}\n"
                           f"{E['user']} ID: {code(str(target_id))}")

    # ─── ADD PRODUCT ───
    elif step == "add_product_name":
        user_states[uid] = {"step": "add_product_price", "pname": text[:50]}
        bot.reply_to(msg, f"{E['check']} اسم المنتج: {bold(text[:50])}\n\n"
                           f"{E['info']} أرسل {bold('السعر')}:\n\n"
                           f"{E['warn']} {italic('مثال: 10')}")

    elif step == "add_product_price":
        try:
            price = float(text)
        except ValueError:
            bot.reply_to(msg, f"{E['x']} أرسل رقم صحيح!")
            return
        user_states[uid]["pprice"] = price
        user_states[uid]["step"] = "add_product_duration"
        bot.reply_to(msg, f"{E['check']} السعر: {bold(currency(price))}\n\n"
                           f"{E['info']} أرسل {bold('المدة')}:\n\n"
                           f"{E['warn']} {italic('مثال: 1 day, 7 days, 30 days, 1 year, lifetime')}")

    elif step == "add_product_duration":
        pname = state["pname"]
        pprice = state["pprice"]
        duration = text[:30]
        pid = str(len(data["products"]) + 1)
        data["products"][pid] = {
            "name": pname,
            "price": pprice,
            "duration": duration,
            "active": True,
            "created": datetime.now().isoformat(),
        }
        save_data(data)
        add_transaction(uid, "add_product", f"إضافة منتج: {pname} ({currency(pprice)} - {duration})")
        del user_states[uid]
        bot.reply_to(msg, f"{E['check']}  {bold('تم إضافة المنتج!')}\n\n"
                           f"{E['tag']} الاسم: {bold(pname)}\n"
                           f"{E['money']} السعر: {bold(currency(pprice))}\n"
                           f"{E['clock']} المدة: {bold(duration)}\n"
                           f"{E['key']} ID: {code(pid)}")

    # ─── EDIT PRODUCT NAME ───
    elif step == "edit_pname":
        pid = state["pid"]
        if pid in data["products"]:
            old_name = data["products"][pid]["name"]
            data["products"][pid]["name"] = text[:50]
            save_data(data)
            add_transaction(uid, "edit_product", f"تعديل اسم منتج: {old_name} → {text[:50]}")
            del user_states[uid]
            bot.reply_to(msg, f"{E['check']} تم تغيير الاسم إلى: {bold(text[:50])}")

    # ─── EDIT PRODUCT PRICE ───
    elif step == "edit_pprice":
        try:
            price = float(text)
        except ValueError:
            bot.reply_to(msg, f"{E['x']} أرسل رقم صحيح!")
            return
        pid = state["pid"]
        if pid in data["products"]:
            data["products"][pid]["price"] = price
            save_data(data)
            add_transaction(uid, "edit_product", f"تعديل سعر منتج: {data['products'][pid]['name']} → {currency(price)}")
            del user_states[uid]
            bot.reply_to(msg, f"{E['check']} تم تغيير السعر إلى: {bold(currency(price))}")

    # ─── EDIT PRODUCT DURATION ───
    elif step == "edit_pdur":
        pid = state["pid"]
        if pid in data["products"]:
            data["products"][pid]["duration"] = text[:30]
            save_data(data)
            add_transaction(uid, "edit_product", f"تعديل مدة منتج: {data['products'][pid]['name']} → {text[:30]}")
            del user_states[uid]
            bot.reply_to(msg, f"{E['check']} تم تغيير المدة إلى: {bold(text[:30])}")

    # ─── ADD KEYS (MANUAL) ───
    elif step == "add_keys_input":
        pid = state["pid"]
        keys = [k.strip() for k in text.split("\n") if k.strip()]
        if not keys:
            bot.reply_to(msg, f"{E['x']} لم يتم إرسال أي مفاتيح!")
            return
        added = 0
        for key in keys:
            if key not in data["keys"]:
                data["keys"][key] = {
                    "product_id": pid,
                    "status": "available",
                    "added_by": str(uid),
                    "added_date": datetime.now().isoformat(),
                }
                added += 1
        save_data(data)
        add_transaction(uid, "add_keys", f"إضافة {added} مفتاح لـ {data['products'].get(pid, {}).get('name', pid)}")
        del user_states[uid]
        bot.reply_to(msg, f"{E['check']}  {bold('تم إضافة المفاتيح!')}\n\n"
                           f"{E['plus']} تمت إضافة: {bold(str(added))} مفتاح\n"
                           f"{E['x']} مكررة/فارغة: {bold(str(len(keys) - added))}\n"
                           f"{E['box']} المخزون الجديد: {bold(str(len(get_product_stock(pid))))}")

    # ─── GENERATE KEYS (AUTO) ───
    elif step == "gen_keys_count":
        try:
            count = int(text)
            if count < 1 or count > 1000:
                raise ValueError
        except ValueError:
            bot.reply_to(msg, f"{E['x']} أرسل رقم من 1 إلى 1000!")
            return
        pid = state["pid"]
        added = 0
        for _ in range(count):
            key = gen_key()
            while key in data["keys"]:
                key = gen_key()
            data["keys"][key] = {
                "product_id": pid,
                "status": "available",
                "added_by": str(uid),
                "added_date": datetime.now().isoformat(),
            }
            added += 1
        save_data(data)
        add_transaction(uid, "gen_keys", f"توليد {added} مفتاح لـ {data['products'].get(pid, {}).get('name', pid)}")
        del user_states[uid]
        bot.reply_to(msg, f"{E['bolt']}  {bold('تم توليد المفاتيح!')}\n\n"
                           f"{E['plus']} تم التوليد: {bold(str(added))} مفتاح\n"
                           f"{E['box']} المخزون الجديد: {bold(str(len(get_product_stock(pid))))}")

    # ─── ADD BALANCE ───
    elif step == "add_bal_uid":
        try:
            target_id = int(text)
        except ValueError:
            bot.reply_to(msg, f"{E['x']} أرسل رقم ID صحيح.")
            return
        if str(target_id) not in data["resellers"]:
            bot.reply_to(msg, f"{E['x']} هذا الريسيلر غير موجود!")
            del user_states[uid]
            return
        user_states[uid] = {"step": "add_bal_amount", "target_id": target_id}
        bot.reply_to(msg, f"{E['check']} الريسيلر: {bold(data['resellers'][str(target_id)]['name'])}\n\n"
                           f"{E['info']} أرسل {bold('المبلغ')} لإضافته:")

    elif step == "add_bal_amount":
        try:
            amount = float(text)
        except ValueError:
            bot.reply_to(msg, f"{E['x']} أرسل رقم صحيح!")
            return
        target_id = state["target_id"]
        new_bal = add_balance(target_id, amount)
        add_transaction(uid, "topup", f"شحن رصيد {data['resellers'][str(target_id)]['name']}", amount)
        del user_states[uid]
        bot.reply_to(msg, f"{E['check']}  {bold('تم الشحن!')}\n\n"
                           f"{E['user']} الريسيلر: {bold(data['resellers'][str(target_id)]['name'])}\n"
                           f"{E['plus']} المبلغ: {bold(currency(amount))}\n"
                           f"{E['bank']} الرصيد الجديد: {bold(currency(new_bal))}")

    # ─── SUB BALANCE ───
    elif step == "sub_bal_uid":
        try:
            target_id = int(text)
        except ValueError:
            bot.reply_to(msg, f"{E['x']} أرسل رقم ID صحيح.")
            return
        if str(target_id) not in data["resellers"]:
            bot.reply_to(msg, f"{E['x']} هذا الريسيلر غير موجود!")
            del user_states[uid]
            return
        user_states[uid] = {"step": "sub_bal_amount", "target_id": target_id}
        bot.reply_to(msg, f"{E['check']} الريسيلر: {bold(data['resellers'][str(target_id)]['name'])}\n\n"
                           f"{E['info']} أرسل {bold('المبلغ')} لخصمه:")

    elif step == "sub_bal_amount":
        try:
            amount = float(text)
        except ValueError:
            bot.reply_to(msg, f"{E['x']} أرسل رقم صحيح!")
            return
        target_id = state["target_id"]
        new_bal = sub_balance(target_id, amount)
        add_transaction(uid, "deduct", f"خصم رصيد {data['resellers'][str(target_id)]['name']}", amount)
        del user_states[uid]
        bot.reply_to(msg, f"{E['check']}  {bold('تم الخصم!')}\n\n"
                           f"{E['user']} الريسيلر: {bold(data['resellers'][str(target_id)]['name'])}\n"
                           f"{E['minus']} المبلغ: {bold(currency(amount))}\n"
                           f"{E['bank']} الرصيد المتبقي: {bold(currency(new_bal))}")

    # ─── SET BALANCE ───
    elif step == "set_bal_uid":
        try:
            target_id = int(text)
        except ValueError:
            bot.reply_to(msg, f"{E['x']} أرسل رقم ID صحيح.")
            return
        if str(target_id) not in data["resellers"]:
            bot.reply_to(msg, f"{E['x']} هذا الريسيلر غير موجود!")
            del user_states[uid]
            return
        user_states[uid] = {"step": "set_bal_amount", "target_id": target_id}
        current = get_balance(target_id)
        bot.reply_to(msg, f"{E['check']} الرصيد الحالي: {bold(currency(current))}\n\n"
                           f"{E['info']} أرسل {bold('الرصيد الجديد')}:")

    elif step == "set_bal_amount":
        try:
            amount = float(text)
        except ValueError:
            bot.reply_to(msg, f"{E['x']} أرسل رقم صحيح!")
            return
        target_id = state["target_id"]
        set_balance(target_id, amount)
        add_transaction(uid, "set_balance", f"تعيين رصيد {data['resellers'][str(target_id)]['name']} إلى {currency(amount)}", amount)
        del user_states[uid]
        bot.reply_to(msg, f"{E['check']}  {bold('تم تعيين الرصيد!')}\n\n"
                           f"{E['user']} الريسيلر: {bold(data['resellers'][str(target_id)]['name'])}\n"
                           f"{E['bank']} الرصيد الجديد: {bold(currency(amount))}")

    # ─── CREATE RECHARGE CODE ───
    elif step == "create_code_amount":
        try:
            amount = float(text)
        except ValueError:
            bot.reply_to(msg, f"{E['x']} أرسل رقم صحيح!")
            return
        code_key = gen_key("CODE", 8)
        while code_key in data["codes"]:
            code_key = gen_key("CODE", 8)
        data["codes"][code_key] = {
            "amount": amount,
            "status": "active",
            "created_by": str(uid),
            "created_date": datetime.now().isoformat(),
        }
        save_data(data)
        add_transaction(uid, "create_code", f"إنشاء كود شحن: {currency(amount)}")
        del user_states[uid]
        bot.reply_to(msg, f"{E['check']}  {bold('تم إنشاء كود الشحن!')}\n\n"
                           f"{E['ticket']} الكود: {code(code_key)}\n"
                           f"{E['money']} القيمة: {bold(currency(amount))}\n\n"
                           f"{E['info']} أرسل هذا الكود للريسيلر لشحن رصيده.")

    # ─── USE RECHARGE CODE (RESELLER) ───
    elif step == "use_recharge_code":
        code_key = text.strip().upper()
        if code_key not in data["codes"]:
            bot.reply_to(msg, f"{E['x']} {bold('كود غير صالح!')}\n\n{E['warn']} تأكد من صحة الكود وحاول مرة أخرى.")
            del user_states[uid]
            return
        cdata = data["codes"][code_key]
        if cdata.get("status") != "active":
            bot.reply_to(msg, f"{E['x']} {bold('هذا الكود مستخدم بالفعل!')}")
            del user_states[uid]
            return
        cdata["status"] = "used"
        cdata["used_by"] = str(uid)
        cdata["used_date"] = datetime.now().isoformat()
        amount = cdata["amount"]
        new_bal = add_balance(uid, amount)
        save_data(data)
        add_transaction(uid, "topup", f"شحن عبر كود: {code_key}", amount)
        del user_states[uid]
        bot.reply_to(msg, f"{E['sparkles']}{'━' * 30}{E['sparkles']}\n"
                           f"{E['check']}  {bold('تم الشحن بنجاح!')}\n"
                           f"{E['sparkles']}{'━' * 30}{E['sparkles']}\n\n"
                           f"{E['plus']} المبلغ: {bold(currency(amount))}\n"
                           f"{E['bank']} رصيدك الجديد: {bold(currency(new_bal))}")

    # ─── BAN USER ───
    elif step == "ban_uid":
        try:
            target_id = int(text)
        except ValueError:
            bot.reply_to(msg, f"{E['x']} أرسل رقم ID صحيح.")
            return
        user_states[uid] = {"step": "ban_reason", "target_id": target_id}
        bot.reply_to(msg, f"{E['check']} ID: {code(str(target_id))}\n\n"
                           f"{E['info']} أرسل {bold('سبب الحظر')}:")

    elif step == "ban_reason":
        target_id = state["target_id"]
        data["bans"][str(target_id)] = {
            "reason": text[:100],
            "banned_by": str(uid),
            "date": datetime.now().isoformat(),
        }
        # Also remove from resellers if exists
        if str(target_id) in data["resellers"]:
            data["resellers"][str(target_id)]["banned"] = True
        save_data(data)
        add_transaction(uid, "ban", f"حظر {target_id}: {text[:100]}")
        del user_states[uid]
        bot.reply_to(msg, f"{E['lock']}  {bold('تم حظر المستخدم!')}\n\n"
                           f"{E['user']} ID: {code(str(target_id))}\n"
                           f"{E['warn']} السبب: {text[:100]}")

    # ─── UNBAN USER ───
    elif step == "unban_uid":
        try:
            target_id = int(text)
        except ValueError:
            bot.reply_to(msg, f"{E['x']} أرسل رقم ID صحيح.")
            return
        if str(target_id) in data["bans"]:
            del data["bans"][str(target_id)]
            if str(target_id) in data["resellers"]:
                data["resellers"][str(target_id)]["banned"] = False
            save_data(data)
            add_transaction(uid, "unban", f"فك حظر {target_id}")
            del user_states[uid]
            bot.reply_to(msg, f"{E['check']}  {bold('تم فك الحظر!')}\n\n"
                               f"{E['user']} ID: {code(str(target_id))}")
        else:
            bot.reply_to(msg, f"{E['x']} هذا المستخدم غير محظور!")
            del user_states[uid]

    # ─── SETTINGS: BOT NAME ───
    elif step == "set_botname":
        data["settings"]["bot_name"] = text[:50]
        save_data(data)
        del user_states[uid]
        bot.reply_to(msg, f"{E['check']} تم تغيير اسم البوت إلى: {bold(text[:50])}")

    # ─── SETTINGS: CURRENCY ───
    elif step == "set_currency":
        data["settings"]["currency"] = text[:5]
        save_data(data)
        del user_states[uid]
        bot.reply_to(msg, f"{E['check']} تم تغيير العملة إلى: {bold(text[:5])}")

    # ─── SETTINGS: DAILY LIMIT ───
    elif step == "set_daily_limit":
        try:
            limit = int(text)
            if limit < 1:
                raise ValueError
        except ValueError:
            bot.reply_to(msg, f"{E['x']} أرسل رقم صحيح أكبر من 0!")
            return
        data["settings"]["max_daily_gen"] = limit
        save_data(data)
        del user_states[uid]
        bot.reply_to(msg, f"{E['check']} تم تغيير الحد اليومي إلى: {bold(str(limit))}")

    # ─── BROADCAST ───
    elif step == "broadcast_msg":
        sent = 0
        failed = 0
        for rid in data["resellers"]:
            try:
                bot.send_message(int(rid),
                    f"{E['bell']}  {bold('إشعار من الإدارة')}\n\n{text}",
                    parse_mode="HTML")
                sent += 1
            except Exception:
                failed += 1
        del user_states[uid]
        bot.reply_to(msg, f"{E['bell']}  {bold('تم بث الإشعار!')}\n\n"
                           f"{E['check']} تم الإرسال: {bold(str(sent))}\n"
                           f"{E['x']} فشل: {bold(str(failed))}")


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════
#  \U0001f680  START BOT
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════

# ═════════════════════════════════════════════════════════════════════════════════════════════════════════
#  ⚙️  FLASK WEBHOOK ROUTES
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════

@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    if request.headers.get("content-type") == "application/json":
        json_str = request.get_data(as_text=True)
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return "", 200
    return "", 403


@app.route("/")
def index():
    n_resellers = len(data.get('resellers', {}))
    n_products = len(data.get('products', {}))
    n_keys = len([k for k, v in data.get('keys', {}).items() if v.get('status') == 'available'])
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>MESTRAX RESELLER BOT</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0a0a1a 0%, #1a0a2e 50%, #0a0a1a 100%);
            min-height: 100vh; display: flex; align-items: center; justify-content: center;
            color: #fff;
        }}
        .container {{ text-align: center; padding: 40px; }}
        .logo {{ font-size: 48px; margin-bottom: 10px; }}
        h1 {{ 
            font-size: 2em; 
            background: linear-gradient(90deg, #a855f7, #6366f1, #8b5cf6);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            margin-bottom: 15px;
        }}
        .status {{ 
            display: inline-block; padding: 8px 24px; border-radius: 20px; 
            background: rgba(34, 197, 94, 0.15); border: 1px solid rgba(34, 197, 94, 0.3);
            color: #22c55e; font-size: 14px; margin-bottom: 20px;
        }}
        .stats {{ 
            display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; 
            max-width: 500px; margin: 20px auto;
        }}
        .stat-card {{ 
            background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);
            border-radius: 12px; padding: 15px; backdrop-filter: blur(10px);
        }}
        .stat-card .num {{ font-size: 1.5em; font-weight: bold; color: #a855f7; }}
        .stat-card .label {{ font-size: 0.8em; color: #888; margin-top: 5px; }}
        .footer {{ color: #555; font-size: 12px; margin-top: 30px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">👑</div>
        <h1>MESTRAX RESELLER BOT</h1>
        <div class="status">● Bot is Online</div>
        <div class="stats">
            <div class="stat-card">
                <div class="num">{n_resellers}</div>
                <div class="label">Resellers</div>
            </div>
            <div class="stat-card">
                <div class="num">{n_products}</div>
                <div class="label">Products</div>
            </div>
            <div class="stat-card">
                <div class="num">{n_keys}</div>
                <div class="label">Available Keys</div>
            </div>
        </div>
        <div class="footer">Powered by MESTRAX | Render Hosted</div>
    </div>
</body>
</html>"""


@app.route("/health")
def health():
    return {"status": "online", "timestamp": datetime.now().isoformat()}, 200


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
#  ⚙️  WEBHOOK SETUP + START
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════

def setup_webhook():
    if WEBHOOK_URL:
        bot.remove_webhook()
        success = bot.set_webhook(url=WEBHOOK_URL, max_connections=100)
        if success:
            logger.info(f"[WEBHOOK] Set to: {WEBHOOK_URL}")
        else:
            logger.error("[WEBHOOK] Failed to set webhook!")
    else:
        logger.warning("[WEBHOOK] RENDER_EXTERNAL_URL not set! Using polling mode.")


scheduler.start()
logger.info("[SCHEDULER] Cron jobs started")
setup_webhook()

# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
#  On Render: Start Command = gunicorn reseller_bot:app
#  Locally:   python reseller_bot.py
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("\u2b50  MESTRAX RESELLER BOT  \u2b50")
    print(f"\U0001f680  Starting on port {port}...")
    print(f"\U0001f451  Admin ID: {ADMIN_IDS}")
    if WEBHOOK_URL:
        print(f"\U0001f310  Webhook: {WEBHOOK_URL}")
    else:
        print("\u26a0\ufe0f  No RENDER_EXTERNAL_URL - running in polling mode")
    threading.Thread(target=bot.infinity_polling, daemon=True).start()
    app.run(host="0.0.0.0", port=port)
