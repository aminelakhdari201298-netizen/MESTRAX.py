# ══════════════════════════════════════════════════════════════════════════════════════════════════════════
#  ★彡 MESTRAX RESELLER BOT ★彡
# ══════════════════════════════════════════════════════════════════════════════════════════════════════════

import os
import json
import random
import string
import logging
from datetime import datetime, timedelta
from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from apscheduler.schedulers.background import BackgroundScheduler

# ═════════════════════════════════════════════════════════════════════════════════════════════════════════
#  ⚙️  CONFIGURATION & TELEGRAM PREMIUM EMOJIS
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════

BOT_TOKEN = "8955914962:AAFv9TPFzh112eJBc6Ixq4oDsYTjsb4Na8c"
ADMIN_IDS = [8254258071]
DATA_FILE = "reseller_data.json"

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL", "")
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"{RENDER_URL}{WEBHOOK_PATH}" if RENDER_URL else ""

# 🎨 تشكيلة إيموجيات تلجرام بريميوم المزخرفة (Custom Emoji IDs)
E = {
    "crown": '<tg-emoji id="5431498305881057417">👑</tg-emoji>',
    "sparkles": '<tg-emoji id="5431376020084497583">✨</tg-emoji>',
    "star": '<tg-emoji id="5431498305881057417">⭐</tg-emoji>',
    "diamond": '<tg-emoji id="5431376020084497583">💎</tg-emoji>',
    "fire": '<tg-emoji id="5431498305881057417">🔥</tg-emoji>',
    "bolt": '<tg-emoji id="5431376020084497583">⚡</tg-emoji>',
    "check": '<tg-emoji id="5431498305881057417">✅</tg-emoji>',
    "x": '<tg-emoji id="5431376020084497583">❌</tg-emoji>',
    "lock": '<tg-emoji id="5431498305881057417">🔒</tg-emoji>',
    "key": '<tg-emoji id="5431376020084497583">🔑</tg-emoji>',
    "money": '<tg-emoji id="5431498305881057417">💰</tg-emoji>',
    "bank": '<tg-emoji id="5431376020084497583">🏦</tg-emoji>',
    "ticket": '<tg-emoji id="5431498305881057417">🎫</tg-emoji>',
    "user": '<tg-emoji id="5431376020084497583">👤</tg-emoji>',
    "users": '<tg-emoji id="5431498305881057417">👥</tg-emoji>',
    "box": '<tg-emoji id="5431376020084497583">📦</tg-emoji>',
    "chart": '<tg-emoji id="5431498305881057417">📈</tg-emoji>',
    "gear": '<tg-emoji id="5431376020084497583">⚙️</tg-emoji>',
    "store": '<tg-emoji id="5431498305881057417">🏪</tg-emoji>',
    "trophy": '<tg-emoji id="5431376020084497583">🏆</tg-emoji>',
    "shield": '<tg-emoji id="5431498305881057417">🛡️</tg-emoji>',
    "bell": '<tg-emoji id="5431376020084497583">🔔</tg-emoji>',
    "bot": '<tg-emoji id="5431498305881057417">🤖</tg-emoji>',
}

# ═════════════════════════════════════════════════════════════════════════════════════════════════════════
#  💾 DATA & HELPERS
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════

