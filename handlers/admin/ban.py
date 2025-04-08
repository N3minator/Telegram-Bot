import json
import os
import re
from datetime import datetime, timedelta
from telegram import Update, ChatMember
from telegram.ext import ContextTypes
from utils.users import get_user_id_by_username
from asyncio import create_task, sleep
from handlers.admin.cooldown_admin import check_cooldown, update_cooldown

ADMIN_DB = "database/admin_db.json"


def load_admins():
    if not os.path.exists(ADMIN_DB):
        return {}
    with open(ADMIN_DB, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return {}


def get_admin_level(user_id: str, chat_id: str, admins: dict) -> str:
    if chat_id in admins and user_id in admins[chat_id].get("admins", {}):
        return admins[chat_id]["admins"][user_id].get("level", "")
    return ""


def parse_duration(text: str):
    time_map = {
        'r': 31536000, 'д': 86400, 'd': 86400,
        'ч': 3600, 'h': 3600,
        'м': 60, 'm': 60,
        'с': 1, 's': 1
    }
    name_map = {
        'r': 'лет', 'д': 'дней', 'd': 'дней',
        'ч': 'часов', 'h': 'часов',
        'м': 'минут', 'm': 'минут',
        'с': 'секунд', 's': 'секунд'
    }
    total_seconds = 0
    readable = []
    found = re.findall(r'(\d+)([rdчdhмmsс])', text)
    for value, unit in found:
        total_seconds += int(value) * time_map[unit]
        readable.append(f"{value} {name_map[unit]}")
    return total_seconds, ', '.join(readable)


async def unban_after_delay(context, chat_id, user_id, delay):
    await sleep(delay)
    try:
        await context.bot.unban_chat_member(chat_id, int(user_id), only_if_banned=True)
    except Exception:
        pass


async def ban_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    chat = update.effective_chat
    user = update.effective_user
    chat_id = str(chat.id)
    user_id = str(user.id)
    admins = load_admins()

    parts = message.text.strip().split(maxsplit=2)
    if not parts or len(parts) < 2:
        await message.reply_text("Укажите пользователя и причину, например:\n!ban @user причина 1d2h")
        return

    # Проверка кулдауна через функции из coldown_admin.py
    admin_level = get_admin_level(user_id, chat_id, admins)
    remaining = check_cooldown(chat_id, user_id, admin_level)
    if remaining:
        await message.reply_text(f"⏳ Подождите {remaining} до следующего использования !ban.")
        return

    # Определение цели
    reason = ""
    duration_text = ""
    duration_seconds = 0
    formatted_duration = ""
    target_user_id = None
    target_username = None

    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
        target_user_id = str(target_user.id)
        target_username = target_user.username
        reason = parts[1] if len(parts) > 1 else ""
        if len(parts) > 2:
            duration_text = parts[2]
    else:
        if len(parts) < 3:
            await message.reply_text("Формат: !ban @user причина 1d2h")
            return
        target = parts[1]
        reason = parts[2]
        if target.startswith("@"):
            username = target[1:]
            uid = get_user_id_by_username(username)
            if not uid:
                await message.reply_text("Пользователь не найден в базе.")
                return
            target_user_id = str(uid)
            target_username = username
        elif target.isdigit():
            target_user_id = target
        else:
            await message.reply_text("Укажите корректный @username или ID.")
            return

    # Проверка прав вызывающего
    try:
        requester_status = await context.bot.get_chat_member(chat.id, user.id)
        if requester_status.status != ChatMember.OWNER:
            requester_level = get_admin_level(str(user.id), chat_id, admins)
            if requester_level not in ["Соруководитель", "Заместитель Главы"]:
                await message.reply_text("⛔ У вас нет прав для выполнения этой команды.")
                return
    except Exception:
        await message.reply_text("Не удалось проверить ваши права.")
        return

    # Нельзя банить владельца
    try:
        target_status = await context.bot.get_chat_member(chat.id, int(target_user_id))
        if target_status.status == ChatMember.OWNER:
            await message.reply_text("Нельзя забанить владельца группы.")
            return
    except Exception:
        await message.reply_text("Не удалось проверить пользователя.")
        return

    # Получаем уровни администраторов
    requester_level = get_admin_level(str(user.id), chat_id, admins)
    target_level = get_admin_level(str(target_user_id), chat_id, admins)

    # Соруководитель не может банить другого соруководителя или заместителя
    if requester_level == "Соруководитель" and target_level in ["Соруководитель", "Заместитель Главы"]:
        await message.reply_text("⛔ Соруководитель не может забанить администратора своего же ранга или выше.")
        return

    # Заместитель Главы не может банить другого заместителя
    if requester_level == "Заместитель Главы" and target_level == "Заместитель Главы":
        await message.reply_text("⛔ Заместитель Главы не может забанить другого Заместителя Главы.")
        return

    # Парсинг срока
    duration_seconds, formatted_duration = parse_duration(reason)
    if duration_seconds > 0:
        reason_parts = reason.rsplit(' ', 1)
        reason = reason_parts[0] if len(reason_parts) == 2 else "Без причины"
        duration_text = formatted_duration

    if not reason:
        await message.reply_text("Вы должны указать причину бана.")
        return

    try:
        # Эта строка отвечает за блокировку пользователя
        await context.bot.ban_chat_member(chat.id, int(target_user_id))

        mention = f"@{target_username}" if target_username else f"<a href='tg://user?id={target_user_id}'>Пользователь</a>"
        admin_mention = user.mention_html()
        group_title = chat.title or "группа"

        text = (
            f"<b>👤 Участник {mention} был заблокирован</b>\n"
            f"<b>👮 Администратором</b> {admin_mention}\n"
            f"📝 Причина: <b>{reason}</b>"
        )

        if duration_seconds:
            unban_time = datetime.utcnow() + timedelta(seconds=duration_seconds) + timedelta(hours=2)
            formatted = unban_time.strftime('%Y-%m-%d %H:%M:%S GMT+2')
            text += f"\n⏳ Срок: {formatted_duration}\n🔓 Разбан в: <b>{formatted}</b>"
            create_task(unban_after_delay(context, chat.id, target_user_id, duration_seconds))

        await message.reply_text(text, parse_mode="HTML")

        # ЛС уведомление
        try:
            private_text = (
                f"🚫 Вы были забанены в группе <b>{group_title}</b>!\n\n"
                f"👮 Администратор: {admin_mention}\n"
                f"📝 Причина: <b>{reason}</b>"
            )
            if duration_seconds:
                private_text += f"\n⏳ Срок: {formatted_duration}\n🔓 Разбан в: <b>{formatted}</b>"
            await context.bot.send_message(chat_id=int(target_user_id), text=private_text, parse_mode="HTML")
        except Exception:
            pass

        # Обновляем кулдаун через coldown_admin.py
        update_cooldown(chat_id, user_id, user.username, group_title)

    except Exception as e:
        await message.reply_text(f"Ошибка при бане: {e}")
