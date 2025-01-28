import requests
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# إعداد المتغيرات
TOKEN = "8034873303:AAEhhLirEbvhypz4uRGfw5X6VtPY4uIaT_o"
CHANNEL_LINK = "https://t.me/+Sy18bATvBtg5ODgy"  # ضع رابط قناتك هنا
REFERRAL_LINK = "https://t.me/DurovCapsBot/caps?startapp=374668608"  # ضع رابط الإحالة الخاص بك هنا
ADMIN_ID = 6783842427  # معرف المدير (ID)

# إنشاء قاعدة بيانات لتخزين المستخدمين
def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT
    )
    """)
    conn.commit()
    conn.close()

# التحقق من اشتراك المستخدم
def is_subscribed(user_id):
    url = f"https://api.telegram.org/bot{TOKEN}/getChatMember"
    params = {"chat_id": CHANNEL_LINK, "user_id": user_id}
    response = requests.get(url, params=params).json()
    if response["ok"]:
        status = response["result"]["status"]
        return status in ["member", "administrator", "creator"]
    return False

# بدء البوت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    username = user.username

    # إضافة المستخدم إلى قاعدة البيانات
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    existing_user = cursor.fetchone()

    if not existing_user:
        cursor.execute("INSERT INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
        conn.commit()
        # إرسال إشعار للمدير عن المستخدم الجديد
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"👤 مستخدم جديد دخل البوت:\n\nID: {user_id}\nUsername: @{username if username else 'غير متوفر'}"
        )
    conn.close()

    # التحقق من اشتراك المستخدم في القناة
    if not is_subscribed(user_id):
        keyboard = [
            [InlineKeyboardButton("📢 اشترك في القناة", url=CHANNEL_LINK)],
            [InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_subscription")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"👋 أهلاً {user.first_name}!\n\n🚀 للانضمام إلى البوت والاستفادة من خدماتنا، يجب عليك الاشتراك في قناتنا:\n\n📢 {CHANNEL_LINK}\n\n"
            "✅ بعد الاشتراك، اضغط على زر التحقق أدناه.",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            f"🎉 مرحبًا {user.first_name}! يمكنك الآن الانضمام والعمل في البوت.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 رابط الإحالة", url=REFERRAL_LINK)]
            ])
        )

# التحقق من الاشتراك عند الضغط على زر التحقق
async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    if is_subscribed(user_id):
        await query.answer("✅ تم التحقق من اشتراكك!")
        await query.edit_message_text(
            "🎉 انضم واعمل في البوت الآن عبر الرابط أدناه.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 رابط الإحالة", url=REFERRAL_LINK)]
            ])
        )
    else:
        await query.answer("❌ لم يتم التحقق من اشتراكك.")
        await query.edit_message_text(
            f"🚨 يجب عليك الاشتراك أولاً في القناة: {CHANNEL_LINK}\nثم اضغط على زر التحقق."
        )

# لوحة تحكم المدير
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ هذه الأوامر مخصصة للمدير فقط.")
        return

    # إنشاء الأزرار
    keyboard = [
        [InlineKeyboardButton("👥 عرض عدد المستخدمين", callback_data="show_users")],
        [InlineKeyboardButton("📢 إرسال رسالة جماعية", callback_data="send_broadcast")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("📋 لوحة تحكم المدير:", reply_markup=reply_markup)

# التعامل مع خيارات لوحة تحكم المدير
async def handle_admin_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    if user_id != ADMIN_ID:
        await query.answer("❌ هذه الخيارات مخصصة للمدير فقط.")
        return

    if query.data == "show_users":
        # عرض عدد المستخدمين
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        conn.close()

        await query.answer()
        await query.edit_message_text(f"👥 عدد المستخدمين: {count}")

    elif query.data == "send_broadcast":
        # طلب رسالة للبث
        await query.answer()
        await query.edit_message_text("📢 أرسل الرسالة التي تريد إرسالها لجميع المستخدمين:")
        context.user_data["waiting_for_broadcast"] = True

# التعامل مع الرسالة الجماعية
async def handle_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ هذه الأوامر مخصصة للمدير فقط.")
        return

    if context.user_data.get("waiting_for_broadcast"):
        message = update.message.text
        context.user_data["waiting_for_broadcast"] = False

        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()
        conn.close()

        for user in users:
            try:
                await context.bot.send_message(chat_id=user[0], text=message)
            except Exception:
                pass

        await update.message.reply_text("✅ تم إرسال الرسالة إلى جميع المستخدمين.")

# تشغيل البوت
async def main():
    # تهيئة قاعدة البيانات
    init_db()

    # إنشاء التطبيق
    application = Application.builder().token(TOKEN).build()

    # تسجيل الأوامر
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CallbackQueryHandler(handle_admin_options, pattern="^show_users|send_broadcast$"))
    application.add_handler(CallbackQueryHandler(check_subscription, pattern="^check_subscription$"))

    # تشغيل التطبيق
    await application.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
