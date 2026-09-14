import logging
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# إعداد السجلات
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# التوكن الخاص بك
TOKEN = "8695639459:AAGNc7Y-9ShCxgQTKAml90FNpv0yAoDt3Ts"
CHANNEL_ID = -1001234567890  

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
    11: {"sub": 0, "dub": 0}
}

EPISODES_MSG_IDS = {
    (1, "sub"): {1: 15},
    (1, "dub"): {1: 102}
}

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
                keyboard.append([InlineKeyboardButton(f"⚠️ الموسم 11 ({type_name}) - متوقف", callback_data=f"season_{media_type}_{season}")])
            else:
                count = SEASONS_EPISODES[season][media_type]
                row.append(InlineKeyboardButton(f"الموسم {season} ({count} حلقة)", callback_data=f"season_{media_type}_{season}"))
                if len(row) == 2:
                    keyboard.append(row)
                    row = []
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")])
        await query.edit_message_text(text=f"📂 اختر الموسم المطلوب ({type_name}):", reply_markup=InlineKeyboardMarkup(keyboard))

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
        await query.edit_message_text(text=f"🎬 اختر الحلقة من الموسم {season_num}:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("ep_"):
        parts = data.split("_")
        media_type = parts[1]
        season_num = int(parts[2])
        ep_num = int(parts[3])
        
        msg_id = EPISODES_MSG_IDS.get((season_num, media_type), {}).get(ep_num)
        if msg_id:
            try:
                await context.bot.copy_message(chat_id=query.message.chat_id, from_chat_id=CHANNEL_ID, message_id=msg_id)
            except Exception as e:
                await query.message.reply_text("⚠️ حدث خطأ أثناء جلب الحلقة، تأكد من أن البوت مشرف في القناة.")
        else:
            await query.message.reply_text(f"⚠️ عذراً، حلقة الموسم {season_num} - الحلقة {ep_num} لم يتم ربطها بعد.")

    elif data == "main_menu":
        keyboard = [[InlineKeyboardButton("🎬 النسخة المترجمة", callback_data="type_sub"), InlineKeyboardButton("🎙️ النسخة المدبلجة", callback_data="type_dub")]]
        await query.edit_message_text(text="🐺 **أهلاً بك مجدداً. اختر النسخة:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# --- تشغيل سيرفر خفيف في الخلفية لترضية رندر ---
def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), BaseHTTPRequestHandler)
    server.serve_forever()

def main():
    # تشغيل سيرفر الويب في خيط خلفي هادئ
    server_thread = threading.Thread(target=run_web_server, daemon=True)
    server_thread.start()

    # تشغيل البوت بالطريقة النظامية المباشرة في الخيط الرئيسي
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # استخدام مرسل الإشارات المعطل لتجنب أي مشاكل مع الخيوط
    application.run_polling(stop_signals=None)

if __name__ == "__main__":
    main()
