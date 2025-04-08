# Команда !clear-cmd <N>m — удаляет сообщения от бота и вызовы команд за последние N минут.
# Поддерживает русскую "м" и латинскую "m".
# Сохраняет кэш сообщений с автоочисткой каждые 48 часов.
# Учитывает уровни доверия, ограничения по времени и количеству сообщений.
# Переменная DEBUG_CLEAR_CMD управляет логированием (включить True/False).

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters
from datetime import datetime, timedelta, timezone
import re

# ✅ Включение/отключение отладочной информации
DEBUG_CLEAR_CMD = True

# 🔒 Доверенные пользователи — без ограничений
TRUSTED_IDS = [5403794760]

# 📌 Разрешённые роли (если понадобится роль-логика)
ALLOWED_ROLES = ["владелец", "заместитель", "соруководитель"]

# 🧠 Кэш сообщений: chat_id -> список словарей с инфой о сообщении
message_cache = {}

# 🕒 Последний вызов команды очистки: chat_id -> datetime
last_clear_call = {}

# 🧼 Отслеживаем последнее время очистки кэша
last_cache_reset = datetime.now(timezone.utc)


# === 🔁 Автоочистка кэша чата (раз в 48 часов)
def cleanup_cache(chat_id):
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=48)

    if chat_id in message_cache:
        message_cache[chat_id] = [m for m in message_cache[chat_id] if m["date"] > cutoff]

        if DEBUG_CLEAR_CMD:
            print(f"[КЭШ] Очистка сообщений в чате {chat_id}. Осталось: {len(message_cache[chat_id])}")


# === ⏳ Время до следующей очистки
def time_until_cache_reset():
    now = datetime.now(timezone.utc)
    next_reset = last_cache_reset + timedelta(hours=48)
    remaining = next_reset - now
    total_hours = remaining.days * 24 + remaining.seconds // 3600
    minutes = (remaining.seconds % 3600) // 60
    return f"{total_hours}ч {minutes}м"


# === 🧼 Хэндлер команды очистки
async def clear_cmd_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    user_text = update.message.text
    now = datetime.now(timezone.utc)

    # ✅ Аргумент: извлекаем число и суффикс "m" или "м"
    match = re.search(r"!clear-cmd\s+(\d+)\s*[мm]", user_text, re.IGNORECASE)
    if not match:
        time_msg = time_until_cache_reset()
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ Использование: !clear-cmd <минуты>m\nПример: !clear-cmd 60m\n\n"
                 f"🧼 Кэш сообщений очищается каждые 48 часов.\n⏳ До следующей очистки: {time_msg}"
        )
        return

    minutes = int(match.group(1))

    # ⏱ Ограничение по времени (если не доверенный)
    if user_id not in TRUSTED_IDS:
        last_call = last_clear_call.get(chat_id)
        if last_call and now - last_call < timedelta(hours=1):
            await context.bot.send_message(chat_id=chat_id, text="⏱ Вы можете использовать эту команду раз в час.")
            return

    # 🧹 Очистка кэша перед фильтрацией
    cleanup_cache(chat_id)

    # 📦 Фильтрация сообщений из кэша
    deleted_count = 0
    cutoff_time = now - timedelta(minutes=minutes)

    if chat_id in message_cache:
        messages_to_delete = [
            msg for msg in message_cache[chat_id]
            if msg["date"] > cutoff_time and (
                msg["user_id"] == context.bot.id or (msg["text"] and msg["text"].startswith("!"))
            )
        ]

        if user_id not in TRUSTED_IDS:
            messages_to_delete = messages_to_delete[-100:]

        for msg in messages_to_delete:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=msg["message_id"])
                deleted_count += 1
                if DEBUG_CLEAR_CMD:
                    print(f"[УДАЛЕНО] {msg['message_id']}: {msg['text'][:30]}")
            except Exception as e:
                if DEBUG_CLEAR_CMD:
                    print(f"[ОШИБКА] Не удалось удалить {msg['message_id']}: {e}")
                continue

    last_clear_call[chat_id] = now

    await context.bot.send_message(chat_id=chat_id, text=f"✅ Удалено сообщений: {deleted_count}")


# === 💾 Кэширование всех сообщений
async def cache_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        msg = update.effective_message
        if not msg:
            return

        chat_id = msg.chat_id
        if chat_id not in message_cache:
            message_cache[chat_id] = []

        message_cache[chat_id].append({
            "message_id": msg.message_id,
            "user_id": msg.from_user.id if msg.from_user else None,
            "is_bot": msg.from_user.is_bot if msg.from_user else False,
            "text": msg.text or "",
            "date": msg.date
        })

        if len(message_cache[chat_id]) > 1000:
            message_cache[chat_id] = message_cache[chat_id][-1000:]

        if DEBUG_CLEAR_CMD:
            print(f"[КЭШ] + {msg.message_id} ({'BOT' if msg.from_user and msg.from_user.is_bot else 'USER'}) — {msg.text or ''}")

    except Exception as e:
        if DEBUG_CLEAR_CMD:
            print(f"[ОШИБКА КЭША] {e}")


# === 🔗 Подключение хэндлеров
clear_cmd_handler_obj = MessageHandler(filters.Regex(r"^!clear-cmd"), clear_cmd_handler)
cache_handler_obj = MessageHandler(filters.ALL, cache_message)
