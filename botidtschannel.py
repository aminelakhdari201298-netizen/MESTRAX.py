import os
import json
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
from threading import Thread

# ================= الإعدادات الأساسية =================
TOKEN = '8716797254:AAFtDL7rEOiFsm6YAtKoq-CSdh0QCBJCk8o'
OWNER_ID = 8254258071  # الأيدي الخاص بك (المالك)

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ================= نظام حفظ البيانات =================
DATA_FILE = 'data.json'

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {"restricted_users": []}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f)

# ================= لوحة التحكم (الأزرار) =================
def main_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    btn_add = InlineKeyboardButton("➕ إضافة أدمن للحظر", callback_data="add_admin")
    btn_remove = InlineKeyboardButton("➖ إزالة أدمن من الحظر", callback_data="remove_admin")
    btn_list = InlineKeyboardButton("📋 قائمة المحظورين", callback_data="list_admins")
    btn_publish = InlineKeyboardButton("📢 نشر رسالة كـ بوت", callback_data="publish_msg")
    
    markup.add(btn_add, btn_remove)
    markup.add(btn_list)
    markup.add(btn_publish)
    return markup

# ================= أوامر البوت =================

@bot.message_handler(commands=['start', 'admin'])
def start_command(message):
    if message.from_user.id == OWNER_ID:
        text = (
            "👑 <b>أهلاً بك يا سيدي المالك!</b> 👑\n\n"
            "مرحباً بك في <b>لوحة التحكم الخرافية</b> 💎.\n"
            "من هنا يمكنك إدارة الأدمنز الذين تريد مسح رسائلهم فور إرسالها، "
            "بالإضافة إلى إمكانية النشر باسم البوت.\n\n"
            "👇 <i>اختر ما تريد فعله من الأزرار أدناه:</i>"
        )
        bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=main_keyboard())
    else:
        bot.send_message(message.chat.id, "⛔️ عذراً، هذا البوت مخصص للمالك فقط!")

# ================= التعامل مع الأزرار (Callbacks) =================

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    if call.from_user.id != OWNER_ID:
        bot.answer_callback_query(call.id, "⛔️ ليس لديك صلاحية لاستخدام هذه الأزرار!")
        return

    data = load_data()

    if call.data == "list_admins":
        users = data["restricted_users"]
        if not users:
            text = "✨ القائمة فارغة! لا يوجد أي أدمن محظور حالياً."
        else:
            text = "📋 <b>قائمة الأدمنز المحظورين:</b>\n\n"
            for u in users:
                text += f"🔹 <code>{u}</code>\n"
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=main_keyboard())

    elif call.data == "add_admin":
        msg = bot.edit_message_text("✍️ <b>أرسل الآن الـ ID الخاص بالأدمن الذي تريد مسح رسائله:</b>", call.message.chat.id, call.message.message_id, parse_mode="HTML")
        bot.register_next_step_handler(msg, process_add_admin)

    elif call.data == "remove_admin":
        msg = bot.edit_message_text("🗑️ <b>أرسل الـ ID الخاص بالأدمن الذي تريد إزالته من قائمة الحظر:</b>", call.message.chat.id, call.message.message_id, parse_mode="HTML")
        bot.register_next_step_handler(msg, process_remove_admin)

    elif call.data == "publish_msg":
        msg = bot.edit_message_text("📢 <b>أرسل الرسالة (نص، صورة، فيديو) التي تريد أن ينشرها البوت في المجموعة:</b>\n\n<i>(تأكد أن البوت موجود في المجموعة كأدمن)</i>", call.message.chat.id, call.message.message_id, parse_mode="HTML")
        bot.register_next_step_handler(msg, process_publish_message)

# ================= دوال المعالجة (الخطوة التالية) =================

def process_add_admin(message):
    if message.text and message.text.isdigit():
        user_id = int(message.text)
        data = load_data()
        if user_id not in data["restricted_users"]:
            data["restricted_users"].append(user_id)
            save_data(data)
            bot.send_message(message.chat.id, f"✅ <b>تم إضافة الـ ID:</b> <code>{user_id}</code> <b>بنجاح!</b> 🗑️ سيتم مسح أي رسالة يرسلها.", parse_mode="HTML", reply_markup=main_keyboard())
        else:
            bot.send_message(message.chat.id, "⚠️ هذا الشخص موجود بالفعل في القائمة!", reply_markup=main_keyboard())
    else:
        bot.send_message(message.chat.id, "❌ خطأ! يجب أن يكون الـ ID عبارة عن أرقام فقط.", reply_markup=main_keyboard())

def process_remove_admin(message):
    if message.text and message.text.isdigit():
        user_id = int(message.text)
        data = load_data()
        if user_id in data["restricted_users"]:
            data["restricted_users"].remove(user_id)
            save_data(data)
            bot.send_message(message.chat.id, f"✅ <b>تم إزالة الـ ID:</b> <code>{user_id}</code> <b>بنجاح!</b> ✨ يمكنه الآن التحدث بحرية.", parse_mode="HTML", reply_markup=main_keyboard())
        else:
            bot.send_message(message.chat.id, "⚠️ هذا الشخص غير موجود في القائمة أصلاً!", reply_markup=main_keyboard())
    else:
        bot.send_message(message.chat.id, "❌ خطأ! الـ ID يجب أن يكون أرقاماً.", reply_markup=main_keyboard())

def process_publish_message(message):
    bot.send_message(message.chat.id, "✅ تم استلام رسالتك. قم بتحويلها (Forward) الآن إلى المجموعة التي يتواجد فيها البوت، أو استخدمها في البوت كما تحب!", reply_markup=main_keyboard())
    # ملاحظة: يمكنك برمجة هذه الدالة لترسل لـ ID مجموعة معينة إذا كنت تعرفه!

# ================= مراقبة ومسح الرسائل =================

@bot.message_handler(func=lambda message: message.chat.type in ['group', 'supergroup'], content_types=['text', 'photo', 'video', 'document', 'audio', 'sticker', 'voice', 'animation'])
def delete_restricted_messages(message):
    data = load_data()
    sender_id = message.from_user.id
    
    # إذا كان المرسل ضمن المحظورين، نقوم بمسح رسالته
    if sender_id in data.get("restricted_users", []):
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except Exception as e:
            print(f"Error deleting message: {e}")

# ================= إعداد سيرفر Flask لـ Render =================

@app.route('/')
def home():
    return "🤖 البوت الأسطوري يعمل بنجاح 24/7! 🔥"

def run_bot():
    bot.infinity_polling(skip_pending=True)

if __name__ == "__main__":
    # تشغيل البوت في مسار منفصل
    thread = Thread(target=run_bot)
    thread.start()
    
    # تشغيل Flask
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
