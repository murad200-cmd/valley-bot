
import logging
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# إعداد السجلات
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# التوكن الصحيح والكامل للبوت
TOKEN = "8695639459:AAEdjd-BqUway2ZFFh0kB1jRAgjiDybZjRQ"

# 📌 معرف قناتك (يجب أن يبدأ بـ -100 وأن يكون البوت مشرفاً فيها)
CHANNEL_ID = -1001234567890  

# أعداد الحلقات الحقيقية لجميع المواسم (الترتيب: مترجم، مدبلج)
SEASONS_EPISODES = {
    1: {"sub": 55, "dub": 86},
    2: {"sub": 42, "dub": 42},
    3: {"sub": 30, "dub": 30},
    4: {"sub": 37, "dub": 37},
    5: {"sub": 34, "dub": 34},
    6: {"sub": 36, "dub": 36},
    7: {"sub": 38, "dub": 38},
    8: {"sub": 39, "dub": 39},
    9: {"sub": 39, "dub": 39},
    10: {"sub": 39, "dub": 39},
    11: {"sub": 0, "dub": 0}  # متوقف
}

# 📥 قاموس أرقام رسائل الحلقات داخل قناتك
EPISODES_MSG_IDS = {
    (1, "sub"): {
        1: 15,  # مثال: الحلقة 1 مترجمة في الرسالة رقم 15
    },
    (1, "dub"): {
        1: 102, # مثال: الحلقة 1 مدبلجة في الرسالة رقم 102
    }
}

# أمر البدء /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("🎬 النسخة المترجمة", callback_data="type_sub"),
            InlineKeyboardButton("🎙️ النسخة المدبلجة", callback_data="type_dub")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🐺 **أهلاً بك في بوت مسلسل وادي الذئاب الرسمي**\n\nاختر النسخة التي تود متابعتها:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# معالجة الأزرار
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("type_"):
        media_type = data.split("_")[1]
        type_name = "مترجم" if media_type == "sub" else "مدبلج"
        
        keyboard = []
        row = []
        
        for season in range(1, 12):
            if season == 11:
                if row:
                    keyboard.append(row)
                    row = []
                btn_text = f"⚠️ الموسم 11 ({type_name}) - متوقف"
                keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"season_{media_type}_{season}")])
            else:
                count = SEASONS_EPISODES[season][media_type]
                btn_text = f"الموسم {season} ({count} حلقة)"
                row.append(InlineKeyboardButton(btn_text, callback_data=f"season_{media_type}_{season}"))
                
                if len(row) == 2:
                    keyboard.append(row)
                    row = []
        
        if row:
            keyboard.append(row)
            
        keyboard.append([InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=f"📂 اختر الموسم المطلوب ({type_name}):", reply_markup=reply_markup)

    elif data.startswith("season_"):
        parts = data.split("_")
        media_type = parts[1]
        season_num = int(parts[2])

        if season_num == 11:
            await query.edit_message_text(
                text="⚠️ **عذراً، الموسم الحادي عشر متوقف حالياً وغير متوفر.**",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع للمواسم", callback_data=f"type_{media_type}")]]),
                parse_mode="Markdown"
            )
            return

        total_episodes = SEASONS_EPISODES[season_num][media_type]
        keyboard = []
        row = []
        
        for ep in range(1, total_episodes + 1):
            row.append(InlineKeyboardButton(f"ح {ep}", callback_data=f"ep_{media_type}_{season_num}_{ep}"))
            if len(row) == 4:
                keyboard.append(row)
                row = []
                
        if row:
            keyboard.append(row)
            
        keyboard.append([InlineKeyboardButton("🔙 رجوع للمواسم", callback_data=f"type_{media_type}")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=f"🎬 اختر الحلقة من الموسم {season_num}:", reply_markup=reply_markup)

    elif data.startswith("ep_"):
        parts = data.split("_")
        media_type = parts[1]
        season_num = int(parts[2])
        ep_num = int(parts[3])
        
        msg_id = EPISODES_MSG_IDS.get((season_num, media_type), {}).get(ep_num)
        
        if msg_id:
            try:
                await context.bot.copy_message(
                    chat_id=query.message.chat_id,
                    from_chat_id=CHANNEL_ID,
                    message_id=msg_id
                )
            except Exception as e:
                await query.message.reply_text("⚠️ حدث خطأ أثناء جلب الحلقة، تأكد من أن البوت مشرف في القناة.")
        else:
            await query.message.reply_text(
                f"⚠️ عذراً، حلقة الموسم {season_num} - الحلقة {ep_num} لم يتم ربطها بعد."
            )

    elif data == "main_menu":
        keyboard = [
            [
                InlineKeyboardButton("🎬 النسخة المترجمة", callback_data="type_sub"),
                InlineKeyboardButton("🎙️ النسخة المدبلجة", callback_data="type_dub")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text="🐺 **أهلاً بك مجدداً. اختر النسخة:**", reply_markup=reply_markup, parse_mode="Markdown")

# --- سيرفر ويب وهمي لإبقاء البت مفتوحاً على Render ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running successfully!")

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

def main():
    # تشغيل سيرفر الويب في خلفية النظام لترضية رندر
    server_thread = threading.Thread(target=run_web_server, daemon=True)
    server_thread.start()

    # تشغيل البوت
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))

    application.run_polling()

if __name__ == "__main__":
    main()
