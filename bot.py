import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes

TOKEN = "8695639459:AAER1q0_wgQazZZnfHjRIPMOInKntGM93ac"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# جدول أعداد الحلقات الحقيقية لكل جزء (مترجم ومدبلج)
SEASONS_EPISODES = {
    "sub": {1: 55, 2: 42, 3: 63, 4: 30, 5: 35, 6: 33, 7: 31, 8: 47, 9: 34, 10: 37, 11: 0},
    "dubbed": {1: 86, 2: 42, 3: 63, 4: 31, 5: 35, 6: 33, 7: 34, 8: 34, 9: 34, 10: 47, 11: 0}
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🎬 مسلسل وادي الذئاب", callback_data="valley_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text("أهلاً بك في بوت مسلسل وادي الذئاب الرسمي!\nاضغط على الزر أدناه للبدء:", reply_markup=reply_markup)

async def valley_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("🎙️ مدبلج", callback_data="dubbed_seasons"), InlineKeyboardButton("📝 مترجم", callback_data="subtitled_seasons")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text="اختر نوع النسخة (مترجم أو مدبلج):", reply_markup=reply_markup)

async def show_seasons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    version_type = "dubbed" if "dubbed" in data else "sub"
    keyboard = []
    row = []
    for i in range(1, 12):
        name = f"الجزء {i}"
        if i == 11:
            name += " (متوقف)"
        row.append(InlineKeyboardButton(name, callback_data=f"season_{version_type}_{i}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="valley_main")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    title = "المترجم" if version_type == "sub" else "المدبلج"
    await query.edit_message_text(text=f"أنت تصفح حلقات وادي الذئاب ({title}).\nاختر الجزء المطلوب:", reply_markup=reply_markup)

async def show_episodes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    parts = data.split("_")
    v_type = parts[1]
    season_num = int(parts[2])
    
    # فحص الجزء الحادي عشر المتوقف
    if season_num == 11:
        keyboard = [[InlineKeyboardButton("🔙 رجوع للأجزاء", callback_data=f"{'dubbed' if v_type=='dubbed' else 'subtitled'}_seasons")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text="عذراً، الجزء الحادي عشر تم توقيف عرضه لأسباب غير معروفة.", reply_markup=reply_markup)
        return

    keyboard = []
    row = []
    total_episodes = SEASONS_EPISODES.get(v_type, {}).get(season_num, 30)
    
    for ep in range(1, total_episodes + 1):
        row.append(InlineKeyboardButton(f"الحلقة {ep}", callback_data=f"play_{v_type}_{season_num}_{ep}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
        
    back_callback = "dubbed_seasons" if v_type == "dubbed" else "subtitled_seasons"
    keyboard.append([InlineKeyboardButton("🔙 رجوع للأجزاء", callback_data=back_callback)])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=f"أنت في الجزء ({season_num}) - نسخة ({'مترجم' if v_type=='sub' else 'مدبلج'}).\nاختر الحلقة:", reply_markup=reply_markup)

async def send_episode_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    parts = data.split("_")
    v_type = parts[1]
    season = parts[2]
    ep = parts[3]
    
    # قاعدة بيانات معرفات الحلقات
    episodes_db = {
        "sub_1_1": "وضع_معرف_ملف_الحلقة_هنا"
    }
    
    key = f"{v_type}_{season}_{ep}"
    file_id = episodes_db.get(key)
    if file_id and file_id != "وضع_معرف_ملف_الحلقة_هنا":
        await context.bot.send_video(chat_id=query.message.chat_id, video=file_id, caption=f"وادي الذئاب ({'مترجم' if v_type=='sub' else 'مدبلج'}) - الجزء {season} - الحلقة {ep}")
    else:
        await query.message.reply_text(f"عذراً، الحلقة {ep} من الجزء {season} ({'مترجم' if v_type=='sub' else 'مدبلج'})\nقريباً سيتم رفعها وتحديثها في البوت!")

async def back_to_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("🎬 مسلسل وادي الذئاب", callback_data="valley_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text="القائمة الرئيسية:", reply_markup=reply_markup)

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(valley_main, pattern="^valley_main$"))
    app.add_handler(CallbackQueryHandler(show_seasons, pattern="^(dubbed_seasons|subtitled_seasons)$"))
    app.add_handler(CallbackQueryHandler(show_episodes, pattern="^season_(sub|dubbed)_\\d+$"))
    app.add_handler(CallbackQueryHandler(send_episode_file, pattern="^play_(sub|dubbed)_"))
    app.add_handler(CallbackQueryHandler(back_to_start, pattern="^back_to_start$"))
    print("البوت يعمل الآن بنجاح...")
    app.run_polling()

if __name__ == "__main__":
    main()
