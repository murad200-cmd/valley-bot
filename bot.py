import logging
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import time
import asyncio
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.WARNING)
logger = logging.getLogger(__name__)

TOKEN = "8695639459:AAHlbqs7dlXUyGw1fweRhuzpQNBeIlHq0eo"
CHANNEL_ID = -1003924784582
ADMIN_CHANNEL_ID = -1003956613480 

unique_users = set()
banned_users = set()
daily_visits = set()
daily_errors_count = 0
user_spam_tracker = {}
user_last_watched = {}

SEASONS_EPISODES = {
    1: {"sub": 55, "dub": 86},
    2: {"sub": 42, "dub": 70},
    3: {"sub": 22, "dub": 124},
    4: {"sub": 30, "dub": 62},
    5: {"sub": 35, "dub": 78},
    6: {"sub": 33, "dub": 72},
    7: {"sub": 31, "dub": 78},
    8: {"sub": 47, "dub": 84},
    9: {"sub": 34, "dub": 34},
    10: {"sub": 37, "dub": 37},
    11: {"sub": 0, "dub": 0}
}

EPISODES_MSG_IDS = {
    (1, "sub"): {i: 206 + i - 1 for i in range(1, 56)},
    (2, "sub"): {i: 261 + i - 1 for i in range(1, 43)},
    (3, "sub"): {i: 303 + i - 1 for i in range(1, 23)},
    (4, "sub"): {i: 325 + i - 1 for i in range(1, 31)},
    (5, "sub"): {i: 355 + i - 1 for i in range(1, 36)},
    (6, "sub"): {i: 423 + i - 1 for i in range(1, 34)},
    (7, "sub"): {i: 456 + i - 1 for i in range(1, 32)},
    (8, "sub"): {i: 487 + i - 1 for i in range(1, 48)},
    (9, "sub"): {i: 534 + i - 1 for i in range(1, 35)},
    (10, "sub"): {i: 568 + i - 1 for i in range(1, 38)},
    (1, "dub"): {i: 605 + i - 1 for i in range(1, 87)},
    (2, "dub"): {i: 691 + i - 1 for i in range(1, 71)},
    (3, "dub"): {i: 761 + i - 1 for i in range(1, 125)},
    (4, "dub"): {i: 885 + i - 1 for i in range(1, 63)},
    (5, "dub"): {i: 947 + i - 1 for i in range(1, 79)},
    (6, "dub"): {i: 1025 + i - 1 for i in range(1, 73)},
    (7, "dub"): {i: 1175 + i - 1 for i in range(1, 79)},
    (8, "dub"): {i: 1253 + i - 1 for i in range(1, 85)},
    (9, "dub"): {i: 1337 + i - 1 for i in range(1, 35)},
    (10, "dub"): {i: 1371 + i - 1 for i in range(1, 38)},
}

def get_main_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("🎬 النسخة المترجمة"), KeyboardButton("🎙️ النسخة المدبلجة")],
        [KeyboardButton("📺 آخر حلقة شاهدتها")]
    ], resize_keyboard=True)

