from telegram import Update
from telegram.ext import ContextTypes


async def echo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.text:
        return

    text = message.text.lower()

    if "да" in text:
        await message.reply_text("пизда!")
    elif "артем" in text:
        await message.reply_text("Лох - Это судьба")
    elif "правила" in text:
        await message.reply_text("📝 Типо вот тебе правила группы")
    elif "помощь" in text:
        await message.reply_text("📌 Список команд бота и бла бла бла")
    else:
        pass  # можно оставить пустым или ответить echo
