import json
import os

USERS_DB = "database/users.json"


# Загружаем пользователей из базы данных
def load_users():
    if not os.path.exists(USERS_DB):
        return {}
    with open(USERS_DB, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


# Сохраняем пользователей в базу данных
def save_users(users: dict):
    with open(USERS_DB, 'w') as f:
        json.dump(users, f, indent=2)


# Регистрируем пользователя в базе
def register_user(user):
    if not user.username:
        return
    users = load_users()
    users[user.username] = user.id
    save_users(users)


# Получаем ID пользователя по его username
def get_user_id_by_username(username: str):
    users = load_users()
    return users.get(username)
