import logging
import os
import threading
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.constants import ChatMemberStatus
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ============================================================
# إعداد السجلات
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)

# 
# ============================================================
# التوكن
# ============================================================

TOKEN = "8695639459:AAGJ6JGYbCIky9CuosFYF6oEDze5rypI4pY"

if not TOKEN:
    raise RuntimeError("لم يتم العثور على توكن البوت")
# ============================================================
# القنوات
# ============================================================

CHANNEL_ID = -1003924784582
ADMIN_CHANNEL_ID = -1003956613480

# ============================================================
# الإحصائيات
# ============================================================

unique_users = set()
daily_visits = set()
daily_active_users = set()

daily_errors_count = 0
total_episode_views = 0

episode_views = {}
user_last_watched = {}
user_profiles = {}
banned_users = set()

# ============================================================
# عدد الحلقات
# ============================================================

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
    11: {"sub": 0, "dub": 0},
}

# ============================================================
# أرقام رسائل الحلقات داخل قناة المحتوى
# ============================================================

EPISODES_MSG_IDS = {
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

# ============================================================
# لوحة المستخدم الرئيسية
# ============================================================

def get_main_keyboard():
    return ReplyKeyboardMarkup(
        [
            [
                KeyboardButton("🎬 النسخة المترجمة"),
                KeyboardButton("🎙️ النسخة المدبلجة"),
            ],
            [
                KeyboardButton("📺 آخر حلقة شاهدتها")
            ],
        ],
        resize_keyboard=True,
    )

# ============================================================
# الوقت
# ============================================================

def now_string():
    return datetime.now().astimezone().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

# ============================================================
# تنظيف النص
# ============================================================

def safe_text(text, limit=3000):
    if not text:
        return "لا يوجد"

    text = str(text)
    text = text.replace("\\", "\\\\")
    text = text.replace("`", "\\`")

    return text[:limit]

# ============================================================
# معلومات المستخدم
# ============================================================

def get_user_info(user):
    username = (
        f"@{user.username}"
        if user.username
        else "لا يوجد معرف"
    )

    full_name = (
        f"{user.first_name or ''} "
        f"{user.last_name or ''}"
    ).strip()

    return {
        "id": user.id,
        "name": full_name or "بدون اسم",
        "username": username,
    }

# ============================================================
# التحقق من مشرف قناة الإدارة
# ============================================================

async def is_admin_in_channel(context, user_id):
    try:
        member = await context.bot.get_chat_member(
            chat_id=ADMIN_CHANNEL_ID,
            user_id=user_id,
        )

        return member.status in (
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER,
        )

    except Exception:
        logger.exception("فشل التحقق من صلاحيات المدير")
        return False

# ============================================================
# حفظ معلومات المستخدم
# ============================================================

def ensure_user_profile(user):
    if user.id not in user_profiles:
        user_profiles[user.id] = {
            "first_seen": now_string(),
            "last_seen": now_string(),
            "phone": None,
            "username": user.username,
            "name": user.full_name,
        }
    else:
        user_profiles[user.id]["last_seen"] = now_string()
        user_profiles[user.id]["username"] = user.username
        user_profiles[user.id]["name"] = user.full_name

# ============================================================
# تقييم الرسائل غير المسموحة
# ============================================================

def evaluate_message_risk(message):

    if message.text:
        text = message.text.lower()

        dangerous_words = [
            "hack",
            "hacking",
            "virus",
            "malware",
            "exploit",
            "phishing",
            "spam",
            "اختراق",
            "تهكير",
            "فيروس",
            "برمجية خبيثة",
            "تصيد",
            "سبام",
        ]

        if any(word in text for word in dangerous_words):
            return (
                "🔴 مرتفع",
                "النص يحتوي على كلمات تستدعي مراجعة الإدارة.",
            )

        return (
            "🟡 متوسط",
            "رسالة نصية خارج نظام أزرار البوت.",
        )

    if message.photo:
        return "🟡 متوسط", "صورة مرسلة خارج النظام."

    if message.video:
        return "🟡 متوسط", "فيديو مرسل خارج النظام."

    if message.document:
        return "🟠 مرتفع", "ملف مرسل خارج النظام."

    if message.audio:
        return "🟡 متوسط", "ملف صوتي مرسل خارج النظام."

    if message.voice:
        return "🟡 متوسط", "رسالة صوتية مرسلة خارج النظام."

    if message.video_note:
        return "🟡 متوسط", "فيديو دائري مرسل خارج النظام."

    if message.animation:
        return "🟡 متوسط", "صورة متحركة مرسلة خارج النظام."

    if message.contact:
        return "🟡 متوسط", "جهة اتصال مرسلة خارج النظام."

    if message.location:
        return "🟠 مرتفع", "موقع جغرافي مرسل خارج النظام."

    if message.venue:
        return "🟠 مرتفع", "مكان مرسل خارج النظام."

    return "🟡 متوسط", "نوع رسالة غير مسموح به."

# ============================================================
# إرسال نشاط المستخدم للإدارة
# ============================================================

async def send_user_activity_to_admin(
    context,
    user,
    status,
    event="start",
):

    ensure_user_profile(user)

    info = get_user_info(user)
    profile = user_profiles[user.id]

    phone = profile.get("phone") or "غير متوفر"

    last_watch = user_last_watched.get(user.id)

    if last_watch:
        type_name = (
            "مترجمة 🎬"
            if last_watch["type"] == "sub"
            else "مدبلجة 🎙️"
        )

        last_episode = (
            f"{type_name} | "
            f"الجزء {last_watch['season']} | "
            f"الحلقة {last_watch['ep']}"
        )
    else:
        last_episode = "لم يشاهد أي حلقة"

    report = (
        "👤 **نشاط مستخدم**\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"📌 الحالة: {status}\n"
        f"📛 الاسم: {safe_text(info['name'], 500)}\n"
        f"🔗 المعرف: {safe_text(info['username'], 500)}\n"
        f"🆔 User ID: `{info['id']}`\n"
        f"💬 Chat ID: `{user.id}`\n"
        f"📱 رقم الهاتف: `{safe_text(phone, 100)}`\n\n"
        f"📅 أول استخدام: `{profile['first_seen']}`\n"
        f"🕐 آخر نشاط: `{profile['last_seen']}`\n"
        f"📺 آخر حلقة: `{safe_text(last_episode, 500)}`\n\n"
        f"📊 إجمالي المستخدمين: **{len(unique_users)}**\n"
        f"🟢 الحدث: `{safe_text(event, 200)}`\n"
        "━━━━━━━━━━━━━━━━━━"
    )

    try:
        await context.bot.send_message(
            chat_id=ADMIN_CHANNEL_ID,
            text=report,
            parse_mode="Markdown",
        )
    except Exception:
        logger.exception("فشل إرسال معلومات المستخدم")

# ============================================================
# /start
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    if not user:
        return

    if user.id in banned_users:
        await update.effective_message.reply_text(
            "🚫 تم حظرك من استخدام هذا البوت."
        )
        return

    ensure_user_profile(user)

    is_new = user.id not in unique_users

    if is_new:
        unique_users.add(user.id)
        status = "🆕 مستخدم جديد تماماً"
    else:
        status = "🔄 مستخدم قديم"

    daily_visits.add(user.id)
    daily_active_users.add(user.id)

    await send_user_activity_to_admin(
        context,
        user,
        status,
        event="/start",
    )

    await update.effective_message.reply_text(
        "🐺 **أهلاً بك في بوت مسلسل وادي الذئاب الرسمي**\n\n"
        "اختر من الأزرار في الأسفل:",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown",
    )

# ============================================================
# تقرير الرسائل غير المسموحة
# ============================================================

async def report_unauthorized_message(update, context):

    user = update.effective_user
    message = update.effective_message

    if not user or not message:
        return

    ensure_user_profile(user)

    info = get_user_info(user)
    profile = user_profiles[user.id]

    risk, reason = evaluate_message_risk(message)

    phone = profile.get("phone") or "غير متوفر"

    if message.text:
        message_type = "📝 نص"
    elif message.photo:
        message_type = "🖼️ صورة"
    elif message.video:
        message_type = "🎥 فيديو"
    elif message.document:
        message_type = "📄 ملف"
    elif message.audio:
        message_type = "🎵 صوت"
    elif message.voice:
        message_type = "🎤 رسالة صوتية"
    elif message.video_note:
        message_type = "⭕ فيديو دائري"
    elif message.animation:
        message_type = "🎞️ صورة متحركة"
    elif message.contact:
        message_type = "📞 جهة اتصال"
    elif message.location:
        message_type = "📍 موقع"
    elif message.venue:
        message_type = "📍 مكان"
    else:
        message_type = "📦 نوع آخر"

    report = (
        "🚨 **رسالة خارج الأزرار**\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "👤 **معلومات المستخدم**\n\n"
        f"📛 الاسم: {safe_text(info['name'], 500)}\n"
        f"🔗 المعرف: {safe_text(info['username'], 500)}\n"
        f"🆔 User ID: `{info['id']}`\n"
        f"💬 Chat ID: `{user.id}`\n"
        f"📱 الهاتف: `{safe_text(phone, 100)}`\n"
        f"📅 أول استخدام: `{profile['first_seen']}`\n"
        f"🕐 آخر نشاط: `{profile['last_seen']}`\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "📨 **معلومات الرسالة**\n\n"
        f"📦 النوع: **{message_type}**\n"
        f"⚠️ تقييم الخطر: **{risk}**\n"
        f"🔎 السبب: {safe_text(reason, 1000)}\n"
        f"🆔 Message ID: `{message.message_id}`\n"
        f"🕐 الوقت: `{now_string()}`\n"
    )

    if message.text:
        report += (
            "\n💬 **محتوى الرسالة:**\n"
            f"`{safe_text(message.text, 3000)}`\n"
        )

    report += (
        "\n━━━━━━━━━━━━━━━━━━\n"
        "👇 **اختر الإجراء:**"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🚫 حظر المستخدم",
                    callback_data=f"BAN:{user.id}",
                ),
                InlineKeyboardButton(
                    "✅ إبقاء المستخدم",
                    callback_data=f"KEEP:{user.id}",
                ),
            ]
        ]
    )

    try:
        await context.bot.send_message(
            chat_id=ADMIN_CHANNEL_ID,
            text=report,
            parse_mode="Markdown",
            reply_markup=keyboard,
        )
    except Exception:
        logger.exception("فشل إرسال تقرير الرسالة")

    # نسخ الرسالة مباشرة من Telegram
    # بدون تحميلها إلى Render
    try:
        await context.bot.copy_message(
            chat_id=ADMIN_CHANNEL_ID,
            from_chat_id=message.chat_id,
            message_id=message.message_id,
        )
    except Exception:
        logger.exception("فشل نسخ الرسالة إلى قناة الإدارة")

