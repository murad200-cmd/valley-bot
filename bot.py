import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# إعداد السجلات
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# التوكن الجديد للبوت
TOKEN = "AAEwR7y2bvHFnMBC2JZAo1d9UaKw9I8DCQc"

# أعداد الحلقات الحقيقية لجميع المواسم (الترتيب: مترجم، مدبلج)
# الموسم 11 متوقف (Discontinued)
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

# قاعدة بيانات وهمية لتخزين file_id للحلقات (يمكنك تعبئتها لاحقاً)
episodes_db = {
    # مثال: (الموسم، النوع، رقم الحلقة): "file_id_here"
}

# أمر البدء /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("🎬 مترجم", callback_data="type_sub"),
            InlineKeyboardButton("🎙️ مدبلج", callback_data="type_dub")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "أهلاً بك في بوت مسلسل وادي الذئاب الرسمي.\nاختر النسخة التي تود متابعتها:",
        reply_markup=reply_markup
    )

# معالجة الأزرار
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("type_"):
        media_type = data.split("_")[1]  # sub أو dub
        type_name = "مترجم" if media_type == "sub" else "مدبلج"
        
        keyboard = []
        for season in range(1, 12):
            if season == 11:
                btn_text = f"الموسم 11 ({type_name}) - ⚠️ متوقف"
            else:
                count = SEASONS_EPISODES[season][media_type]
                btn_text = f"الموسم {season} ({type_name}) - {count} حلقة"
            
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"season_{media_type}_{season}")])
        
        keyboard.append([InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=f"اختر الموسم ({type_name}):", reply_markup=reply_markup)

    elif data.startswith("season_"):
        parts = data.split("_")
        media_type = parts[1]
        season_num = int(parts[2])

        if season_num == 11:
            await query.edit_message_text(
                text="⚠️ عذراً، الموسم الحادي عشر متوقف حالياً وغير متوفر.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع للمواسم", callback_data=f"type_{media_type}")]])
            )
            return

        total_episodes = SEASONS_EPISODES[season_num][media_type]
        keyboard = []
        
        # أزرار الحلقات (مثال توضيحي لتقسيم الحلقات)
        for ep in range(1, total_episodes + 1):
            keyboard.append([InlineKeyboardButton(D2A(ep), callback_data=f"ep_{media_type}_{season_num}_{ep}")])
            
        keyboard.append([InlineKeyboardButton("🔙 رجوع للمواسم", callback_data=f"type_{media_type}")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=f"اختر الحلقة من الموسم {season_num}:", reply_markup=reply_markup)

    elif data == "main_menu":
        keyboard = [
            [
                InlineKeyboardButton("🎬 مترجم", callback_data="type_sub"),
                InlineKeyboardButton("🎙️ مدبلج", callback_data="type_dub")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text="أهلاً بك مجدداً. اختر النسخة:", reply_markup=reply_markup)

# دالة مساعدة لتنسيق رقم الحلقة
def D2A(ep):
    return f"الحلقة {ep}"

def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))

    application.run_polling()

if __name__ == "__main__":
    main()
