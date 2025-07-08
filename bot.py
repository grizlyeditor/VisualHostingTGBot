import os, json, threading, subprocess
from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
from dotenv import load_dotenv

# Load .env
load_dotenv()
TOKEN = os.getenv("TOKEN")
BASE_DIR = "users"
os.makedirs(BASE_DIR, exist_ok=True)
user_sessions = {}

# Flask app
app = Flask(__name__)
application = None  # Global app instance for telegram

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[KeyboardButton("VisualHosting")], [KeyboardButton("JWT Generator")]]
    await update.message.reply_text("Choose an option:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

# Handle messages
async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = str(update.effective_user.id)
    folder = os.path.join(BASE_DIR, uid)
    os.makedirs(folder, exist_ok=True)

    if text == "VisualHosting":
        kb = [[KeyboardButton("Make"), KeyboardButton("Info")], [KeyboardButton("Back")]]
        await update.message.reply_text("Visual Hosting Options:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

    elif text == "Make":
        bot_file = os.path.join(folder, "bot.py")
        if not os.path.exists(bot_file):
            await update.message.reply_text("No `bot.py` found in your folder.")
            return
        if uid in user_sessions:
            await update.message.reply_text("Bot already running.")
            return
        await update.message.reply_text("Bot is starting... ✅")

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
        await update.message.reply_text(f"📂 Files:\n{file_list}\n\nStatus: {status}")

    elif text == "Back":
        await start(update, context)

    elif text == "JWT Generator":
        await update.message.reply_text("Please send `.json` file with UID & Password list.")

# Handle file upload
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = update.message.document
    uid = str(update.effective_user.id)
    folder = os.path.join(BASE_DIR, uid)
    os.makedirs(folder, exist_ok=True)

    file_path = os.path.join(folder, file.file_name)
    await file.get_file().download_to_drive(custom_path=file_path)
    await update.message.reply_text(f"File `{file.file_name}` saved!")

    if file.file_name.endswith(".json"):
        with open(file_path, "r") as f:
            try:
                creds = json.load(f)
            except:
                await update.message.reply_text("❌ Invalid JSON.")
                return

        await update.message.reply_text("Processing UIDs...\n")

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
            except Exception:
                results.append(f"{i}. ❌ Error")

        result_txt = "\n".join(results)
        await update.message.reply_text(f"✅ Done:\n{result_txt}")

# Set up Telegram app with handlers
async def setup_bot():
    global application
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    await application.initialize()
    await application.start()
    await application.updater.start_polling()  # Not required in webhook, but safe
    print("Bot started!")

# Flask endpoint to receive Telegram webhooks
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put(update)
    return "OK"

# Root route for test
@app.route("/", methods=["GET"])
def index():
    return "Bot is running ✅"

# Start everything
if __name__ == "__main__":
    import asyncio
    asyncio.run(setup_bot())
    app.run(host="0.0.0.0", port=10000)