async def send_daily_report(context):
    global daily_visits, daily_errors_count
    report_msg = (
        f"📊 **التقرير اليومي والإحصائيات الشاملة**\n\n"
        f"👥 الزوار الجدد (اليوم): **{len(daily_visits)}**\n"
        f"🌐 **إجمالي الزوار منذ التأسيس:** **{len(unique_users)}**\n"
        f"⚠️ الأخطاء المسجلة: **{daily_errors_count}**\n"
        f"🟢 الحالة: **يعمل بكفاءة تامة على Render**"
    )
    try:
        await context.bot.send_message(chat_id=ADMIN_CHANNEL_ID, text=report_msg, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error sending report: {e}")
    daily_visits.clear()
    daily_errors_count = 0

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id in banned_users:
        return
        
    is_new_user = False
    if user.id not in unique_users:
        unique_users.add(user.id)
        is_new_user = True

    daily_visits.add(user.id)

    if is_new_user:
        username = f"@{user.username}" if user.username else "لا يوجد معرف"
        full_name = f"{user.first_name}"
        new_user_alert = (
            f"👤 **مستخدم جديد انضم إلى البوت!**\n\n"
            f"▫️ الاسم: {full_name}\n"
            f"▫️ المعرف: {username}\n"
            f"▫️ الأيدي: `{user.id}`\n"
            f"🌐 إجمالي الزوار حتى الآن: **{len(unique_users)}**"
        )
        try:
            await context.bot.send_message(chat_id=ADMIN_CHANNEL_ID, text=new_user_alert, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Error sending new user alert: {e}")

    await update.message.reply_text(
        "🐺 **أهلاً بك في بوت مسلسل وادي الذئاب الرسمي**\n\nاختر من الأزرار في الأسفل:",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id in banned_users:
        return

    text = update.message.text if update.message.text else (update.message.caption or "")
    chat_id = update.effective_chat.id
    user_id = user.id

    if text in ["🎬 النسخة المترجمة", "🎙️ النسخة المدبلجة", "📺 آخر حلقة شاهدتها", "🔙 القائمة الرئيسية"] or \
       ("الجزء " in text and ("مترجم -" in text or "مدبلج -" in text)) or \
       text.startswith("حلقة "):
        
        if user_id in user_spam_tracker:
            user_spam_tracker[user_id]["count"] = 0

        if text == "🎬 النسخة المترجمة":
            context.user_data["media_type"] = "sub"
            # ترتيب الأجزاء في صفوف من زرين (أعمدة وصفوف منظمة)
            keyboard = []
            row = []
            for s in range(1, 11):
                row.append(KeyboardButton(f"مترجم - الجزء {s} ({SEASONS_EPISODES[s]['sub']} ح)"))
                if len(row) == 2:
                    keyboard.append(row)
                    row = []
            if row:
                keyboard.append(row)
            keyboard.append([KeyboardButton("⚠️ الجزء 11 (مترجم) - متوقف")])
            keyboard.append([KeyboardButton("🔙 القائمة الرئيسية")])
            await update.message.reply_text("📂 اختر الجزء المطلوب:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

        elif text == "🎙️ النسخة المدبلجة":
            context.user_data["media_type"] = "dub"
            # ترتيب الأجزاء المدبلجة في صفوف من زرين (أعمدة وصفوف منظمة)
            keyboard = []
            row = []
            for s in range(1, 11):
                row.append(KeyboardButton(f"مدبلج - الجزء {s} ({SEASONS_EPISODES[s]['dub']} ح)"))
                if len(row) == 2:
                    keyboard.append(row)
                    row = []
            if row:
                keyboard.append(row)
            keyboard.append([KeyboardButton("⚠️ الجزء 11 (مدبلج) - متوقف")])
            keyboard.append([KeyboardButton("🔙 القائمة الرئيسية")])
            await update.message.reply_text("📂 اختر الجزء المطلوب:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

        elif text == "📺 آخر حلقة شاهدتها":
            last_ep_info = user_last_watched.get(user_id)
            if last_ep_info:
                msg_id = EPISODES_MSG_IDS.get((last_ep_info["season"], last_ep_info["type"]), {}).get(last_ep_info["ep"])
                if msg_id:
                    await context.bot.copy_message(chat_id=chat_id, from_chat_id=CHANNEL_ID, message_id=msg_id)
            else:
                await update.message.reply_text("⚠️ لم تقم بمشاهدة أي حلقة حتى الآن.", reply_markup=get_main_keyboard())

        elif text == "🔙 القائمة الرئيسية":
            await update.message.reply_text("🐺 القائمة الرئيسية:", reply_markup=get_main_keyboard())

        elif "الجزء " in text:
            try:
                parts = text.split("-")
                season_num = int(parts[1].strip().split(" ")[1])
                media_type = "sub" if "مترجم" in parts[0] else "dub"
                context.user_data["current_season"] = season_num
                context.user_data["media_type"] = media_type
                total = SEASONS_EPISODES[season_num][media_type]
                
                # ترتيب أزرار الحلقات في شبكة منتظمة (5 أزرار في كل صف لتبدو مرتبة بشكل جميل كأعمدة وصفوف)
                keyboard = []
                row = []
                for ep in range(1, total + 1):
                    row.append(KeyboardButton(f"حلقة {ep}"))
                    if len(row) == 5:
                        keyboard.append(row)
                        row = []
                if row:
                    keyboard.append(row)
                
                keyboard.append([KeyboardButton("🔙 القائمة الرئيسية")])
                await update.message.reply_text(f"🎬 اختر رقم الحلقة:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
            except:
                pass

        elif text.startswith("حلقة "):
            try:
                ep_num = int(text.split(" ")[1])
                s_num = context.user_data.get("current_season", 1)
                m_type = context.user_data.get("media_type", "sub")
                user_last_watched[user_id] = {"season": s_num, "ep": ep_num, "type": m_type}
                msg_id = EPISODES_MSG_IDS.get((s_num, m_type), {}).get(ep_num)
                if msg_id:
                    await context.bot.copy_message(chat_id=chat_id, from_chat_id=CHANNEL_ID, message_id=msg_id)
            except:
                pass
    else:
        is_link = "http://" in text or "https://" in text or "t.me://" in text or "t.me/" in text or "www." in text
        current_time = time.time()
        
        if user_id not in user_spam_tracker:
            user_spam_tracker[user_id] = {"count": 1, "last_time": current_time}
        else:
            if current_time - user_spam_tracker[user_id]["last_time"] < 10:
                user_spam_tracker[user_id]["count"] += 1
            user_spam_tracker[user_id]["last_time"] = current_time

        spam_count = user_spam_tracker[user_id]["count"]
        msg_id_to_forward = update.message.message_id

        try:
            await update.message.delete()
        except:
            pass

        username = f"@{user.username}" if user.username else "لا يوجد معرف"
        full_name = f"{user.first_name}"

        if is_link or spam_count > 4:
            banned_users.add(user_id)
            auto_ban_report = (
                f"🚨 **حظر تلقائي فوري!**\n"
                f"👤 الاسم: {full_name} | المعرف: {username} | الأيدي: `{user.id}`\n"
                f"📌 السبب: {'رابط مريب' if is_link else 'إغراق (Spam)'}"
            )
            try:
                await context.bot.send_message(chat_id=ADMIN_CHANNEL_ID, text=auto_ban_report, parse_mode="Markdown")
                await context.bot.forward_message(chat_id=ADMIN_CHANNEL_ID, from_chat_id=chat_id, message_id=msg_id_to_forward)
            except:
                pass
            return

        info_header = (
            f"⚠️ **محاولة كتابة أو إرسال خاطئة - بانتظار قرارك**\n"
            f"👤 الاسم: {full_name} | المعرف: {username}\n"
            f"🆔 الأيدي: `{user.id}`"
        )
        
        inline_kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🛑 حظر", callback_data=f"ban_{user_id}"),
                InlineKeyboardButton("✅ السماح", callback_data=f"pass_{user_id}")
            ]
        ])

        try:
            await context.bot.send_message(chat_id=ADMIN_CHANNEL_ID, text=info_header, parse_mode="Markdown")
            await context.bot.forward_message(chat_id=ADMIN_CHANNEL_ID, from_chat_id=chat_id, message_id=msg_id_to_forward)
            await context.bot.send_message(chat_id=ADMIN_CHANNEL_ID, text="اختر الإجراء المناسب للمستخدم:", reply_markup=inline_kb)
        except Exception as e:
            logger.error(f"Error forwarding user message: {e}")

        warning_msg = await update.message.reply_text("⚠️ **الكتابة وإرسال الملفات غير مسموحة هنا، استخدم الأزرار.**")
        await asyncio.sleep(3)
        try:
            await warning_msg.delete()
        except:
            pass

async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    parts = data.split("_")
    action = parts[0]
    target_user_id = int(parts[1])

    if action == "ban":
        banned_users.add(target_user_id)
        new_kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📌 الاستمرار بالحظر", callback_data=f"keepban_{target_user_id}"),
                InlineKeyboardButton("🔓 إزالة الحظر", callback_data=f"unban_{target_user_id}")
            ]
        ])
        try:
            await query.edit_message_text(
                text=f"🛑 **تم حظر المستخدم (ID: `{target_user_id}`) بنجاح.**\nاختر الإجراء التالي:", 
                parse_mode="Markdown", 
                reply_markup=new_kb
            )
        except:
            pass

    elif action == "pass":
        try:
            await query.edit_message_text(
                text=f"✅ **تم السماح للمستخدم (ID: `{target_user_id}`) بمتابعة النشاط.**", 
                parse_mode="Markdown"
            )
        except:
            pass

    elif action == "keepban":
        try:
            await query.edit_message_text(
                text=f"📌 **تم تأكيد الاستمرار بحظر المستخدم (ID: `{target_user_id}`).**", 
                parse_mode="Markdown"
            )
        except:
            pass

    elif action == "unban":
        if target_user_id in banned_users:
            banned_users.remove(target_user_id)
        try:
            await query.edit_message_text(
                text=f"🔓 **تم إزالة الحظر عن المستخدم (ID: `{target_user_id}`) بنجاح.**", 
                parse_mode="Markdown"
            )
        except:
            pass

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    global daily_errors_count
    daily_errors_count += 1
    try:
        error_msg = f"⚠️ **خطأ تقني مؤقت في البوت:**\n`{context.error}`"
        await context.bot.send_message(chat_id=ADMIN_CHANNEL_ID, text=error_msg, parse_mode="Markdown")
    except:
        pass

class SafeHTTPHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is active and running smoothly via Telegram!")
    
    def log_message(self, format, *args):
        return 

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SafeHTTPHandler)
    server.serve_forever()

def main():
    threading.Thread(target=run_web_server, daemon=True).start()
    application = Application.builder().token(TOKEN).build()
    
    if application.job_queue:
        application.job_queue.run_repeating(send_daily_report, interval=86400, first=60)

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(admin_callback_handler, pattern="^(ban|pass|keepban|unban)_"))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_messages))
    application.add_error_handler(error_handler)

    application.run_polling(drop_pending_updates=True, stop_signals=None)

if __name__ == "__main__":
    main()
