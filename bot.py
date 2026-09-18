import logging
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import asyncio
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# إعداد السجلات
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# التوكن الخاص بك
TOKEN = "8695639459:AAHlbqs7dlXUyGw1fweRhuzpQNBeIlHq0eo"

# 📌 معرف قناتك الخاصة بالمسلسل
CHANNEL_ID = -1003924784582

# 📌 معرف قناة الإدارة للمتابعة
ADMIN_CHANNEL_ID = -1003956613480 

# مجموعة لتخزين معرفات المستخدمين الفريدين
unique_users = set()

# متغيرات لتتبع إحصائيات الـ 24 ساعة الأخيرة
daily_visits = set()
daily_errors_count = 0

# قاموس لتخزين آخر حلقة شاهدها كل مستخدم
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

# 📌 دالة إرسال التقرير التلقائي عبر حلقة بايثون الخلفية
async def send_daily_report_loop(bot):
    await asyncio.sleep(60)
    while True:
        global daily_visits, daily_errors_count
        new_users_count = len(daily_visits)
        total_users_count = len(unique_users)
        
        report_msg = (
            f"📊 **التقرير اليومي لأداء البوت (كل 24 ساعة)**\n\n"
            f"👥 عدد الزوار الجدد اليوم: **{new_users_count}**\n"
            f"📈 إجمالي المستخدمين الكلي: **{total_users_count}**\n"
            f"⚠️ عدد الأخطاء البرمجية المرصودة: **{daily_errors_count}**\n"
            f"🟢 حالة السيرفر: **يعمل بشكل مستقر وسليم**"
        )
        
        try:
            await bot.send_message(chat_id=ADMIN_CHANNEL_ID, text=report_msg, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Failed to send daily report: {e}")
        
        daily_visits.clear()
        daily_errors_count = 0
        
        await asyncio.sleep(86400)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user.id in unique_users:
        user_status = "🔄 مستخدم قديم (عاد لفتح البوت)"
    else:
        unique_users.add(user.id)
        user_status = "🆕 مستخدم جديد تماماً"

    daily_visits.add(user.id)

    total_users_count = len(unique_users)
    username = f"@{user.username}" if user.username else "لا يوجد معرف"
    full_name = f"{user.first_name} {user.last_name or ''}".strip()
    
    admin_msg = (
        f"👤 **نشاط جديد في البوت!**\n\n"
        f"📌 الحالة: **{user_status}**\n"
        f"📛 الاسم: {full_name}\n"
        f"🔗 المعرف: {username}\n"
        f"🆔 الأيدي: `{user.id}`\n"
        f"📊 إجمالي عدد المستخدمين: **{total_users_count}**\n\n"
        f"🟢 **حالة السيرفر:** يعمل بشكل مستقر وسليم"
    )
    
    try:
        await context.bot.send_message(chat_id=ADMIN_CHANNEL_ID, text=admin_msg, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Failed to send visit info to admin channel: {e}")

    await update.message.reply_text(
        "🐺 **أهلاً بك في بوت مسلسل وادي الذئاب الرسمي**\n\nاختر من الأزرار في الأسفل:",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    user = update.effective_user

    if text == "🎬 النسخة المترجمة":
        context.user_data["media_type"] = "sub"
        keyboard = []
        row = []
        for season in range(1, 12):
            if season == 11:
                if row:
                    keyboard.append(row)
                    row = []
                keyboard.append([KeyboardButton("⚠️ الجزء 11 (مترجم) - متوقف")])
            else:
                count = SEASONS_EPISODES[season]["sub"]
                row.append(KeyboardButton(f"مترجم - الجزء {season} ({count} ح)"))
                if len(row) == 2:
                    keyboard.append(row)
                    row = []
        if row:
            keyboard.append(row)
        
        keyboard.append([KeyboardButton("🔙 القائمة الرئيسية")])
        await update.message.reply_text("📂 اختر الجزء المطلوب (المترجم):", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

    elif text == "🎙️ النسخة المدبلجة":
        context.user_data["media_type"] = "dub"
        keyboard = []
        row = []
        for season in range(1, 12):
            if season == 11:
                if row:
                    keyboard.append(row)
                    row = []
                keyboard.append([KeyboardButton("⚠️ الجزء 11 (مدبلج) - متوقف")])
            else:
                count = SEASONS_EPISODES[season]["dub"]
                row.append(KeyboardButton(f"مدبلج - الجزء {season} ({count} ح)"))
                if len(row) == 2:
                    keyboard.append(row)
                    row = []
        if row:
            keyboard.append(row)
        
        keyboard.append([KeyboardButton("🔙 القائمة الرئيسية")])
        await update.message.reply_text("📂 اختر الجزء المطلوب (المدبلج):", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

    elif text == "📺 آخر حلقة شاهدتها":
        last_ep_info = user_last_watched.get(user_id)
        if last_ep_info:
            season_num = last_ep_info["season"]
            ep_num = last_ep_info["ep"]
            media_type = last_ep_info["type"]
            type_name = "مترجمة 🎬" if media_type == "sub" else "مدبلجة 🎙️"
            
            await update.message.reply_text(
                f"📌 **آخر حلقة قمت بمشاهدتها:**\n"
                f"▫️ النسخة: {type_name}\n"
                f"▫️ الجزء: {season_num}\n"
                f"▫️ الحلقة: {ep_num}\n\n"
                f"جاري إرسالها لك الان...",
                reply_markup=get_main_keyboard(),
                parse_mode="Markdown"
            )
            
            msg_id = EPISODES_MSG_IDS.get((season_num, media_type), {}).get(ep_num)
            if msg_id:
                try:
                    await context.bot.copy_message(chat_id=chat_id, from_chat_id=CHANNEL_ID, message_id=msg_id)
                except Exception as e:
                    logger.error(f"Error copying last watched episode: {e}")
            else:
                await update.message.reply_text("⚠️ عذراً، لم يتم العثور على ملف الحلقة.")
        else:
            await update.message.reply_text(
                "⚠️ **لم تقم بمشاهدة أي حلقة حتى الآن!**\nقم بتصفح الأقسام واختر حلقتك الأولى.",
                reply_markup=get_main_keyboard(),
                parse_mode="Markdown"
            )

    elif text == "🔙 القائمة الرئيسية":
        await update.message.reply_text("🐺 **القائمة الرئيسية:**", reply_markup=get_main_keyboard(), parse_mode="Markdown")

    elif "الجزء " in text and ("مترجم -" in text or "مدبلج -" in text):
        try:
            parts = text.split("-")
            media_prefix = parts[0].strip()
            season_part = parts[1].strip()
            season_num = int(season_part.split(" ")[1])
            
            media_type = "sub" if "مترجم" in media_prefix else "dub"
            context.user_data["current_season"] = season_num
            context.user_data["media_type"] = media_type

            total_episodes = SEASONS_EPISODES[season_num][media_type]
            if total_episodes == 0:
                await update.message.reply_text("⚠️ هذا الجزء غير متوفر حالياً.")
                return

            keyboard = []
            row = []
            for ep in range(1, total_episodes + 1):
                row.append(KeyboardButton(f"حلقة {ep}"))
                if len(row) == 5:
                    keyboard.append(row)
                    row = []
            if row:
                keyboard.append(row)
            
            back_text = "🎬 النسخة المترجمة" if media_type == "sub" else "🎙️ النسخة المدبلجة"
            keyboard.append([KeyboardButton(back_text), KeyboardButton("🔙 القائمة الرئيسية")])
            
            await update.message.reply_text(f"🎬 اختر رقم الحلقة من الجزء {season_num}:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        except Exception as e:
            logger.error(f"Error parsing season selection: {e}")

    elif text.startswith("حلقة "):
        try:
            ep_num = int(text.split(" ")[1])
            season_num = context.user_data.get("current_season", 1)
            media_type = context.user_data.get("media_type", "sub")

            user_last_watched[user_id] = {
                "season": season_num,
                "ep": ep_num,
                "type": media_type
            }

            msg_id = EPISODES_MSG_IDS.get((season_num, media_type), {}).get(ep_num)
            if msg_id:
                await context.bot.copy_message(chat_id=chat_id, from_chat_id=CHANNEL_ID, message_id=msg_id)
            else:
                await update.message.reply_text(f"⚠️ عذراً، حلقة الجزء {season_num} - الحلقة {ep_num} لم يتم ربطها بعد.")
        except Exception as e:
            logger.error(f"Error sending episode: {e}")

    else:
        # 📌 إذا كتب المستخدم نصاً خارج الأزرار، نحذفه ونرسل تقريراً فورياً لقناة الإدارة مع تفاصيله
        try:
            await update.message.delete()
        except Exception:
            pass
        
        username = f"@{user.username}" if user.username else "لا يوجد معرف"
        full_name = f"{user.first_name} {user.last_name or ''}".strip()
        
        unknown_msg_report = (
            f"⚠️ **محاولة إرسال نص خاطئ في البوت!**\n\n"
            f"👤 الاسم: {full_name}\n"
            f"🔗 المعرف: {username}\n"
            f"🆔 الأيدي: `{user.id}`\n"
            f"📝 النص المرسل: `{text}`"
        )
        
        try:
            await context.bot.send_message(chat_id=ADMIN_CHANNEL_ID, text=unknown_msg_report, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Failed to send unknown text report: {e}")
        
        warning_msg = await update.message.reply_text(
            "⚠️ **عذراً، الكتابة النصية غير مسموحة هنا!**\nالرجاء استخدام الأزرار في الأسفل للتنقل.",
            parse_mode="Markdown"
        )
        await asyncio.sleep(4)
        try:
            await warning_msg.delete()
        except Exception:
            pass

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    global daily_errors_count
    daily_errors_count += 1
    logger.error("Exception while handling an update:", exc_info=context.error)

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), BaseHTTPRequestHandler)
    server.serve_forever()

def main():
    server_thread = threading.Thread(target=run_web_server, daemon=True)
    server_thread.start()

    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))
    application.add_error_handler(error_handler)

    async def post_init(app: Application):
        asyncio.create_task(send_daily_report_loop(app.bot))

    application.post_init = post_init

    application.run_polling(drop_pending_updates=True, stop_signals=None)

if __name__ == "__main__":
    main()
