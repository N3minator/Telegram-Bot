import json
import os
from datetime import datetime, timedelta
from collections import defaultdict

STATS_PATH = "database/group_stats.json"


def load_stats():
    if not os.path.exists(STATS_PATH):
        return {}
    with open(STATS_PATH, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def save_stats(stats):
    with open(STATS_PATH, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)


def get_today_date():
    return datetime.utcnow().strftime("%Y-%m-%d")


def rotate_blocks(block_list, max_blocks=3):
    if len(block_list) > max_blocks:
        block_list.pop(0)
    return block_list


def update_message_stat(chat_id, user_id, username=None):
    stats = load_stats()
    chat_id = str(chat_id)
    today = get_today_date()

    if chat_id not in stats:
        stats[chat_id] = {
            "message_blocks": [],
            "active_blocks": [],
            "ban_blocks": [],
            "message_counters": {},
            "ban_counters": {}
        }

    chat = stats[chat_id]

    # === Message block ===
    if not chat["message_blocks"] or chat["message_blocks"][-1]["date"] != today:
        chat["message_blocks"].append({"date": today, "count": 0})
        chat["message_blocks"] = rotate_blocks(chat["message_blocks"], 3)

    chat["message_blocks"][-1]["count"] += 1

    # === Active users block ===
    if not chat["active_blocks"] or chat["active_blocks"][-1]["date"] != today:
        chat["active_blocks"].append({"date": today, "users": []})
        chat["active_blocks"] = rotate_blocks(chat["active_blocks"], 3)

    if user_id not in chat["active_blocks"][-1]["users"]:
        chat["active_blocks"][-1]["users"].append(user_id)

    # === User weekly message counter ===
    uid = str(user_id)
    if "message_counters" not in chat:
        chat["message_counters"] = {}
    if uid not in chat["message_counters"]:
        chat["message_counters"][uid] = {"count": 0, "username": username or ""}

    chat["message_counters"][uid]["count"] += 1
    if username:
        chat["message_counters"][uid]["username"] = username

    save_stats(stats)


def update_ban_stat(chat_id, admin_id, admin_username=None):
    stats = load_stats()
    chat_id = str(chat_id)
    today = get_today_date()

    if chat_id not in stats:
        stats[chat_id] = {
            "message_blocks": [],
            "active_blocks": [],
            "ban_blocks": [],
            "message_counters": {},
            "ban_counters": {}
        }

    chat = stats[chat_id]

    # === Ban block ===
    if not chat["ban_blocks"] or chat["ban_blocks"][-1]["date"] != today:
        chat["ban_blocks"].append({"date": today, "count": 0})
        chat["ban_blocks"] = rotate_blocks(chat["ban_blocks"], 7)

    chat["ban_blocks"][-1]["count"] += 1

    # === Admin ban counter ===
    aid = str(admin_id)
    if aid not in chat["ban_counters"]:
        chat["ban_counters"][aid] = {"count": 0, "username": admin_username or ""}

    chat["ban_counters"][aid]["count"] += 1
    if admin_username:
        chat["ban_counters"][aid]["username"] = admin_username

    save_stats(stats)


def get_3day_message_count(chat_id):
    stats = load_stats()
    blocks = stats.get(str(chat_id), {}).get("message_blocks", [])
    return sum(block["count"] for block in blocks)


def get_3day_active_users(chat_id):
    stats = load_stats()
    blocks = stats.get(str(chat_id), {}).get("active_blocks", [])
    users = set()
    for block in blocks:
        users.update(block["users"])
    return len(users)


def get_7day_bans(chat_id):
    stats = load_stats()
    blocks = stats.get(str(chat_id), {}).get("ban_blocks", [])
    return sum(block["count"] for block in blocks)


def get_top10_users(chat_id):
    stats = load_stats()
    counters = stats.get(str(chat_id), {}).get("message_counters", {})
    top = sorted(counters.items(), key=lambda x: x[1]["count"], reverse=True)[:10]
    return [(i + 1, v["username"], v["count"]) for i, (uid, v) in enumerate(top)]


def get_top5_banners(chat_id):
    stats = load_stats()
    counters = stats.get(str(chat_id), {}).get("ban_counters", {})
    top = sorted(counters.items(), key=lambda x: x[1]["count"], reverse=True)[:5]
    return [(i + 1, v["username"], v["count"]) for i, (uid, v) in enumerate(top)]
