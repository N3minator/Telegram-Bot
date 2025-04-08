import os
import sys
import time
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters
from datetime import datetime

# 🔐 ID пользователей, которым разрешён перезапуск
TRUSTED_IDS = [5403794760]

# 🔁 Хранилище инфы о перезапуске
restart_info = {
    "initiator_id": None,
    "initiator_name": None,
    "start_time": None,
    "chat_id": None,
    "message_id": None
}


# 🔄 Команда !restart
async def restart_bot_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in TRUSTED_IDS:
        await update.message.reply_text("❌ У вас нет прав для перезапуска бота.")
        return

    # Сохраняем данные перед перезапуском
    restart_info["initiator_id"] = user_id
    restart_info["initiator_name"] = update.effective_user.full_name
    restart_info["start_time"] = time.time()
    restart_info["chat_id"] = update.effective_chat.id
    restart_info["message_id"] = update.message.message_id

    await update.message.reply_text("🔁 Перезапускаю бота...")

    # Корректно закрываем соединение
    await context.bot.close()

    # Перезапускаем процесс Python
    os.execl(sys.executable, sys.executable, *sys.argv)


# ✅ Обработчик при старте — уведомление об успешном рестарте
async def on_bot_start(app):
    if restart_info["start_time"]:
        now = time.time()
        duration = round(now - restart_info["start_time"], 2)

        chat_id = restart_info["chat_id"]
        name = restart_info["initiator_name"]
        uid = restart_info["initiator_id"]

        text = (
            f"✅ Бот успешно перезапущен!\n\n"
            f"👤 Инициатор: <b>{name}</b> (<code>{uid}</code>)\n"
            f"🕒 Время запуска: <b>{datetime.now().strftime('%d.%m.%Y %H:%M:%S')}</b>\n"
            f"⚡️ Время перезапуска: <b>{duration} сек.</b>"
        )

        try:
            await app.bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
        except Exception as e:
            print("[❗ Ошибка при отправке сообщения о рестарте]:", e)

        # Очищаем инфу после отправки
        restart_info["start_time"] = None


# 🎯 Telegram-хэндлер
restart_handler = MessageHandler(filters.TEXT & filters.Regex(r"^!restart$"), restart_bot_handler)