# ============================================================
# التعامل مع الرسائل
# ============================================================

async def handle_messages(update, context):

    global total_episode_views

    message = update.effective_message
    user = update.effective_user

    if not message or not user:
        return

    user_id = user.id

    if user_id in banned_users:
        try:
            await message.delete()
        except Exception:
            pass
        return

    ensure_user_profile(user)
    daily_active_users.add(user_id)

    # ========================================================
    # رقم الهاتف إذا شاركه المستخدم بنفسه
    # ========================================================

    if message.contact:

        if message.contact.user_id == user_id:

            user_profiles[user_id]["phone"] = (
                message.contact.phone_number
            )

            try:
                await context.bot.send_message(
                    chat_id=ADMIN_CHANNEL_ID,
                    text=(
                        "📱 **تم استلام رقم هاتف المستخدم**\n\n"
                        f"👤 الاسم: {safe_text(user.full_name, 500)}\n"
                        f"🔗 المعرف: "
                        f"{safe_text('@' + user.username if user.username else 'لا يوجد', 500)}\n"
                        f"🆔 User ID: `{user_id}`\n"
                        f"📱 الهاتف: `{safe_text(message.contact.phone_number, 100)}`\n"
                        f"📅 الوقت: `{now_string()}`"
                    ),
                    parse_mode="Markdown",
                )
            except Exception:
                logger.exception("فشل تسجيل رقم الهاتف")

        else:
            await report_unauthorized_message(
                update,
                context,
            )

        return

    text = message.text

    # ========================================================
    # النسخة المترجمة
    # ========================================================

    if text == "🎬 النسخة المترجمة":

        context.user_data["media_type"] = "sub"

        keyboard = []
        row = []

        for season in range(1, 12):

            if season == 11:

                if row:
                    keyboard.append(row)
                    row = []

                keyboard.append(
                    [
                        KeyboardButton(
                            "⚠️ الجزء 11 (مترجم) - متوقف"
                        )
                    ]
                )

            else:

                count = SEASONS_EPISODES[season]["sub"]

                row.append(
                    KeyboardButton(
                        f"مترجم - الجزء {season} ({count} ح)"
                    )
                )

                if len(row) == 2:
                    keyboard.append(row)
                    row = []

        if row:
            keyboard.append(row)

        keyboard.append(
            [
                KeyboardButton("🔙 القائمة الرئيسية")
            ]
        )

        await message.reply_text(
            "📂 اختر الجزء المطلوب (المترجم):",
            reply_markup=ReplyKeyboardMarkup(
                keyboard,
                resize_keyboard=True,
            ),
        )

        return

    # ========================================================
    # النسخة المدبلجة
    # ========================================================

    if text == "🎙️ النسخة المدبلجة":

        context.user_data["media_type"] = "dub"

        keyboard = []
        row = []

        for season in range(1, 12):

            if season == 11:

                if row:
                    keyboard.append(row)
                    row = []

                keyboard.append(
                    [
                        KeyboardButton(
                            "⚠️ الجزء 11 (مدبلج) - متوقف"
                        )
                    ]
                )

            else:

                count = SEASONS_EPISODES[season]["dub"]

                row.append(
                    KeyboardButton(
                        f"مدبلج - الجزء {season} ({count} ح)"
                    )
                )

                if len(row) == 2:
                    keyboard.append(row)
                    row = []

        if row:
            keyboard.append(row)

        keyboard.append(
            [
                KeyboardButton("🔙 القائمة الرئيسية")
            ]
        )

        await message.reply_text(
            "📂 اختر الجزء المطلوب (المدبلج):",
            reply_markup=ReplyKeyboardMarkup(
                keyboard,
                resize_keyboard=True,
            ),
        )

        return

    # ========================================================
    # آخر حلقة شاهدتها
    # ========================================================

    if text == "📺 آخر حلقة شاهدتها":

        last_ep_info = user_last_watched.get(user_id)

        if not last_ep_info:

            await message.reply_text(
                "⚠️ **لم تقم بمشاهدة أي حلقة حتى الآن!**\n"
                "قم بتصفح الأقسام واختر حلقتك الأولى.",
                reply_markup=get_main_keyboard(),
                parse_mode="Markdown",
            )

            return

        season_num = last_ep_info["season"]
        ep_num = last_ep_info["ep"]
        media_type = last_ep_info["type"]

        type_name = (
            "مترجمة 🎬"
            if media_type == "sub"
            else "مدبلجة 🎙️"
        )

        await message.reply_text(
            f"📌 **آخر حلقة قمت بمشاهدتها:**\n"
            f"▫️ النسخة: {type_name}\n"
            f"▫️ الجزء: {season_num}\n"
            f"▫️ الحلقة: {ep_num}\n\n"
            "جاري إرسالها لك الآن...",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown",
        )

        msg_id = (
            EPISODES_MSG_IDS
            .get((season_num, media_type), {})
            .get(ep_num)
        )

        if not msg_id:
            await message.reply_text(
                "⚠️ عذراً، لم يتم العثور على ملف الحلقة."
            )
            return

        try:

            await context.bot.copy_message(
                chat_id=user_id,
                from_chat_id=CHANNEL_ID,
                message_id=msg_id,
            )

        except Exception:
            logger.exception("خطأ في إرسال آخر حلقة")

        return

    # ========================================================
    # القائمة الرئيسية
    # ========================================================

    if text == "🔙 القائمة الرئيسية":

        await message.reply_text(
            "🐺 **القائمة الرئيسية:**",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown",
        )

        return

    # ========================================================
    # اختيار الجزء
    # ========================================================

    if (
        text
        and "الجزء " in text
        and (
            "مترجم -" in text
            or "مدبلج -" in text
        )
    ):

        try:

            parts = text.split("-")

            media_prefix = parts[0].strip()
            season_part = parts[1].strip()

            season_num = int(
                season_part.split(" ")[1]
            )

            media_type = (
                "sub"
                if "مترجم" in media_prefix
                else "dub"
            )

            context.user_data["current_season"] = season_num
            context.user_data["media_type"] = media_type

            total_episodes = (
                SEASONS_EPISODES[season_num][media_type]
            )

            if total_episodes == 0:

                await message.reply_text(
                    "⚠️ هذا الجزء غير متوفر حالياً."
                )

                return

            keyboard = []
            row = []

            for ep in range(
                1,
                total_episodes + 1,
            ):

                row.append(
                    KeyboardButton(
                        f"حلقة {ep}"
                    )
                )

                if len(row) == 5:
                    keyboard.append(row)
                    row = []

            if row:
                keyboard.append(row)

            back_text = (
                "🎬 النسخة المترجمة"
                if media_type == "sub"
                else "🎙️ النسخة المدبلجة"
            )

            keyboard.append(
                [
                    KeyboardButton(back_text),
                    KeyboardButton("🔙 القائمة الرئيسية"),
                ]
            )

            await message.reply_text(
                f"🎬 اختر رقم الحلقة من الجزء {season_num}:",
                reply_markup=ReplyKeyboardMarkup(
                    keyboard,
                    resize_keyboard=True,
                ),
            )

        except Exception:
            logger.exception(
                "خطأ في تحليل اختيار الجزء"
            )

        return

    # ========================================================
    # اختيار الحلقة
    # ========================================================

    if text and text.startswith("حلقة "):

        try:

            ep_num = int(
                text.split(" ")[1]
            )

            season_num = context.user_data.get(
                "current_season",
                1,
            )

            media_type = context.user_data.get(
                "media_type",
                "sub",
            )

            total_episodes = (
                SEASONS_EPISODES
                .get(season_num, {})
                .get(media_type, 0)
            )

            if ep_num < 1 or ep_num > total_episodes:

                await message.reply_text(
                    "⚠️ رقم الحلقة غير صحيح."
                )

                return

            msg_id = (
                EPISODES_MSG_IDS
                .get((season_num, media_type), {})
                .get(ep_num)
            )

            if not msg_id:

                await message.reply_text(
                    f"⚠️ عذراً، حلقة الجزء "
                    f"{season_num} - الحلقة {ep_num} "
                    "لم يتم ربطها بعد."
                )

                return

            # إرسال الحلقة مباشرة من Telegram
            try:

                await context.bot.copy_message(
                    chat_id=user_id,
                    from_chat_id=CHANNEL_ID,
                    message_id=msg_id,
                )

            except Exception:

                logger.exception(
                    "فشل إرسال الحلقة"
                )

                await message.reply_text(
                    "⚠️ حدث خطأ أثناء إرسال الحلقة، حاول مرة أخرى."
                )

                return

            # تسجيل المشاهدة فقط بعد نجاح الإرسال
            user_last_watched[user_id] = {
                "season": season_num,
                "ep": ep_num,
                "type": media_type,
            }

            key = (
                season_num,
                media_type,
                ep_num,
            )

            episode_views[key] = (
                episode_views.get(key, 0) + 1
            )

            total_episode_views += 1

        except Exception:

            logger.exception(
                "خطأ في إرسال الحلقة"
            )

        return

    # ========================================================
    # أي شيء آخر = رسالة غير مسموحة
    # ========================================================

    await report_unauthorized_message(
        update,
        context,
    )

    try:
        await message.delete()
    except Exception:
        pass

    try:

        warning_msg = await context.bot.send_message(
            chat_id=user_id,
            text=(
                "⚠️ **عذراً، الكتابة النصية غير مسموحة هنا!**\n"
                "الرجاء استخدام الأزرار في الأسفل للتنقل."
            ),
            parse_mode="Markdown",
        )

        await asyncio.sleep(4)

        try:
            await warning_msg.delete()
        except Exception:
            pass

    except Exception:
        logger.exception("فشل إرسال رسالة التحذير")

