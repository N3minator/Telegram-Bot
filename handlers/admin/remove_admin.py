import json
import os
from telegram import Update, ChatMember
from telegram.ext import ContextTypes
from utils.users import get_user_id_by_username

ADMIN_DB = "database/admin_db.json"


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
    if chat_id not in admins:
        return False
    group_admins = admins[chat_id].get("admins", {})
    user_data = group_admins.get(str(user_id))
    if user_data and user_data.get("level") == "Заместитель Главы":
        return True
    return False


async def remove_admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    chat = update.effective_chat
    user = update.effective_user
    chat_id = str(chat.id)

    admins = load_admins()  # ✅ Загрузка базы ДО проверки прав

    try:
        requester = await context.bot.get_chat_member(chat.id, user.id)
        if requester.status != ChatMember.OWNER and not has_admin_permission(str(user.id), chat_id, admins):
            await message.reply_text("У вас нет прав для выполнения этой команды.")
            return
    except Exception:
        await message.reply_text("Ошибка проверки прав.")
        return

    if chat_id not in admins or not admins[chat_id]["admins"]:
        await message.reply_text("В этой группе нет администраторов для удаления.")
        return

    target_user_id = None
    target_username = None

    text = message.text.strip()
    parts = text.split(maxsplit=1)

    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
        target_user_id = str(target_user.id)
        target_username = target_user.username or None
    elif len(parts) == 2:
        identifier = parts[1].strip()
        if identifier.startswith("@"):
            username = identifier[1:]
            uid = get_user_id_by_username(username)
            if not uid:
                await message.reply_text("Пользователь не найден в базе.")
                return
            target_user_id = str(uid)
            target_username = username
        elif identifier.isdigit():
            target_user_id = str(identifier)
        else:
            await message.reply_text("Неверный формат. Укажите @username, ID или используйте ответ на сообщение.")
            return
    else:
        await message.reply_text("Укажите пользователя для удаления: через ответ, ID или @.")
        return

    if target_user_id not in admins[chat_id]["admins"]:
        await message.reply_text("Этот пользователь не является администратором.")
        return

    removed_admin = admins[chat_id]["admins"].pop(target_user_id)
    save_admins(admins)

    mention = (
        f"@{target_username}" if target_username else f"<a href='tg://user?id={target_user_id}'>Пользователь</a>"
    )
    await message.reply_text(
        f"{mention} был удалён из администраторов уровня: <b>{removed_admin.get('level', 'Неизвестно')}</b>",
        parse_mode="HTML"
    )