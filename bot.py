import logging
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
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
    2: {"sub": 42, "dub": 42},
    3: {"sub": 62, "dub": 30},
    4: {"sub": 37, "dub": 37},
    5: {"sub": 34, "dub": 34},
    6: {"sub": 36, "dub": 36},
    7: {"sub": 38, "dub": 38},
    8: {"sub": 39, "dub": 39},
    9: {"sub": 39, "dub": 39},
    10: {"sub": 39, "dub": 39},
    11: {"sub": 0, "dub": 0}
}

# 📂 ربط الحلقات تسلسلياً بناءً على البداية من الرسالة 1
EPISODES_MSG_IDS = {
    (1, "sub"): {i: 1 + i - 1 for i in range(1, 56)},
    (2, "sub"): {i: 56 + i - 1 for i in range(1, 43)},
    (3, "sub"): {i: 98 + i - 1 for i in range(1, 63)},
    (1, "dub"): {
        # سيتم ملؤها لاحقاً
    }
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
                keyboard.append([KeyboardButton(f"⚠️ الموسم 11 (مترجم) - متوقف")])
            else:
                count = SEASONS_EPISODES[season]["sub"]
                row.append(KeyboardButton(f"الموسم {season} (مترجم)"))
                if len(row) == 2:
                    keyboard.append(row)
                    row = []
        if row:
            keyboard.append(row)
        keyboard.append([KeyboardButton("🔙 القائمة الرئيسية")])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("📂 اختر الموسم المطلوب:", reply_markup=reply_markup)

    elif text == "🎙️ النسخة المدبلجة" or text == "🔙 المواسم المدبلجة":
        context.user_data["media_type"] = "dub"
        keyboard = []
        row = []
        for season in range(1, 12):
            if season == 11:
                if row:
                    keyboard.append(row)
                    row = []
                keyboard.append([KeyboardButton(f"⚠️ الموسم 11 (مدبلج) - متوقف")])
            else:
                count = SEASONS_EPISODES[season]["dub"]
                row.append(KeyboardButton(f"الموسم {season} (مدبلج)"))
                if len(row) == 2:
                    keyboard.append(row)
                    row = []
        if row:
            keyboard.append(row)
        keyboard.append([KeyboardButton("🔙 القائمة الرئيسية")])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("📂 اختر الموسم المطلوب:", reply_markup=reply_markup)

    elif text.startswith("الموسم "):
        # استخراج رقم الموسم ونوعه من نص الزر (مثال: "الموسم 1 (مترجم)")
        parts = text.split(" ")
        season_num = int(parts[1])
        media_type = "sub" if "مترجم" in text else "dub"
        context.user_data["current_season"] = season_num

        total_episodes = SEASONS_EPISODES[season_num][media_type]
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

    elif text.startswith("حلقة "):
        ep_num = int(text.replace("حلقة ", ""))
        season_num = context.user_data.get("current_season", 1)
        media_type = context.user_data.get("media_type", "sub")

        msg_id = EPISODES_MSG_IDS.get((season_num, media_type), {}).get(ep_num)
        if msg_id:
            try:
                await context.bot.copy_message(chat_id=chat_id, from_chat_id=CHANNEL_ID, message_id=msg_id)
            except Exception as e:
                await update.message.reply_text("⚠️ حدث خطأ أثناء جلب الحلقة، تأكد من أن البوت مشرف في القناة.")
        else:
            await update.message.reply_text(f"⚠️ عذراً، حلقة الموسم {season_num} - الحلقة {ep_num} لم يتم ربطها بعد.")

    elif text == "🔙 القائمة الرئيسية":
        keyboard = [
            [KeyboardButton("🎬 النسخة المترجمة"), KeyboardButton("🎙️ النسخة المدبلجة")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("🐺 **أهلاً بك مجدداً. اختر النسخة:**", reply_markup=reply_markup, parse_mode="Markdown")

    else:
        await update.message.reply_text("⚠️ يرجى استخدام الأزرار الموجودة أسفل الشاشة فقط.")

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
    application.run_polling(stop_signals=None)

if __name__ == "__main__":
    main()