# ============================================================
# أزرار الإدارة
# ============================================================

async def admin_callback(update, context):

    query = update.callback_query

    if not query:
        return

    authorized = await is_admin_in_channel(
        context,
        query.from_user.id,
    )

    if not authorized:

        await query.answer(
            "⛔ هذا الزر مخصص لمشرفي قناة الإدارة.",
            show_alert=True,
        )

        return

    await query.answer()

    data = query.data or ""

    try:

        action, user_id_text = data.split(
            ":",
            1,
        )

        target_user_id = int(
            user_id_text
        )

    except Exception:

        await query.answer(
            "⚠️ بيانات غير صحيحة.",
            show_alert=True,
        )

        return

    # ========================================================
    # حظر المستخدم
    # ========================================================

    if action == "BAN":

        banned_users.add(
            target_user_id
        )

        try:

            await context.bot.send_message(
                chat_id=target_user_id,
                text="🚫 تم حظرك من استخدام البوت.",
            )

        except Exception:
            pass

        try:

            await query.edit_message_reply_markup(
                reply_markup=None
            )

        except Exception:
            pass

        try:

            await context.bot.send_message(
                chat_id=ADMIN_CHANNEL_ID,
                text=(
                    "🚫 **تم حظر المستخدم**\n\n"
                    f"🆔 User ID: `{target_user_id}`\n"
                    f"👮 بواسطة المشرف: "
                    f"`{query.from_user.id}`\n"
                    f"🕐 الوقت: `{now_string()}`"
                ),
                parse_mode="Markdown",
            )

        except Exception:
            logger.exception("فشل تسجيل الحظر")

        return

    # ========================================================
    # إبقاء المستخدم
    # ========================================================

    if action == "KEEP":

        try:

            await query.edit_message_reply_markup(
                reply_markup=None
            )

        except Exception:
            pass

        try:

            await context.bot.send_message(
                chat_id=ADMIN_CHANNEL_ID,
                text=(
                    "✅ **تم الإبقاء على المستخدم**\n\n"
                    f"🆔 User ID: `{target_user_id}`\n"
                    f"👮 بواسطة المشرف: "
                    f"`{query.from_user.id}`\n"
                    f"🕐 الوقت: `{now_string()}`"
                ),
                parse_mode="Markdown",
            )

        except Exception:
            logger.exception(
                "فشل تسجيل عملية الإبقاء"
            )

