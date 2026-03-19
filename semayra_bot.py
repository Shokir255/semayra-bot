#!/usr/bin/env python3
import os
import sqlite3
import logging
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo
from calendar import monthrange

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

TZ = ZoneInfo("Asia/Tashkent")
DEFAULT_TIME = time(8, 0)
DB_PATH = "semayra_bot.db"

BTN_RU = "🇷🇺 Русский"
BTN_UZ = "🇺🇿 O'zbek"
BTN_PLAN = "📅 План инъекций"
BTN_HOW = "💉 Как применять"
BTN_ABOUT = "ℹ️ О препарате"
BTN_SAFE = "⚠️ Безопасность"
BTN_AE = "🤢 Побочные эффекты"
BTN_FAQ = "❓ FAQ"
BTN_CONTACT = "☎️ Контакты"
BTN_SET_PLAN = "🗓 Установить план"
BTN_SHOW_PLAN = "📌 Мой график"
BTN_DONE = "✅ Сделал инъекцию"
BTN_BACK = "⬅️ Назад"

TEXTS = {
    "ru": {
        "welcome": "Здравствуйте! Я бот SEMAYRA.\nВыберите язык:",
        "privacy": "🔒 Мы не запрашиваем ФИО/паспорт/адрес.\nДля напоминаний храним только chat_id и дату.",
        "menu": "Выберите раздел:",
        "plan_menu": "📅 План инъекций:",
        "pick_date": "Выберите дату первой инъекции (время 08:00):",
        "plan_set": "✅ План установлен.\nСледующая инъекция: {dt}",
        "how": "💉 КАК ПРИМЕНЯТЬ\n\n• Делайте инъекцию 1 раз в неделю в один и тот же день.\n• Вводится подкожно (живот/бедро/плечо).\n• Меняйте место укола.\n\n⚠️ Точную дозу и схему определяет врач.",
        "safe": "⚠️ БЕЗОПАСНОСТЬ\n\n• При сильной тошноте/рвоте/болях в животе — обратитесь к врачу.\n• Сообщите врачу о всех лекарствах.\n• Беременность/ГВ — только по назначению врача.\n\nℹ️ Это информационный бот, не заменяет консультацию.",
        "ae": "🤢 ПОБОЧНЫЕ ЭФФЕКТЫ\n\nЧастые:\n• тошнота, изжога\n• снижение аппетита\n• диарея/запор\n• головная боль\n\nРедко/опасно:\n• сильные боли в животе\n• признаки обезвоживания\n\nПри тревожных симптомах — врач.",
        "about": "ℹ️ О ПРЕПАРАТЕ\n\nSEMAYRA (семаглутид) — препарат для контроля веса/гликемии.\n⚠️ Применение — по назначению врача.",
        "faq": "❓ FAQ\n\n• Когда эффект? Обычно 4–8 недель.\n• Пропустил дозу? Если прошло <5 дней — сделайте как можно скорее, иначе пропустите и вернитесь к графику.\n• Нужна диета? Да, желательно.\n\nНапоминания: 📅 План инъекций → 🗓 Установить план",
        "contact": "☎️ КОНТАКТЫ\n\nSORRENTO MARKETING\n📍 Узбекистан, Ташкент, ул. Амира Темура, 51А\n🌐 sorrento.marketing\n📧 office@sorrento.marketing\n📞 +998 71 230 95 86 — офис\n📞 +998 71 230 95 87 — фармаконадзор\n\n💬 Telegram: @Sorrentomarketing_bot\n📸 Instagram: @sorrentomarketing\n\n⚕️ При вопросах по здоровью — только врач.",
        "no_plan": "У вас ещё не установлен план. Нажмите 🗓 Установить план.",
        "my_plan": "📌 Следующая инъекция: {dt}",
        "done": "✅ Отметил(а). Следующая инъекция: {dt}",
    },
    "uz": {
        "welcome": "Assalomu alaykum! Men SEMAYRA botiman.\nTilni tanlang:",
        "privacy": "🔒 Bot FIO/pasport so'ramaydi.\nFaqat chat_id va sana saqlanadi.",
        "menu": "Bo'limni tanlang:",
        "plan_menu": "📅 Inʼeksiya rejasi:",
        "pick_date": "Birinchi inʼeksiya sanasini tanlang (vaqt 08:00):",
        "plan_set": "✅ Reja o'rnatildi.\nKeyingi inʼeksiya: {dt}",
        "how": "💉 QANDAY QO'LLASH\n\n• Haftasiga 1 marta, bir xil kunda.\n• Teri ostiga (qorin/son/yelka).\n• Inʼeksiya joyini almashtiring.\n\n⚠️ Doza va sxema — shifokor belgilaydi.",
        "safe": "⚠️ XAVFSIZLIK\n\n• Kuchli ko'ngil aynishi/qusish/qorin og'rig'i bo'lsa — shifokorga murojaat qiling.\n• Boshqa dori vositalari haqida shifokorga ayting.\n\nℹ️ Bot maslahat o'rnini bosa olmaydi.",
        "ae": "🤢 NOJO'YA TA'SIRLAR\n\nKo'p uchraydi:\n• ko'ngil aynishi\n• ishtaha pasayishi\n• ich ketishi/qabziyat\n• bosh og'rig'i\n\nXavfli belgilar bo'lsa — shifokor.",
        "about": "ℹ️ PREPARAT HAQIDA\n\nSEMAYRA (semaglutid) — vazn nazorati va diabet uchun.\n⚠️ Shifokor maslahati shart.",
        "faq": "❓ SAVOLLAR\n\n❔ Natijalar qachon?\n✅ 4–8 haftadan keyin\n\n❔ Dozani o'tkazib yubordim?\n✅ 5 kundan kam — tezroq\n\n❔ Parhezmi?\n✅ Ha, kerak\n\nEslatma: 📅 План инъекций → 🗓 Установить план",
        "contact": "☎️ ALOQA\n\nSORRENTO MARKETING\n📍 O'zbekiston, Toshkent, Amir Temur ko'chasi, 51A\n🌐 sorrento.marketing\n📧 office@sorrento.marketing\n📞 +998 71 230 95 86 — ofis\n📞 +998 71 230 95 87 — farmakonazorat\n\n💬 Telegram: @Sorrentomarketing_bot\n📸 Instagram: @sorrentomarketing\n\n⚕️ Shifokoringizga murojaat qiling!",
        "no_plan": "Sizda reja yo'q. 🗓 Uстановить план tugmasini bosing.",
        "my_plan": "📌 Keyingi inʼeksiya: {dt}",
        "done": "✅ Belgilandi. Keyingi inʼeksiya: {dt}",
    },
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger("semayra")


def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY,
            lang TEXT DEFAULT 'ru',
            next_injection TEXT
        )
        """
    )
    conn.commit()
    return conn


def get_user(conn, chat_id: int):
    row = conn.execute(
        "SELECT lang, next_injection FROM users WHERE chat_id=?",
        (chat_id,),
    ).fetchone()
    if row:
        return {"lang": row[0] or "ru", "next_injection": row[1]}
    return {"lang": "ru", "next_injection": None}


def ensure_user(conn, chat_id: int):
    conn.execute("INSERT OR IGNORE INTO users(chat_id) VALUES (?)", (chat_id,))
    conn.commit()


def set_lang(conn, chat_id: int, lang: str):
    ensure_user(conn, chat_id)
    conn.execute("UPDATE users SET lang=? WHERE chat_id=?", (lang, chat_id))
    conn.commit()


def set_injection(conn, chat_id: int, dt: datetime):
    ensure_user(conn, chat_id)
    conn.execute("UPDATE users SET next_injection=? WHERE chat_id=?", (dt.isoformat(), chat_id))
    conn.commit()


def kb_lang():
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton(BTN_RU, callback_data="lang|ru"),
            InlineKeyboardButton(BTN_UZ, callback_data="lang|uz"),
        ]]
    )


def kb_main():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(BTN_PLAN)],
            [KeyboardButton(BTN_HOW), KeyboardButton(BTN_ABOUT)],
            [KeyboardButton(BTN_SAFE), KeyboardButton(BTN_AE)],
            [KeyboardButton(BTN_FAQ), KeyboardButton(BTN_CONTACT)],
        ],
        resize_keyboard=True,
    )


def kb_plan():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(BTN_SET_PLAN), KeyboardButton(BTN_SHOW_PLAN)],
            [KeyboardButton(BTN_DONE)],
            [KeyboardButton(BTN_BACK)],
        ],
        resize_keyboard=True,
    )


def build_calendar(year: int, month: int):
    title = f"{month:02d}.{year}"
    kb = [[InlineKeyboardButton(f"📅 {title}", callback_data="noop")]]

    first_wd, days = monthrange(year, month)
    row = []
    for _ in range(first_wd):
        row.append(InlineKeyboardButton(" ", callback_data="noop"))

    for d in range(1, days + 1):
        row.append(InlineKeyboardButton(str(d), callback_data=f"day|{year}|{month}|{d}"))
        if len(row) == 7:
            kb.append(row)
            row = []

    if row:
        while len(row) < 7:
            row.append(InlineKeyboardButton(" ", callback_data="noop"))
        kb.append(row)

    prev = (datetime(year, month, 15) - timedelta(days=31)).replace(day=1)
    nxt = (datetime(year, month, 15) + timedelta(days=31)).replace(day=1)
    kb.append(
        [
            InlineKeyboardButton("◀️", callback_data=f"cal|{prev.year}|{prev.month}"),
            InlineKeyboardButton("▶️", callback_data=f"cal|{nxt.year}|{nxt.month}"),
        ]
    )
    return InlineKeyboardMarkup(kb)


def parse_next_injection(s: str | None):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(TEXTS["ru"]["welcome"], reply_markup=kb_lang())


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    conn = context.application.bot_data["db"]
    chat_id = update.effective_chat.id

    user = get_user(conn, chat_id)
    lang = user["lang"]
    data = q.data or ""

    if data == "noop":
        return

    if data.startswith("lang|"):
        lang = data.split("|", 1)[1]
        set_lang(conn, chat_id, lang)
        await q.message.reply_text(TEXTS[lang]["privacy"])
        await q.message.reply_text(TEXTS[lang]["menu"], reply_markup=kb_main())
        return

    if data.startswith("cal|"):
        _, y, m = data.split("|")
        await q.edit_message_reply_markup(reply_markup=build_calendar(int(y), int(m)))
        return

    if data.startswith("day|"):
        _, y, m, d = data.split("|")
        dt = datetime(int(y), int(m), int(d), DEFAULT_TIME.hour, DEFAULT_TIME.minute, tzinfo=TZ)
        set_injection(conn, chat_id, dt)
        await q.message.reply_text(
            TEXTS[lang]["plan_set"].format(dt=dt.strftime("%d.%m.%Y %H:%M")),
            reply_markup=kb_plan(),
        )
        return


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = context.application.bot_data["db"]
    chat_id = update.effective_chat.id
    ensure_user(conn, chat_id)

    user = get_user(conn, chat_id)
    lang = user["lang"]
    text = (update.message.text or "").strip()

    next_dt = parse_next_injection(user["next_injection"])

    if text == BTN_PLAN:
        await update.message.reply_text(TEXTS[lang]["plan_menu"], reply_markup=kb_plan())
    elif text == BTN_SET_PLAN:
        now = datetime.now(TZ)
        await update.message.reply_text(TEXTS[lang]["pick_date"], reply_markup=build_calendar(now.year, now.month))
    elif text == BTN_SHOW_PLAN:
        if not next_dt:
            await update.message.reply_text(TEXTS[lang]["no_plan"], reply_markup=kb_plan())
        else:
            await update.message.reply_text(TEXTS[lang]["my_plan"].format(dt=next_dt.strftime("%d.%m.%Y %H:%M")), reply_markup=kb_plan())
    elif text == BTN_DONE:
        if not next_dt:
            await update.message.reply_text(TEXTS[lang]["no_plan"], reply_markup=kb_plan())
        else:
            new_dt = next_dt + timedelta(days=7)
            set_injection(conn, chat_id, new_dt)
            await update.message.reply_text(TEXTS[lang]["done"].format(dt=new_dt.strftime("%d.%m.%Y %H:%M")), reply_markup=kb_plan())
    elif text == BTN_BACK:
        await update.message.reply_text(TEXTS[lang]["menu"], reply_markup=kb_main())
    elif text == BTN_HOW:
        await update.message.reply_text(TEXTS[lang]["how"])
    elif text == BTN_ABOUT:
        await update.message.reply_text(TEXTS[lang]["about"])
    elif text == BTN_SAFE:
        await update.message.reply_text(TEXTS[lang]["safe"])
    elif text == BTN_AE:
        await update.message.reply_text(TEXTS[lang]["ae"])
    elif text == BTN_FAQ:
        await update.message.reply_text(TEXTS[lang]["faq"])
    elif text == BTN_CONTACT:
        await update.message.reply_text(TEXTS[lang]["contact"])


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN не найден в переменных окружения")

    app = ApplicationBuilder().token(token.strip()).build()
    app.bot_data["db"] = init_db()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    log.info("✅ Бот SEMAYRA запущен")
    app.run_polling(close_loop=False)


if __name__ == "__main__":
    main()
