import json
from datetime import datetime

# Время кулдауна (в секундах)
COOLDOWN_SECONDS_SENIOR = 3 * 60 * 60  # 3 часа
COOLDOWN_SECONDS_DEPUTY = 60  # 1 минута

# Название файла, где хранятся кулдауны
COOLDOWN_DB = "database/cooldowns.json"


def load_cooldowns():
    """
    Загружает данные из JSON-файла с кулдаунами.
    """
    try:
        with open(COOLDOWN_DB, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_cooldowns(cooldowns: dict):
    """
    Сохраняет данные в JSON-файл с отступами и без ASCII-escape,
    чтобы в тексте нормально отображались эмодзи и кириллица.
    """
    with open(COOLDOWN_DB, "w", encoding="utf-8") as f:
        json.dump(cooldowns, f, indent=2, ensure_ascii=False)


def check_cooldown(chat_id: str, user_id: str, admin_level: str):
    """
    Проверяет, есть ли ещё «остаток» кулдауна для данного админа.
    Если кулдаун не истёк, возвращает строку вида '1 ч 2 мин 5 сек'.
    Если кулдауна нет — возвращает None.
    """
    data = load_cooldowns()
    now = datetime.utcnow()

    # Проверяем, есть ли данные по данному чату
    if chat_id not in data:
        return None

    # И есть ли в этом чате записи по админам
    admins_block = data[chat_id].get("админы")
    if not admins_block or user_id not in admins_block:
        return None

    # Берём поле "последнее_использование" и вычисляем, сколько времени прошло
    last_used_str = admins_block[user_id].get("последнее_использование")
    if not last_used_str:
        return None

    last_time = datetime.fromisoformat(last_used_str)
    delta = now - last_time
    remaining = 0

    # Логика по уровням админов и кулдаун-секундам
    if admin_level == "Соруководитель" and delta.total_seconds() < COOLDOWN_SECONDS_SENIOR:
        remaining = COOLDOWN_SECONDS_SENIOR - delta.total_seconds()
    elif admin_level == "Заместитель Главы" and delta.total_seconds() < COOLDOWN_SECONDS_DEPUTY:
        remaining = COOLDOWN_SECONDS_DEPUTY - delta.total_seconds()

    if remaining > 0:
        hrs, rem = divmod(int(remaining), 3600)
        mins, secs = divmod(rem, 60)
        parts = []
        if hrs: parts.append(f"{hrs} ч")
        if mins: parts.append(f"{mins} мин")
        if secs: parts.append(f"{secs} сек")
        return ' '.join(parts)

    return None


def update_cooldown(chat_id: str, user_id: str, admin_username: str, chat_title: str):
    """
    Записывает в файл новую отметку времени (last_used),
    а также информацию об администраторе и названии чата.
    """
    data = load_cooldowns()
    now = datetime.utcnow()

    # Если в файле ещё нет информации по этому чату, создаём "блок" для него
    if chat_id not in data:
        data[chat_id] = {
            "Название группы": chat_title,
            "ID группы": chat_id,
            "админы": {}
        }

    # Обновим название группы и ID (вдруг изменилось название, или хотим явно хранить)
    data[chat_id]["Название группы"] = chat_title
    data[chat_id]["ID группы"] = chat_id

    # Создаём/обновляем информацию по конкретному админу
    data[chat_id]["админы"][user_id] = {
        "имя_админа": admin_username,
        "ID админа": user_id,
        "Описание": "⌛ Кулдаун после использования !ban",
        "последнее_использование": now.isoformat()
    }

    # Сохраняем изменения в файл
    save_cooldowns(data)