# ============================================================
# فك الحظر
# ============================================================

async def unban_command(update, context):

    user = update.effective_user

    if not user:
        return

    authorized = await is_admin_in_channel(
        context,
        user.id,
    )

    if not authorized:

        await update.effective_message.reply_text(
            "⛔ هذا الأمر مخصص لمشرفي قناة الإدارة."
        )

        return

    if not context.args:

        await update.effective_message.reply_text(
            "الاستخدام:\n/unban USER_ID"
        )

        return

    try:

        target_user_id = int(
            context.args[0]
        )

    except ValueError:

        await update.effective_message.reply_text(
            "⚠️ User ID غير صحيح."
        )

        return

    banned_users.discard(
        target_user_id
    )

    await update.effective_message.reply_text(
        f"✅ تم فك حظر المستخدم:\n`{target_user_id}`",
        parse_mode="Markdown",
    )

    try:

        await context.bot.send_message(
            chat_id=ADMIN_CHANNEL_ID,
            text=(
                "✅ **تم فك حظر مستخدم**\n\n"
                f"🆔 User ID: `{target_user_id}`\n"
                f"👮 بواسطة المشرف: `{user.id}`\n"
                f"🕐 الوقت: `{now_string()}`"
            ),
            parse_mode="Markdown",
        )

    except Exception:
        logger.exception(
            "فشل تسجيل فك الحظر"
        )

