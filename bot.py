import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes

# توكن البوت الخاص بك
TOKEN = "8695639459:AAER1q0_wgQazZZnfHjRIPMOInKntGM93ac"

# إعدادات سجل الأخطاء للتتبع
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


# 1. أمر البداية /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  keyboard = [
      [InlineKeyboardButton("🎬 مسلسل وادي الذئاب", callback_data="valley_main")]
  ]
  reply_markup = InlineKeyboardMarkup(keyboard)

  if update.message:
    await update.message.reply_text(
        "أهلاً بك في بوت مسلسل وادي الذئاب الرسمي!\nاضغط على الزر أدناه للبدء:",
        reply_markup=reply_markup,
    )


# 2. القائمة الرئيسية لوادي الذئاب (مترجم أو مدبلج)
async def valley_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.callback_query
  await query.answer()

  keyboard = [
      [
          InlineKeyboardButton("🎙️ مدبلج", callback_data="dubbed_seasons"),
          InlineKeyboardButton("📝 مترجم", callback_data="subtitled_seasons"),
      ],
      [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_start")],
  ]
  reply_markup = InlineKeyboardMarkup(keyboard)
  await query.edit_message_text(
      text="اختر نوع النسخة (مترجم أو مدبلج):", reply_markup=reply_markup
  )


# 3. عرض الأجزاء من 1 إلى 11 (سواء لمترجم أو مدبلج)
async def show_seasons(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.callback_query
  await query.answer()

  data = query.data  # لمعرفة هل هو مترجم أم مدبلج
  version_type = "dubbed" if "dubbed" in data else "sub"

  # إنشاء أزرار للأجزاء من 1 إلى 11 بشكل مرتب
  keyboard = []
  row = []
  for i in range(1, 12):
    row.append(
        InlineKeyboardButton(
            f"الجزء {i}", callback_data=f"season_{version_type}_{i}"
        )
    )
    if len(row) == 3:  # 3 أزرار في كل سطر
      keyboard.append(row)
      row = []
  if row:
    keyboard.append(row)

  # زر الرجوع
  keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="valley_main")])

  reply_markup = InlineKeyboardMarkup(keyboard)
  title = "المترجم" if version_type == "sub" else "المدبلج"
  await query.edit_message_text(
      text=f"أنت تصفح حلقات وادي الذئاب ({title}).\nاختر الجزء المطلوب:",
      reply_markup=reply_markup,
  )


# 4. عرض الحلقات الخاصة بالجزء المحدد
async def show_episodes(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.callback_query
  await query.answer()

  data = query.data
  parts = data.split("_")
  v_type = parts[1]  # sub أو dubbed
  season_num = parts[2]  # رقم الجزء

  keyboard = [
      [
          InlineKeyboardButton(
              "الحلقة 1", callback_data=f"play_{v_type}_{season_num}_1"
          ),
          InlineKeyboardButton(
              "الحلقة 2", callback_data=f"play_{v_type}_{season_num}_2"
          ),
      ],
      [
          InlineKeyboardButton(
              "الحلقة 3", callback_data=f"play_{v_type}_{season_num}_3"
          ),
          InlineKeyboardButton(
              "الحلقة 4", callback_data=f"play_{v_type}_{season_num}_4"
          ),
      ],
      [
          InlineKeyboardButton(
              "🔙 رجوع للأجزاء", callback_data=f"{v_type}_seasons"
          )
      ],
  ]
  reply_markup = InlineKeyboardMarkup(keyboard)

  await query.edit_message_text(
      text=f"أنت في الجزء ({season_num}) - نسخة ({'مترجم' if v_type=='sub' else 'مدبلج'}).\nاختر الحلقة:",
      reply_markup=reply_markup,
  )


# 5. إرسال الحلقة للمستخدم عند الضغط عليها
async def send_episode_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.callback_query
  await query.answer()

  data = query.data
  parts = data.split("_")
  v_type = parts[1]
  season = parts[2]
  ep = parts[3]

  episodes_db = {
      "sub_1_1": "وضع_معرف_ملف_الحلقة_هنا_مثلاً",
  }

  key = f"{v_type}_{season}_{ep}"
  file_id = episodes_db.get(key)

  if file_id and file_id != "وضع_معرف_ملف_الحلقة_هنا_مثلاً":
    await context.bot.send_video(
        chat_id=query.message.chat_id,
        video=file_id,
        caption=f"وادي الذئاب ({'مترجم' if v_type=='sub' else 'مدبلج'}) - الجزء {season} - الحلقة {ep}",
    )
  else:
    await query.message.reply_text(
        f"عذراً، الحلقة {ep} من الجزء {season} ({'مترجم' if v_type=='sub' else 'مدبلج'})\nقريباً سيتم رفعها وتحديثها في البوت!"
    )


# دالة العودة للبداية
async def back_to_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.callback_query
  await query.answer()
  keyboard = [
      [InlineKeyboardButton("🎬 مسلسل وادي الذئاب", callback_data="valley_main")]
  ]
  reply_markup = InlineKeyboardMarkup(keyboard)
  await query.edit_message_text(
      text="القائمة الرئيسية:", reply_markup=reply_markup
  )


# تشغيل البوت وربط الدوال بالأزرار
def main():
  app = ApplicationBuilder().token(TOKEN).build()

  app.add_handler(CommandHandler("start", start))
  app.add_handler(
      CallbackQueryHandler(valley_main, pattern="^valley_main$")
  )
  app.add_handler(
      CallbackQueryHandler(
          show_seasons, pattern="^(dubbed_seasons|subtitled_seasons)$"
      )
  )
  app.add_handler(
      CallbackQueryHandler(show_episodes, pattern="^season_(sub|dubbed)_\\d+$")
  )
  app.add_handler(
      CallbackQueryHandler(send_episode_file, pattern="^play_(sub|dubbed)_")
  )
  app.add_handler(
      CallbackQueryHandler(back_to_start, pattern="^back_to_start$")
  )

  print("البوت يعمل الآن بنجاح...")
  app.run_polling()


if __name__ == "__main__":
  main()
