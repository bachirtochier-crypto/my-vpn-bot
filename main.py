import os
import sqlite3
import threading
import time
from flask import Flask
import telebot

# 🔑 ТОКЕН ВАШЕГО VPN-БОТА
TOKEN = "7508869772:AAHJsTZHGBmGt1yypiuerXBM1Z3rorNXGsQ"
bot = telebot.TeleBot(TOKEN)

# НАСТРОЙКА БАЗЫ ДАННЫХ
def init_db():
    conn = sqlite3.connect("vpn_database.db")
    cursor = conn.cursor()
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        balance_days INTEGER DEFAULT 0,
        vpn_key TEXT DEFAULT NULL
    )"""
    )
    conn.commit()
    conn.close()


init_db()


# МЕНЮ КНОПОК (REPLY)
def main_menu():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("✨ Начать тест (1 день бесплатно)", "💳 Купить подписку")
    markup.row("📅 Мой профиль", "❓ Инструкция")
    return markup


# КОМАНДА /START
@bot.message_handler(commands=["start"])
def start_message(message):
    user_id = message.from_user.id
    username = message.from_user.username or "Пользователь"

    conn = sqlite3.connect("vpn_database.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
        (user_id, username),
    )
    conn.commit()
    conn.close()

    text = (
        "✨ Добро пожаловать в наш официальный VPN-сервис!\n\n"
        "Мы создали быстрый и надежный VPN, который работает повсюду в России на максимальной скорости и без сбоев 🌐\n\n"
        "🎁 Вам доступен 1 ДЕНЬ БЕСПЛАТНОГО ТЕСТА, чтобы вы могли лично убедиться в качестве!\n\n"
        "👇 Используйте меню кнопок ниже для управления подпиской:"
    )
    bot.send_message(message.chat.id, text, reply_markup=main_menu())


# ОБРАБОТКА ТЕКСТОВЫХ КНОПОК МЕНЮ
@bot.message_handler(content_types=["text"])
def handle_text_buttons(message):
    user_id = message.from_user.id

    if message.text == "✨ Начать тест (1 день бесплатно)":
        conn = sqlite3.connect("vpn_database.db")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT balance_days, vpn_key FROM users WHERE user_id = ?",
            (user_id,),
        )
        user = cursor.fetchone()

        if user and user[0] > 0:
            bot.send_message(
                message.chat.id, "❌ Вы уже активировали тестовый период!"
            )
        else:
            # Симулируем выдачу тестового дня
            test_key = "vless://test-key-generated-by-bot-for-rashido-vpn"
            cursor.execute(
                "UPDATE users SET balance_days = 1, vpn_key = ? WHERE user_id = ?",
                (test_key, user_id),
            )
            conn.commit()
            bot.send_message(
                message.chat.id,
                "🎁 Вам успешно начислен 1 день тестового VPN!\n\nВаш ключ доступа отправлен в профиль. Нажмите кнопку «📅 Мой профиль», чтобы забрать его.",
            )
        conn.close()

    elif message.text == "📅 Мой профиль":
        conn = sqlite3.connect("vpn_database.db")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT balance_days, vpn_key FROM users WHERE user_id = ?",
            (user_id,),
        )
        user = cursor.fetchone()
        conn.close()

        days = user[0] if user else 0
        key = (
            user[1]
            if user and user[1]
            else "Ключ отсутствует. Купите подписку или активируйте тест."
        )

        profile_text = (
            f"👤 *Ваш профиль:*\n\n"
            f"📅 Доступно дней подписки: *{days}*\n\n"
            f"🔑 *Ваш VPN-ключ:* \n`{key}`\n\n"
            f"_(Нажмите на текст ключа, чтобы скопировать его)_"
        )
        bot.send_message(message.chat.id, profile_text, parse_mode="Markdown")

    elif message.text == "❓ Инструкция":
        instruction = (
            "❓ *Как подключиться к VPN?*\n\n"
            "1. Скопируйте ваш персональный ключ из раздела «📅 Мой профиль».\n"
            "2. Скачайте приложение *v2rayNG* (для Android) или *v2Box* (для iPhone).\n"
            "3. Импортируйте скопированный ключ в приложение через значок плюса (+).\n"
            "4. Нажмите кнопку подключения!"
        )
        bot.send_message(message.chat.id, instruction, parse_mode="Markdown")

    elif message.text == "💳 Купить подписку":
        text = (
            "📥 *Выберите период подписки:*\n"
            "Чем больше срок — тем дешевле выходит месяц!\n\n"
            "_(Внимание! Бот запущен в демо-режиме, оплата симулируется бесплатно)_"
        )
        markup = telebot.types.InlineKeyboardMarkup()
        markup.row(
            telebot.types.InlineKeyboardButton(
                text="📅 1 месяц — 250 руб", callback_data="buy_30"
            )
        )
        markup.row(
            telebot.types.InlineKeyboardButton(
                text="📅 3 месяца — 650 руб (Скидка!)", callback_data="buy_90"
            )
        )
        markup.row(
            telebot.types.InlineKeyboardButton(
                text="🚀 6 месяцев — 1200 руб (Выгодно)", callback_data="buy_180"
            )
        )
        markup.row(
            telebot.types.InlineKeyboardButton(
                text="💎 1 год — 2100 руб (Макс. скидка)", callback_data="buy_365"
            )
        )
        bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="Markdown")


# ОБРАБОТКА ДЕМО-ОПЛАТЫ ИЗ ТАРИФНОЙ СЕТКИ
@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def process_demo_payment(call):
    days_to_add = int(call.data.split("_")[1])
    user_id = call.from_user.id

    conn = sqlite3.connect("vpn_database.db")
    cursor = conn.cursor()

    # Добавляем дни подписки к текущему балансу
    cursor.execute(
        "SELECT balance_days FROM users WHERE user_id = ?", (user_id,)
    )
    current_days = cursor.fetchone()[0] or 0
    new_days = current_days + days_to_add

    # Генерируем постоянный демо-ключ
    premium_key = f"vless://premium-key-for-user-{user_id}-activated"

    cursor.execute(
        "UPDATE users SET balance_days = ?, vpn_key = ? WHERE user_id = ?",
        (new_days, premium_key, user_id),
    )
    conn.commit()
    conn.close()

    success_text = (
        "✅ *Оплата прошла успешно!*\n\n"
        "Ваш платёж успешно получен. Подписка на VPN активирована/продлена 🚀\n\n"
        "🌐 Ваш ключ обновлен. Можете продолжать пользоваться быстрым и безопасным интернетом!"
    )
    bot.send_message(call.message.chat.id, success_text, parse_mode="Markdown")
    bot.answer_callback_query(call.id)


# ФЛАСК-СЕРВЕР ДЛЯ ВЕБ-ИНТЕРФЕЙСА RENDER
if __name__ == "__main__":
    app = Flask(__name__)

    @app.route("/")
    def home():
        return "VPN Bot is active and running!"

    app_port = int(os.environ.get("PORT", 5000))
    threading.Thread(target=bot.infinity_polling, daemon=True).start()
    app.run(host="0.0.0.0", port=app_port)