# ============================================================
# الإحصائيات
# ============================================================

async def stats_command(update, context):

    user = update.effective_user

    if not user:
        return

    authorized = await is_admin_in_channel(
        context,
        user.id,
    )

    if not authorized:

        await update.effective_message.reply_text(
            "⛔ هذا الأمر مخصص لمشرفي قناة الإدارة."
        )

        return

    report = (
        "📊 **إحصائيات البوت الحالية**\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"👥 إجمالي المستخدمين: **{len(unique_users)}**\n"
        f"🆕 زيارات الفترة: **{len(daily_visits)}**\n"
        f"🟢 النشطون: **{len(daily_active_users)}**\n"
        f"📺 إجمالي مشاهدات الحلقات: **{total_episode_views}**\n"
        f"🔴 المحظورون: **{len(banned_users)}**\n"
        f"⚠️ الأخطاء: **{daily_errors_count}**\n"
        f"🕐 وقت التقرير: `{now_string()}`\n"
        "━━━━━━━━━━━━━━━━━━"
    )

    await update.effective_message.reply_text(
        report,
        parse_mode="Markdown",
    )

# ============================================================
# أكثر الحلقات مشاهدة
# ============================================================

async def most_watched_command(update, context):

    user = update.effective_user

    if not user:
        return

    authorized = await is_admin_in_channel(
        context,
        user.id,
    )

    if not authorized:

        await update.effective_message.reply_text(
            "⛔ هذا الأمر مخصص لمشرفي قناة الإدارة."
        )

        return

    if not episode_views:

        await update.effective_message.reply_text(
            "📊 لا توجد مشاهدات مسجلة بعد."
        )

        return

    sorted_items = sorted(
        episode_views.items(),
        key=lambda item: item[1],
        reverse=True,
    )[:10]

    lines = [
        "🔥 **أكثر 10 حلقات مشاهدة**\n"
    ]

    for index, (key, views) in enumerate(
        sorted_items,
        start=1,
    ):

        season, media_type, episode = key

        type_name = (
            "مترجم 🎬"
            if media_type == "sub"
            else "مدبلج 🎙️"
        )

        lines.append(
            f"{index}️⃣ الجزء {season} - "
            f"الحلقة {episode} - "
            f"{type_name} — **{views}** مشاهدة"
        )

    await update.effective_message.reply_text(
        "\n".join(lines),
        parse_mode="Markdown",
    )

