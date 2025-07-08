import os, json, threading, subprocess, uuid, time
from telegram import ReplyKeyboardMarkup, KeyboardButton, Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import requests

TOKEN = "7718570853:AAGLRnxyQ-GJm2qvmQ7VXC-WEzgdK6DBQ1I"
BASE_DIR = "users"
os.makedirs(BASE_DIR, exist_ok=True)
user_sessions = {}

def start(update: Update, context: CallbackContext):
    kb = [[KeyboardButton("VisualHosting")], [KeyboardButton("JWT Generator")]]
    update.message.reply_text("Choose an option:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

def handle_msg(update: Update, context: CallbackContext):
    text = update.message.text
    uid = str(update.effective_user.id)
    folder = os.path.join(BASE_DIR, uid)
    os.makedirs(folder, exist_ok=True)

    if text == "VisualHosting":
        kb = [[KeyboardButton("Make"), KeyboardButton("Info")], [KeyboardButton("Back")]]
        update.message.reply_text("Visual Hosting Options:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

    elif text == "Make":
        bot_file = os.path.join(folder, "bot.py")
        if not os.path.exists(bot_file):
            update.message.reply_text("No `bot.py` found in your folder.")
            return
        if uid in user_sessions:
            update.message.reply_text("Bot already running.")
            return
        update.message.reply_text("Bot is starting... ✅")

        # Run in background
        def run():
            p = subprocess.Popen(["python3", bot_file], cwd=folder)
            user_sessions[uid] = p
            p.wait()
            user_sessions.pop(uid, None)

        threading.Thread(target=run).start()

    elif text == "Info":
        files = os.listdir(folder)
        status = "🟢 ON" if uid in user_sessions else "🔴 OFF"
        file_list = "\n".join(files)
        update.message.reply_text(f"📂 Files:\n{file_list}\n\nStatus: {status}")

    elif text == "Back":
        start(update, context)

    elif text == "JWT Generator":
        update.message.reply_text("Please send `.json` file with UID & Password list.")

def handle_file(update: Update, context: CallbackContext):
    file = update.message.document
    uid = str(update.effective_user.id)
    folder = os.path.join(BASE_DIR, uid)
    os.makedirs(folder, exist_ok=True)

    file_path = os.path.join(folder, file.file_name)
    file.get_file().download(custom_path=file_path)
    update.message.reply_text(f"File `{file.file_name}` saved!")

    if file.file_name.endswith(".json"):
        with open(file_path, "r") as f:
            try:
                creds = json.load(f)
            except:
                update.message.reply_text("❌ Invalid JSON.")
                return

        update.message.reply_text("Processing UIDs...\n")

        results = []
        for i, entry in enumerate(creds, start=1):
            uid_ = entry.get("uid")
            pwd = entry.get("password")
            if not uid_ or not pwd:
                results.append(f"{i}. Skipped (invalid entry)")
                continue

            url = f"https://jw-ttoken.vercel.app/token?uid={uid_}&password={pwd}"
            try:
                r = requests.get(url)
                token = r.text.strip()
                results.append(f"{i}. ✅ Token: `{token}`")
            except Exception as e:
                results.append(f"{i}. ❌ Error")

        result_txt = "\n".join(results)
        update.message.reply_text(f"✅ Done:\n{result_txt}")

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_msg))
    dp.add_handler(MessageHandler(Filters.document, handle_file))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()