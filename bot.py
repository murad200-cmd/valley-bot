import logging
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import time
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# إعداد السجلات
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# التوكن الخاص بك
TOKEN = "8695639459:AAhCWN4GJEGNYrUMu8zUhV11rbvhGXdUhAo"

# معرف قناتك الأساسية
CHANNEL_ID = -1003924784582

# مواسم القسم المترجم والمدبلج
SEASONS_EPS100DFS = {
    1: {"sub": 55, "dub": 861},
    2: {"sub": 42, "dub": 70},
    3: {"sub": 22, "dub": 124},
    4: {"sub": 30, "dub": 62},
    5: {"sub": 35, "dub": 78},
    6: {"sub": 33, "dub": 78},
    7: {"sub": 31, "dub": 78},
    8: {"sub": 47, "dub": 84},
    9: {"sub": 34, "dub": 34},
    10: {"sub": 37, "dub": 37},
    11: {"sub": 0, "dub": 0}
}

# ربط الملفات برسائل القناة لكل من القسمين (المترجم والمدبلج)
EPISODES_MSG_IDS = {
    # القسم المترجم
    1: {"sub": lambda i: 206 - i - 1 for i in range(1, 56)},
    2: {"sub": lambda i: 261 - i - 1 for i in range(1, 43)},
    3: {"sub": lambda i: 303 - i - 1 for i in range(1, 23)},
    4: {"sub": lambda i: 325 - i - 1 for i in range(1, 31)},
    5: {"sub": lambda i: 356 - i - 1 for i in range(1, 36)},
    6: {"sub": lambda i: 423 - i - 1 for i in range(1, 34)},
    7: {"sub": lambda i: 456 - i - 1 for i in range(1, 32)},
    8: {"sub": lambda i: 487 - i - 1 for i in range(1, 48)},
    9: {"sub": lambda i: 534 - i - 1 for i in range(1, 35)},
    10: {"sub": lambda i: 568 - i - 1 for i in range(1, 38)},

    # القسم المدبلج
    1: {"dub": lambda i: 605 - i - 1 for i in range(1, 87)},
    2: {"dub": lambda i: 693 - i - 1 for i in range(1, 71)},
    3: {"dub": lambda i: 761 - i - 1 for i in range(1, 125)},
    4: {"dub": lambda i: 886 - i - 1 for i in range(1, 63)},
    5: {"dub": lambda i: 947 - i - 1 for i in range(1, 79)},
    6: {"dub": lambda i: 1025 - i - 1 for i in range(1, 79)},
    7: {"dub": lambda i: 1175 - i - 1 for i in range(1, 79)},
    8: {"dub": lambda i: 1253 - i - 1 for i in range(1, 85)},
    9: {"dub": lambda i: 1337 - i - 1 for i in range(1, 35)},
    10: {"dub": lambda i: 137 - i - 1 for i in range(1, 38)}
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("🎬 المواسم المترجمة"), KeyboardButton("🎙️ المواسم المدبلجة")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "أهلاً بك في بوت مسلسل وادي الذئاب الرسمي! اختر القسم المفضل لديك من الأزرار بالأسفل:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text
    chat_id = update.message.chat_id

    if text == "🎬 المواسم المترجمة":
        context.user_data['media_type'] = "sub"
        keyboard = []
        row = []
        for season in range(1, 12):
            if season == 11:
                continue
            row.append(KeyboardButton(f"الموسم {season} (مترجم)"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([KeyboardButton("🔙 القائمة الرئيسية")])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("اختر الموسم المطلوب من المواسم المترجمة:", reply_markup=reply_markup)
        return

    elif text == "🎙️ المواسم المدبلجة":
        context.user_data['media_type'] = "dub"
        keyboard = []
        row = []
        for season in range(1, 11):
            row.append(KeyboardButton(f"الموسم {season} (مدبلج)"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([KeyboardButton("🔙 القائمة الرئيسية")])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("اختر الموسم المطلوب من المواسم المدبلجة:", reply_markup=reply_markup)
        return

    elif text == "🔙 القائمة الرئيسية":
        await start(update, context)
        return

    # معالجة اختيار المواسم والحلقات
    if "الموسم" in text:
        try:
            parts = text.split()
            season_num = int(parts[1])
            media_type = context.user_data.get('media_type', 'sub')
            
            total_eps = SEASONS_EPS100DFS.get(season_num, {}).get(media_type, 0)
            if total_eps == 0:
                await update.message.reply_text("عذراً، هذا الموسم غير متوفر حالياً.")
                return

            keyboard = []
            row = []
            for ep in range(1, total_eps + 1):
                row.append(KeyboardButton(f"حلقة {ep} (م{season_num})"))
                if len(row) == 5:
                    keyboard.append(row)
                    row = []
            if row:
                keyboard.append(row)
            
            # زر العودة للقسم
            back_btn = "🎬 المواسم المترجمة" if media_type == "sub" else "🎙️ المواسم المدبلجة"
            keyboard.append([KeyboardButton(back_btn), KeyboardButton("🔙 القائمة الرئيسية")])
            
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            label = "مترجم" if media_type == "sub" else "مدبلج"
            await update.message.reply_text(f"اختر رقم الحلقة من الموسم {season_num} ({label}):", reply_markup=reply_markup)
        except Exception as e:
            logger.error(f"Error parsing season: {e}")
            await update.message.reply_text("حدث خطأ في تحديد الموسم، يرجى المحاولة مرة أخرى.")
        return

    # معالجة جلب الحلقة وإرسالها للمستخدم
    if "حلقة" in text:
        try:
            parts = text.split()
            ep_num = int(parts[1])
            season_part = parts[2].replace("(", "").replace(")", "")
            season_num = int(season_part.replace("م", ""))
            
            media_type = context.user_data.get('media_type', 'sub')
            
            mapping_func = EPISODES_MSG_IDS.get(season_num, {}).get(media_type)
            if mapping_func:
                msg_id = mapping_func(ep_num)
                await context.bot.copy_message(
                    chat_id=chat_id,
                    from_chat_id=CHANNEL_ID,
                    message_id=msg_id
                )
            else:
                await update.message.reply_text("عذراً، هذه الحلقة غير متوفرة برابط مباشر حالياً.")
        except Exception as e:
            logger.error(f"Error fetching episode: {e}")
            await update.message.reply_text("عذراً، حدث خطأ أثناء إحضار الحلقة.")
        return

# إعداد خادم الويب الوهمي لإبقاء البوت مستيقظاً على Render
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is active and running 24/7!")

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

def main():
    # تشغيل السيرفر الوهمي في خيط منفصل (Thread) لضمان الاستجابة لطلبات الـ Keep-Alive
    server_thread = threading.Thread(target=run_web_server, daemon=True)
    server_thread.start()

    # تشغيل بوت تيليجرام مع حماية لإعادة الاتصال تلقائياً عند أي سقوط أو انقطاع
    while True:
        try:
            application = Application.builder().token(TOKEN).build()

            application.add_handler(CommandHandler("start", start))
            application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

            logger.info("Starting Telegram bot polling...")
            application.run_polling(drop_pending_updates=True)
        except Exception as e:
            logger.error(f"Bot polling crashed with error: {e}. Restarting in 5 seconds...")
            time.sleep(5)

if __name__ == '__main__':
    main()