# ============================================================
# التقرير الدوري
# ============================================================

async def daily_report_job(context):

    global daily_visits
    global daily_active_users
    global daily_errors_count

    report = (
        "📊 **التقرير الدوري للبوت**\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🕐 وقت التقرير: `{now_string()}`\n\n"
        f"🆕 المستخدمون الذين بدأوا خلال الفترة: "
        f"**{len(daily_visits)}**\n"
        f"🟢 المستخدمون النشطون: "
        f"**{len(daily_active_users)}**\n"
        f"👥 إجمالي المستخدمين أثناء التشغيل: "
        f"**{len(unique_users)}**\n"
        f"📺 إجمالي المشاهدات أثناء التشغيل: "
        f"**{total_episode_views}**\n"
        f"⚠️ الأخطاء: **{daily_errors_count}**\n"
        f"🔴 المحظورون أثناء التشغيل: "
        f"**{len(banned_users)}**\n\n"
        "🟢 **حالة البوت: يعمل**\n"
        "━━━━━━━━━━━━━━━━━━"
    )

    try:

        await context.bot.send_message(
            chat_id=ADMIN_CHANNEL_ID,
            text=report,
            parse_mode="Markdown",
        )

    except Exception:
        logger.exception(
            "فشل إرسال التقرير الدوري"
        )

    daily_visits.clear()
    daily_active_users.clear()
    daily_errors_count = 0

