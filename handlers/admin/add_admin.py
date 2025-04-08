import json
import os
import logging
import re
from telegram import Update, ChatMember
from telegram.ext import ContextTypes
from utils.users import get_user_id_by_username, register_user

ADMIN_DB = "database/admin_db.json"

logging.basicConfig(level=logging.INFO)

# Включить детальный лог этой команды — True / False
DEBUG_ADD_ADMIN = True


def debug_log(message):
    if DEBUG_ADD_ADMIN:
        logging.debug(message)


def load_admins():
    if not os.path.exists(ADMIN_DB):
        return {}
    with open(ADMIN_DB, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def save_admins(admins: dict):
    with open(ADMIN_DB, 'w', encoding='utf-8') as f:
        json.dump(admins, f, indent=2, ensure_ascii=False)


def has_admin_permission(user_id: str, chat_id: str, admins: dict) -> bool:
    user_id = str(user_id)
    chat_id = str(chat_id)
    if chat_id not in admins:
        return False
    group_admins = admins[chat_id].get("admins", {})
    user_data = group_admins.get(user_id)
    if user_data and user_data.get("level") == "Заместитель Главы":
        return True
    return False


async def add_admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    chat = update.effective_chat
    user = update.effective_user
    chat_id = str(chat.id)
    chat_title = chat.title or "Без названия"

    admins = load_admins()

    try:
        requester = await context.bot.get_chat_member(chat.id, user.id)
        if requester.status != ChatMember.OWNER and not has_admin_permission(user.id, chat_id, admins):
            await message.reply_text("У вас нет прав для выполнения этой команды.")
            return
    except Exception as e:
        logging.error(f"Ошибка get_chat_member (запросивший): {type(e).__name__} - {e}")
        await message.reply_text("Не удалось проверить ваши права.")
        return

    text = message.text.strip()
    parts = text.split(maxsplit=2)
    debug_log(f"Команда разбита на части: {parts}")

    if message.reply_to_message:
        if not message.reply_to_message.from_user:
            await message.reply_text("Не удалось определить пользователя в ответе.")
            return
        if len(parts) < 2:
            await message.reply_text("Укажите уровень доступа: 'Соруководитель' или 'Заместитель Главы'")
            return
        target_user = message.reply_to_message.from_user
        level_raw = parts[1].strip().casefold()
        debug_log(f"Получен level из ответа: {level_raw}")
        target_user_id = str(target_user.id)
        username = target_user.username
        if username:
            register_user(target_user)
    else:
        if len(parts) < 3:
            await message.reply_text("Формат: !add-admin @username|ID уровень_доступа")
            return

        target = parts[1]
        level_raw = parts[2].strip().casefold()
        debug_log(f"Получен level: {level_raw}")

        if target.startswith('@'):
            username = target[1:]
            uid = get_user_id_by_username(username)
            if not uid:
                await message.reply_text("Не удалось найти пользователя в базе.")
                return
            target_user_id = str(uid)
        elif target.isdigit():
            target_user_id = target
            username = None
        else:
            await message.reply_text("Укажите правильный @username или ID.")
            return

    match = re.search(r"(\d+)$", level_raw)
    if match:
        level_raw = match.group(1)
    debug_log(f"Обновлённый level_raw после поиска числа: {level_raw}")

    level_map = {
        "соруководитель": "Соруководитель",
        "заместитель главы": "Заместитель Главы",
        "1": "Заместитель Главы",
        "2": "Соруководитель"
    }
    debug_log(f"Проверка уровня: {level_raw} против {list(level_map.keys())}")
    if level_raw not in level_map:
        await message.reply_text(f"Недопустимый уровень. Используйте: {', '.join(set(level_map.values()))} \n(Если у вас Темы - попробуйте ввести команду в основном чате группы)")
        return

    level = level_map[level_raw]

    if not target_user_id:
        await message.reply_text("Не удалось определить ID пользователя.")
        return

    try:
        target_status = await context.bot.get_chat_member(chat.id, int(target_user_id))
        if target_status.status == ChatMember.OWNER:
            await message.reply_text("Нельзя назначить владельца группы администратором.")
            return
    except Exception as e:
        logging.error(f"Ошибка get_chat_member (цель): {type(e).__name__} - {e}")
        await message.reply_text("Не удалось получить статус пользователя.")
        return

    if chat_id not in admins:
        admins[chat_id] = {
            "group_title": chat_title,
            "admins": {}
        }

    already_admin = target_user_id in admins[chat_id]["admins"]

    admins[chat_id]["admins"][target_user_id] = {
        "username": username if username else None,
        "level": level
    }

    save_admins(admins)

    mention = f"@{username}" if username else f"<a href='tg://user?id={target_user_id}'>Пользователь</a>"
    msg = f"{mention} назначен администратором уровня: <b>{level}</b>"
    if already_admin:
        msg += " (обновлено)"
    await message.reply_text(msg, parse_mode="HTML")
