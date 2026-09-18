import logging
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# إعداد السجلات
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# التوكن الخاص بك
TOKEN = "8695639459:AAHlbqs7dlXUyGw1fweRhuzpQNBeIlHq0eo"

# 📌 معرف قناتك الخاصة بالمسلسل
CHANNEL_ID = -1003924784582

# 📌 معرف قناة الإدارة للمتابعة
ADMIN_CHANNEL_ID = -1003956613480 

# مجموعة لتخزين معرفات المستخدمين الفريدين للتحقق من (جديد أو قديم) وحساب العدد الإجمالي
unique_users = set()

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
    # القسم المترجم
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

    # القسم المدبلج
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # التحقق هل المستخدم جديد أم قديم
    if user.id in unique_users:
        user_status = "🔄 مستخدم قديم (عاد لفتح البوت)"
    else:
        unique_users.add(user.id)
        user_status = "🆕 مستخدم جديد تماماً"

    total_users_count = len(unique_users)
    username = f"@{user.username}" if user.username else "لا يوجد معرف"
    full_name = f"{user.first_name} {user.last_name or ''}".strip()
    
    admin_msg = (
        f"👤 **نشاط جديد في البوت!**\n\n"
        f"📌 الحالة: **{user_status}**\n"
        f"📛 الاسم: {full_name}\n"
        f"🔗 المعرف: {username}\n"
        f"🆔 الأيدي: `{user.id}`\n"
        f"📊 إجمالي عدد المستخدمين: **{total_users_count}**"
    )
    
    try:
        await context.bot.send_message(chat_id=ADMIN_CHANNEL_ID, text=admin_msg, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Failed to send visit info to admin channel: {e}")

    keyboard = [
        [
            InlineKeyboardButton("🎬 النسخة المترجمة", callback_data="type_sub"),
            InlineKeyboardButton("🎙️ النسخة المدبلجة", callback_data="type_dub")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "🐺 **أهلاً بك في بوت مسلسل وادي الذئاب الرسمي**\n\nاختر النسخة من الأزرار بالأسفل:"
    
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دالة حماية لمنع استخدام الكيبورد وكتابة الرسائل النصية"""
    try:
        # حذف رسالة النص التي كتبها المستخدم لمنع الفوضى في البوت
        await update.message.delete()
    except Exception:
        pass
    
    # إرسال تنبيه مؤقت أو رسالة توجيهية للمستخدم
    warning_msg = await update.message.reply_text(
        "⚠️ **عذراً، الكتابة النصية غير مسموحة هنا!**\nالرجاء استخدام الأزرار الظاهرة في الشاشة للتنقل داخل البوت.",
        parse_mode="Markdown"
    )
    
    # حذف رسالة التنبيه بعد 4 ثوانٍ للحفاظ على نظافة المحادثة
    import asyncio
    await asyncio.sleep(4)
    try:
        await warning_msg.delete()
    except Exception:
        pass

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = query.message.chat_id

    if data == "main_menu":
        keyboard = [
            [
                InlineKeyboardButton("🎬 النسخة المترجمة", callback_data="type_sub"),
                InlineKeyboardButton("🎙️ النسخة المدبلجة", callback_data="type_dub")
            ]
        ]
        await query.message.edit_text(
            "🐺 **أهلاً بك مجدداً. اختر النسخة:**",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    elif data in ["type_sub", "type_dub"]:
        media_type = "sub" if data == "type_sub" else "dub"
        context.user_data["media_type"] = media_type
        
        keyboard = []
        row = []
        for season in range(1, 12):
            if season == 11:
                if row:
                    keyboard.append(row)
                    row = []
                keyboard.append([InlineKeyboardButton(f"⚠️ الموسم 11 ({'مترجم' if media_type=='sub' else 'مدبلج'}) - متوقف", callback_data="none")])
            else:
                count = SEASONS_EPISODES[season][media_type]
                row.append(InlineKeyboardButton(f"الموسم {season} ({count} ح)", callback_data=f"season_{season}"))
                if len(row) == 2:
                    keyboard.append(row)
                    row = []
        if row:
            keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")])
        
        type_name = "المترجمة" if media_type == "sub" else "المدبلجة"
        await query.message.edit_text(
            f"📂 اختر الموسم المطلوب ({type_name}):",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data.startswith("season_"):
        season_num = int(data.split("_")[1])
        context.user_data["current_season"] = season_num
        media_type = context.user_data.get("media_type", "sub")
        
        total_episodes = SEASONS_EPISODES[season_num][media_type]
        if total_episodes == 0:
            await query.answer("⚠️ هذا الموسم غير متوفر حالياً.", show_alert=True)
            return

        keyboard = []
        row = []
        for ep in range(1, total_episodes + 1):
            row.append(InlineKeyboardButton(str(ep), callback_data=f"ep_{ep}"))
            if len(row) == 5:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        
        back_data = "type_sub" if media_type == "sub" else "type_dub"
        keyboard.append([InlineKeyboardButton("🔙 عودة للمواسم", callback_data=back_data)])
        
        await query.message.edit_text(
            f"🎬 اختر رقم الحلقة من الموسم {season_num}:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data.startswith("ep_"):
        ep_num = int(data.split("_")[1])
        season_num = context.user_data.get("current_season", 1)
        media_type = context.user_data.get("media_type", "sub")

        msg_id = EPISODES_MSG_IDS.get((season_num, media_type), {}).get(ep_num)
        if msg_id:
            try:
                await context.bot.copy_message(chat_id=chat_id, from_chat_id=CHANNEL_ID, message_id=msg_id)
            except Exception as e:
                logger.error(f"Error copying message: {e}")
                await query.answer("⚠️ حدث عطل أثناء إرسال الحلقة.", show_alert=True)
        else:
            await query.answer(f"⚠️ عذراً، حلقة الموسم {season_num} - الحلقة {ep_num} لم يتم ربطها بعد.", show_alert=True)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
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
    application.add_handler(CallbackQueryHandler(button_handler))
    # معالج لحماية البوت ومنع إرسال الرسائل النصية من الكيبورد (يستقبل أي نص عدا الأوامر مثل /start)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))
    application.add_error_handler(error_handler)

    application.run_polling(drop_pending_updates=True, stop_signals=None)

if __name__ == "__main__":
    main()
