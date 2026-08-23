import os
import telebot
from telebot import types

# Токен бота (можно задать через переменную окружения BOT_TOKEN).
TOKEN = os.environ.get("BOT_TOKEN")

# --- Прокси (опционально) ---
# Локально бот ходит в Telegram через SOCKS5-прокси приложения Happ
# (порт 10808, Settings → Advanced → "Allow LAN Connections").
# На Render (и любом другом зарубежном сервере) прокси не нужен —
# там переменная BOT_PROXY не задана, и这几 строки просто пропускаются.
from telebot import apihelper

PROXY_URL = os.environ.get("BOT_PROXY")
if PROXY_URL:
    apihelper.proxy = {"https": PROXY_URL}

bot = telebot.TeleBot(TOKEN)

# Справочники меню (потом легко поправить цены/названия здесь)
MEAT_LABELS = {"pork": "со свининой 🐖", "chicken": "с курицей 🍗"}
SIZES = {
    "small": ("Маленькая", "250 ₽"),
    "big": ("Большая", "350 ₽"),
}


# --- Клавиатуры меню ---

def meat_keyboard():
    """Клавиатура выбора начинки."""
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton("🐖 Со свининой", callback_data="meat|pork"),
        types.InlineKeyboardButton("🍗 С курицей", callback_data="meat|chicken"),
    )
    return kb


def size_keyboard(meat):
    """Клавиатура выбора размера (несёт в себе выбранную начинку)."""
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton(f"Маленькая · {SIZES['small'][1]}", callback_data=f"size|{meat}|small"),
        types.InlineKeyboardButton(f"Большая · {SIZES['big'][1]}", callback_data=f"size|{meat}|big"),
    )
    kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="back"))
    return kb


def new_order_keyboard():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔄 Новый заказ", callback_data="restart"))
    return kb


# --- Обработчики ---

@bot.message_handler(commands=["start", "menu"])
def show_menu(message):
    bot.send_message(
        message.chat.id,
        "Добро пожаловать! 🔥\n\nКакую шаурму вам приготовить?",
        reply_markup=meat_keyboard(),
    )


@bot.message_handler(func=lambda m: True)
def fallback(message):
    """Любой другой текст — показываем меню."""
    bot.send_message(message.chat.id, "Выберите шаурму из меню 👇", reply_markup=meat_keyboard())


@bot.callback_query_handler(func=lambda c: c.data in ("restart", "back"))
def restart_or_back(c):
    bot.edit_message_text(
        "Какую шаурму вам приготовить?" if c.data == "restart" else "Хорошо, выберите начинку:",
        chat_id=c.message.chat.id,
        message_id=c.message.message_id,
        reply_markup=meat_keyboard(),
    )
    bot.answer_callback_query(c.id)


@bot.callback_query_handler(func=lambda c: c.data.startswith("meat|"))
def choose_meat(c):
    meat = c.data.split("|")[1]
    bot.edit_message_text(
        f"Отлично — шаурма *{MEAT_LABELS[meat]}*. Какой размер?",
        chat_id=c.message.chat.id,
        message_id=c.message.message_id,
        reply_markup=size_keyboard(meat),
        parse_mode="Markdown",
    )
    bot.answer_callback_query(c.id)


@bot.callback_query_handler(func=lambda c: c.data.startswith("size|"))
def choose_size(c):
    _, meat, size = c.data.split("|")
    size_name, price = SIZES[size]
    bot.edit_message_text(
        "✅ *Заказ принят!*\n\n"
        f"Шаурма {MEAT_LABELS[meat]}\n"
        f"Размер: {size_name}\n"
        f"К оплате: *{price}*\n\n"
        "Спасибо! Мы скоро свяжемся для подтверждения 📞",
        chat_id=c.message.chat.id,
        message_id=c.message.message_id,
        reply_markup=new_order_keyboard(),
        parse_mode="Markdown",
    )
    bot.answer_callback_query(c.id)


if __name__ == "__main__":
    # --- Keep-alive веб-сервер для Render ---
    # Render требует, чтобы сервис слушал HTTP-порт, иначе считает его упавшим.
    # Этот сервер ничего не делает, кроме ответа "OK" — и не даёт бесплатному
    # тарифу усыпить бота (плюс его пингует UptimeRobot).
    # Если flask не установлен (например, запускаем локально) — просто пропускаем.
    try:
        import threading
        from flask import Flask

        web = Flask(__name__)

        @web.route("/")
        def health():
            return "Bot is running ✅"

        threading.Thread(
            target=lambda: web.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)), use_reloader=False),
            daemon=True,
        ).start()
    except ImportError:
        print("flask не установлен — keep-alive сервер пропущен (это нормально для локального запуска).")

    print("Бот запущен. Нажми Ctrl+C, чтобы остановить.")
    bot.infinity_polling()