# ============================================================
# تسجيل الأخطاء
# ============================================================

async def error_handler(update, context):

    global daily_errors_count

    daily_errors_count += 1

    logger.error(
        "Exception while handling an update:",
        exc_info=context.error,
    )

    try:

        await context.bot.send_message(
            chat_id=ADMIN_CHANNEL_ID,
            text=(
                "⚠️ **خطأ في البوت**\n\n"
                f"🕐 الوقت: `{now_string()}`\n"
                "📛 الخطأ:\n"
                f"`{safe_text(str(context.error), 3000)}`"
            ),
            parse_mode="Markdown",
        )

    except Exception:
        logger.exception(
            "فشل إرسال الخطأ للإدارة"
        )

# ============================================================
# Web Server الخاص بـ Render
# ============================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        self.send_response(200)

        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8",
        )

        self.end_headers()

        self.wfile.write(
            b"Bot is running."
        )

    def log_message(self, format, *args):
        return

# ============================================================
# تشغيل Web Server
# ============================================================

def run_web_server():

    port = int(
        os.environ.get(
            "PORT",
            "10000",
        )
    )

    server = HTTPServer(
        ("0.0.0.0", port),
        HealthHandler,
    )

    logger.info(
        f"Health server running on port {port}"
    )

    server.serve_forever()

