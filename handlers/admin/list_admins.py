import json
import os
from telegram import Update
from telegram.ext import ContextTypes

ADMIN_DB = "database/admin_db.json"


def load_admins():
    if not os.path.exists(ADMIN_DB):
        return {}
    with open(ADMIN_DB, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


async def list_admins_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    chat_id = str(update.effective_chat.id)
    admins = load_admins()

    if chat_id not in admins or not admins[chat_id]["admins"]:
        await message.reply_text("В этой группе пока нет назначенных администраторов.")
        return

    group_admins = admins[chat_id]["admins"]
    title = admins[chat_id].get("group_title", "Без названия")

    # Сортируем по категориям
    categories = {
        "Соруководитель": [],
        "Заместитель Главы": []
    }

    for user_id, info in group_admins.items():
        level = info.get("level", "Другое")
        username = info.get("username")

        mention = f"@{username}" if username else f"<a href='tg://user?id={user_id}'>Пользователь</a>"
        if level in categories:
            categories[level].append(mention)
        else:
            # На случай если появятся новые уровни в будущем
            if level not in categories:
                categories[level] = []
            categories[level].append(mention)

    result = f"<b>Администраторы группы:</b> {title}\n\n"

    # Упорядоченный вывод
    order = [
        ("Заместитель Главы", "⭐⭐️ Заместители Главы"),
        ("Соруководитель", "⭐️ Соруководители")
    ]

    for key, label in order:
        if categories.get(key):
            result += f"<b>{label}:</b>\n"
            for user in categories[key]:
                result += f"• {user}\n"
            result += "\n"

    await message.reply_text(result.strip(), parse_mode="HTML")
