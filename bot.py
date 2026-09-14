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

# 📂 ربط الحلقات بناءً على أرقام الرسائل في قناتك الخاصة
EPISODES_MSG_IDS = {
    (1, "sub"): {
        1: 4,   2: 5,   3: 6,   4: 7,   5: 8,
        6: 9,   7: 10,  8: 11,  9: 12,  10: 13,
        11: 14, 12: 15, 13: 16, 14: 17, 15: 18,
        16: 19, 17: 20, 18: 21, 19: 22, 20: 23,
        21: 24, 22: 25, 23: 26, 24: 27, 25: 28,
        26: 29, 27: 30, 28: 31, 29: 32, 30: 33,
        31: 34, 32: 35, 33: 36, 34: 37, 35: 38,
        36: 39, 37: 40, 38: 41, 39: 42, 40: 43,
        41: 44, 42: 45, 43: 46, 44: 47, 45: 48,
        46: 49, 47: 50, 48: 51, 49: 52, 50: 53,
        51: 54, 52: 55, 53: 56, 54: 57, 55: 58
    },
    (2, "sub"): {
        1: 60,  2: 61,  3: 62,  4: 63,  5: 64,
        6: 65,  7: 66,  8: 67,  9: 68,  10: 69,
        11: 70, 12: 71, 13: 72, 14: 73, 15: 74,
        16: 75, 17: 76, 18: 77, 19: 78, 20: 79,
        21: 80, 22: 81, 23: 82, 24: 83, 25: 84,
        26: 85, 27: 86, 28: 87, 29: 88, 30: 89,
        31: 90, 32: 91, 33: 92, 34: 93, 35: 94,
        36: 95, 37: 96, 38: 97, 39: 98, 40: 99,
        41: 100, 42: 101
    },
    (3, "sub"): {
        1: 103, 2: 104, 3: 105, 4: 106, 5: 107,
        6: 108, 7: 109, 8: 110, 9: 111, 10: 112,
        11: 113, 12: 114, 13: 115, 14: 116, 15: 117,
        16: 118, 17: 119, 18: 120, 19: 121, 20: 122,
        21: 123, 22: 124, 23: 125, 24: 126, 25: 127,
        26: 128, 27: 129, 28: 130, 29: 131, 30: 132,
        31: 133, 32: 134, 33: 135, 34: 136, 35: 137,
        36: 138, 37: 139, 38: 140, 39: 141, 40: 142,
        41: 143, 42: 144, 43: 145, 44: 146, 45: 147,
        46: 148, 47: 149, 48: 150, 49: 151, 50: 152,
        51: 153, 52: 154, 53: 155, 54: 156, 55: 157,
        56: 158, 57: 159, 58: 160, 59: 161, 60: 162,
        61: 163, 62: 164
    },
    (1, "dub"): {
        # سيتم ملؤها لاحقاً
    }
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
                await query.message.reply_text("⚠️ حدث خطأ أثناء جلب الحلقة، تأكد من أن البوت مشرف في القناة وأن معرف القناة صحيح.")
        else:
            await query.message.reply_text(f"⚠️ عذراً، حلقة الموسم {season_num} - الحلقة {ep_num} لم يتم ربطها بعد.")

    elif data == "main_menu":
        keyboard = [[InlineKeyboardButton("🎬 النسخة المترجمة", callback_data="type_sub"), InlineKeyboardButton("🎙️ النسخة المدبلجة", callback_data="type_dub")]]
        await query.edit_message_text(text="🐺 **أهلاً بك مجدداً. اختر النسخة:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

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
    application.run_polling(stop_signals=None)

if __name__ == "__main__":
    main()