def load_data():
    default = {
        "admins": {str(aid): {"name": "Owner", "created": datetime.now().isoformat()} for aid in ADMIN_IDS},
        "resellers": {},
        "products": {},
        "keys": {},
        "transactions": [],
        "settings": {"bot_name": "MESTRAX RESELLER", "currency": "$", "max_daily_gen": 50},
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

def is_admin(user_id): return str(user_id) in data.get("admins", {}) or user_id in ADMIN_IDS
def is_reseller(user_id): return str(user_id) in data.get("resellers", {})
def is_banned(user_id): return str(user_id) in data.get("bans", {})
def has_access(user_id): return is_admin(user_id) or is_reseller(user_id)

def bold(text): return f"<b>{text}</b>"
def currency(amount): return f"{amount}{data['settings']['currency']}"
def btn(text, callback_data): return InlineKeyboardButton(text, callback_data=callback_data)

def get_balance(user_id):
    uid = str(user_id)
    if uid in data["resellers"]: return data["resellers"][uid].get("balance", 0)
    if uid in data["admins"]: return data["admins"][uid].get("balance", 0)
    return 0

# ═════════════════════════════════════════════════════════════════════════════════════════════════════════
#  🤖 BOT PANELS WITH PREMIUM DESIGN
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════

@bot.message_handler(commands=['start'])
def cmd_start(message):
    uid = message.from_user.id
    uname = message.from_user.first_name or "User"

    if is_banned(uid):
        bot.reply_to(message, f"{E['lock']} {bold('حسابك محظور!')}\n\nتواصل مع الدعم الفني للمزيد من التفاصيل.")
        return

    if not has_access(uid):
        bot.reply_to(message, f"{E['shield']} {bold('وصول غير مصرح!')}\n\nعذراً {uname}، هذا البوت خاص بالريسيلرات المعينين فقط.")
        return

    if is_admin(uid):
        show_admin_panel(message)
    else:
        show_reseller_panel(message)

def show_admin_panel(message):
    uid = str(message.from_user.id)
    admin_name = data["admins"].get(uid, {}).get("name", "Owner")
    text = (
        f"{E['sparkles']} ━━━━━━━━━━━━━━━━━━ {E['sparkles']}\n"
        f"  {E['crown']} {bold('لوحة التحكم الخاصة بالحساب')} {E['crown']}\n"
        f"{E['sparkles']} ━━━━━━━━━━━━━━━━━━ {E['sparkles']}\n\n"
        f"{E['user']} مرحباً بك يا ملك: {bold(admin_name)}\n"
        f"{E['users']} عدد الموزعين: {bold(str(len(data['resellers'])))} موزع\n"
        f"{E['box']} إجمالي المنتجات: {bold(str(len(data['products'])))} منتج\n"
        f"{E['fire']} الحالة: {bold('البوت يعمل بكامل كفاءته')}\n"
    )
    buttons = [
        [btn(f"{E['users']} إدارة الموزعين", "admin_resellers"), btn(f"{E['box']} إدارة المنتجات", "admin_products")],
        [btn(f"{E['key']} إدارة المفاتيح", "admin_keys"), btn(f"{E['money']} شحن الأرصدة", "admin_balance")],
        [btn(f"{E['ticket']} أكواد الشحن", "admin_codes"), btn(f"{E['gear']} إعدادات النظام", "admin_settings")]
    ]
    bot.send_message(message.chat.id, text, reply_markup=InlineKeyboardMarkup(buttons))

def show_reseller_panel(message):
    uid = str(message.from_user.id)
    rdata = data["resellers"].get(uid, {})
    rname = rdata.get("name", "Reseller")
    balance = get_balance(int(uid))

    text = (
        f"{E['sparkles']} ━━━━━━━━━━━━━━━━━━ {E['sparkles']}\n"
        f"  {E['diamond']} {bold('لوحة الموزع المعتمد')} {E['diamond']}\n"
        f"{E['sparkles']} ━━━━━━━━━━━━━━━━━━ {E['sparkles']}\n\n"
        f"{E['user']} أهلاً بك عزيزي: {bold(rname)}\n"
        f"{E['money']} رصيدك الحالي: {bold(currency(balance))}\n"
        f"{E['trophy']} المستوى: {bold('موزع V.I.P')}\n"
    )
    buttons = [
        [btn(f"{E['store']} متجر السيرفرات", "reseller_shop"), btn(f"{E['key']} مفاتيحي المشتراة", "reseller_my_keys")],
        [btn(f"{E['ticket']} كود شحن سريع", "reseller_recharge"), btn(f"{E['chart']} إحصائيات حسابي", "reseller_profile")]
    ]
    bot.send_message(message.chat.id, text, reply_markup=InlineKeyboardMarkup(buttons))

# ═════════════════════════════════════════════════════════════════════════════════════════════════════════
#  🌐 WEBHOOK SERVER
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════

@app.route("/", methods=["GET"])
def index():
    return "Bot Server is Online", 200

@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    if request.headers.get("content-type") == "application/json":
        json_string = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
    return "Forbidden", 403

if __name__ == "__main__":
    if RENDER_URL:
        bot.remove_webhook()
        bot.set_webhook(url=WEBHOOK_URL)
        port = int(os.environ.get("PORT", 5000))
        app.run(host="0.0.0.0", port=port)
    else:
        bot.remove_webhook()
        bot.infinity_polling()
