import logging
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# إعداد السجلات
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# التوكن الخاص بك
TOKEN = "8695639459:AAGNc7Y-9ShCxgQTKAml90FNpv0yAoDt3Ts"

# 📌 معرف قناتك الخاصة
CHANNEL_ID = -1003924784582

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

# 📂 ربط الحلقات بالرسائل الصحيحة لكل من القسمين (المترجم والمدبلج)
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
    keyboard = [
        [KeyboardButton("🎬 النسخة المترجمة"), KeyboardButton("🎙️ النسخة المدبلجة")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "🐺 **أهلاً بك في بوت مسلسل وادي الذئاب الرسمي**\n\nاختر النسخة من الأزرار بالأسفل:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
        
    text = update.message.text
    chat_id = update.message.chat_id

    if text == "🎬 النسخة المترجمة" or text == "🔙 المواسم المترجمة":
        context.user_data["media_type"] = "sub"
        keyboard = []
        row = []
        for season in range(1, 12):
            if season == 11:
                if row:
                    keyboard.append(row)
                    row = []
                keyboard.append([KeyboardButton("⚠️ الموسم 11 (مترجم) - متوقف")])
            else:
                count = SEASONS_EPISODES[season]["sub"]
                row.append(KeyboardButton(f"الموسم {season} ({count} حلقة)"))
                if len(row) == 2:
                    keyboard.append(row)
                    row = []
        if row:
            keyboard.append(row)
        keyboard.append([KeyboardButton("🔙 القائمة الرئيسية")])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("📂 اختر الموسم المطلوب (مترجم):", reply_markup=reply_markup)

    elif text == "🎙️ النسخة المدبلجة" or text == "🔙 المواسم المدبلجة":
        context.user_data["media_type"] = "dub"
        keyboard = []
        row = []
        for season in range(1, 12):
            if season == 11:
                if row:
                    keyboard.append(row)
                    row = []
                keyboard.append([KeyboardButton("⚠️ الموسم 11 (مدبلج) - متوقف")])
            else:
                count = SEASONS_EPISODES[season]["dub"]
                row.append(KeyboardButton(f"الموسم {season} ({count} حلقة)"))
                if len(row) == 2:
                    keyboard.append(row)
                    row = []
        if row:
            keyboard.append(row)
        keyboard.append([KeyboardButton("🔙 القائمة الرئيسية")])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("📂 اختر الموسم المطلوب (مدبلج):", reply_markup=reply_markup)

    elif text.startswith("الموسم "):
        try:
            parts = text.split(" ")
            season_num = int(parts[1])
            media_type = context.user_data.get("media_type", "sub")
            
            context.user_data["current_season"] = season_num

            total_episodes = SEASONS_EPISODES[season_num][media_type]
            if total_episodes == 0:
                await update.message.reply_text("⚠️ هذا الموسم غير متوفر حالياً.")
                return

            keyboard = []
            row = []
            for ep in range(1, total_episodes + 1):
                row.append(KeyboardButton(f"حلقة {ep}"))
                if len(row) == 4:
                    keyboard.append(row)
                    row = []
            if row:
                keyboard.append(row)
            
            back_btn = "🔙 المواسم المترجمة" if media_type == "sub" else "🔙 المواسم المدبلجة"
            keyboard.append([KeyboardButton(back_btn)])
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text(f"🎬 اختر الحلقة من الموسم {season_num}:", reply_markup=reply_markup)
        except Exception as e:
            logger.error(f"Error in season selection: {e}")

    elif text.startswith("حلقة "):
        try:
            ep_num = int(text.replace("حلقة ", ""))
            season_num = context.user_data.get("current_season", 1)
            media_type = context.user_data.get("media_type", "sub")

            msg_id = EPISODES_MSG_IDS.get((season_num, media_type), {}).get(ep_num)
            if msg_id:
                await context.bot.copy_message(chat_id=chat_id, from_chat_id=CHANNEL_ID, message_id=msg_id)
            else:
                await update.message.reply_text(f"⚠️ عذراً، حلقة الموسم {season_num} - الحلقة {ep_num} لم يتم ربطها بعد.")
        except Exception as e:
            logger.error(f"Error sending episode: {e}")

    elif text == "🔙 القائمة الرئيسية":
        keyboard = [
            [KeyboardButton("🎬 النسخة المترجمة"), KeyboardButton("🎙️ النسخة المدبلجة")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("🐺 **أهلاً بك مجدداً. اختر النسخة:**", reply_markup=reply_markup, parse_mode="Markdown")

    else:
        await update.message.reply_text("⚠️ يرجى استخدام الأزرار الموجودة أسفل الشاشة فقط.")

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
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)

    application.run_polling(drop_pending_updates=True, stop_signals=None)

if __name__ == "__main__":
    main()