# ============================================================
# Main
# ============================================================

def main():

    # Render Health Server
    server_thread = threading.Thread(
        target=run_web_server,
        daemon=True,
    )

    server_thread.start()

    # Telegram Application
    application = (
        Application
        .builder()
        .token(TOKEN)
        .build()
    )

    # التقرير الدوري كل 24 ساعة
    if application.job_queue:

        application.job_queue.run_repeating(
            daily_report_job,
            interval=86400,
            first=60,
        )

    else:

        logger.warning(
            "JobQueue غير متوفر. "
            "ثبت python-telegram-bot[job-queue]"
        )

    # ========================================================
    # الأوامر
    # ========================================================

    application.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    application.add_handler(
        CommandHandler(
            "stats",
            stats_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "mostwatched",
            most_watched_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "unban",
            unban_command,
        )
    )

    # ========================================================
    # أزرار الإدارة
    # ========================================================

    application.add_handler(
        CallbackQueryHandler(
            admin_callback,
            pattern=r"^(BAN|KEEP):",
        )
    )

    # ========================================================
    # جميع رسائل المستخدمين
    # ========================================================

    application.add_handler(
        MessageHandler(
            filters.ALL & ~filters.COMMAND,
            handle_messages,
        )
    )

    # ========================================================
    # الأخطاء
    # ========================================================

    application.add_error_handler(
        error_handler
    )

    logger.info(
        "Starting Telegram bot..."
    )

    # تشغيل البوت
    application.run_polling(
        drop_pending_updates=True,
        stop_signals=None,
    )

# ============================================================
# التشغيل
# ============================================================

if __name__ == "__main__":
    main()
