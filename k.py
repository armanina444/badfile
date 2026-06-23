import sqlite3
import ssl
import asyncio
import random
from datetime import datetime
from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    ContextTypes,
    filters,
    CommandHandler,
    ChatMemberHandler,
)
from openai import OpenAI

# توکن‌ها
TOKEN = "8665268315:AAGcd1IAXaHbg-fUqniGRtEAVSuvLN8ix-8"
OPENROUTER_API_KEY = "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"

# فقط این کاربر کنترل میکنه
OWNER_USERNAME = "armansdz"

# غیرفعال کردن SSL
ssl._create_default_https_context = ssl._create_unverified_context

# کلاینت OpenRouter
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

# دیتابیس
def init_db():
    conn = sqlite3.connect('warnings.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS offenses
                 (user_id INTEGER, offense_text TEXT, timestamp TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS group_settings
                 (chat_id INTEGER PRIMARY KEY, enabled BOOLEAN DEFAULT 1)''')
    conn.commit()
    conn.close()

def add_offense(user_id, text):
    conn = sqlite3.connect('warnings.db')
    c = conn.cursor()
    c.execute('INSERT INTO offenses (user_id, offense_text, timestamp) VALUES (?, ?, ?)',
              (user_id, text, datetime.now()))
    conn.commit()
    conn.close()

def get_offense_count(user_id):
    conn = sqlite3.connect('warnings.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM offenses WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0

def is_group_enabled(chat_id):
    conn = sqlite3.connect('warnings.db')
    c = conn.cursor()
    c.execute('SELECT enabled FROM group_settings WHERE chat_id = ?', (chat_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else True

def set_group_enabled(chat_id, enabled):
    conn = sqlite3.connect('warnings.db')
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO group_settings (chat_id, enabled) VALUES (?, ?)',
              (chat_id, enabled))
    conn.commit()
    conn.close()

# چک کردن مالک
def is_owner(username: str) -> bool:
    return username and username.lower() == OWNER_USERNAME.lower()

# تشخیص با AI
async def classify_with_ai(text: str) -> str:
    try:
        prompt = f"""
Classify this Persian text into one word:
PRO_IRAN = support for Islamic Republic, Khamenei, IRGC, anti-USA/Israel
ANTI_USA_ISRAEL = insult to USA or Israel
NEUTRAL = non-political

Text: {text}
Output ONLY one word:
"""
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model="openai/gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=10
            )
        )
        result = response.choices[0].message.content.strip()
        return result if result in ["PRO_IRAN", "ANTI_USA_ISRAEL"] else "NEUTRAL"
    except:
        return "NEUTRAL"

# تولید پاسخ کوبنده با فحش
async def generate_response(offense_text: str, username: str, count: int) -> str:
    try:
        prompt = f"""
Generate a SHORT, BRUTAL, ABUSIVE Persian response to @{username} who posted this:
"{offense_text}"

Rules:
- Use these insults: خوار کصه, زن جنده, خواهر گاو باز, کونی, حرومزاده, مادر جنده
- Make fun of their text with a smart reference
- MAXIMUM 2 sentences
- Include a humiliating fact about Iran/Khamenei/IRGC
- No extra text, just the insult

Examples:
"ای خوار کصه، خامنه‌ای که ازش حمایت میکنی هنوز تو یخچاله، برو آمار تورم رو ببین!"
"خواهر گاو باز، اسرائیل رو توهین میکنی ولی با اینترنت آمریکایی داری پیام می‌دی؟ کونی!"

Generate:
"""
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model="openai/gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.9,
                max_tokens=100
            )
        )
        return response.choices[0].message.content.strip()
    except:
        insults = ["خوار کصه", "زن جنده", "کونی", "حرومزاده", "مادر جنده"]
        return f"ای {random.choice(insults)}، پیام کثیفت پاک شد!"

# تولید فکت
async def generate_fact() -> str:
    try:
        prompt = """
Generate ONE SHORT Persian sentence with an insult about Iran regime:
- Use: خوار کصه, کونی, حرومزاده, مادر جنده
- Include a humiliating fact
- MAXIMUM 10 words
"""
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model="openai/gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                max_tokens=50
            )
        )
        return response.choices[0].message.content.strip()
    except:
        return "ای کونی، اقتصاد ایران نابود شده!"

# هندلر اصلی
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    
    chat_id = update.message.chat_id
    if update.message.chat.type not in ["group", "supergroup"]:
        return
    if not is_group_enabled(chat_id):
        return
    
    user = update.message.from_user
    text = update.message.text
    username = user.username or f"User_{user.id}"
    
    # تشخیص با AI
    category = await classify_with_ai(text)
    if category == "NEUTRAL":
        return
    
    # ثبت تخلف
    add_offense(user.id, text)
    count = get_offense_count(user.id)
    
    # پاک کردن پیام
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=update.message.message_id)
    except:
        pass
    
    # پاسخ کوبنده
    response = await generate_response(text, username, count)
    await update.message.reply_text(response, quote=False)
    
    # گاهی فکت (30% شانس)
    if random.random() < 0.3:
        fact = await generate_fact()
        await update.message.reply_text(fact, quote=False)

# ارسال خودکار فکت به همه گروه‌ها
async def send_fact_to_all(context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect('warnings.db')
    c = conn.cursor()
    c.execute('SELECT chat_id FROM group_settings WHERE enabled = 1')
    groups = c.fetchall()
    conn.close()
    
    fact = await generate_fact()
    for group in groups:
        try:
            await context.bot.send_message(chat_id=group[0], text=fact)
            await asyncio.sleep(1)
        except:
            pass

# وقتی ربات اضافه شد
async def on_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.chat_member:
        return
    chat = update.chat_member.chat
    if chat.type not in ["group", "supergroup"]:
        return
    if update.chat_member.new_chat_member.status == "member":
        set_group_enabled(chat.id, True)
        await context.bot.send_message(chat_id=chat.id, text="فعال شدم.")

# دستورات - فقط برای مالک
async def enable(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    if not is_owner(user.username):
        await update.message.reply_text("شما دسترسی ندارید.")
        return
    
    chat_id = update.message.chat_id
    set_group_enabled(chat_id, True)
    await update.message.reply_text("فعال شد.")

async def disable(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    if not is_owner(user.username):
        await update.message.reply_text("شما دسترسی ندارید.")
        return
    
    chat_id = update.message.chat_id
    set_group_enabled(chat_id, False)
    await update.message.reply_text("غیرفعال شد.")

async def my_offenses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    count = get_offense_count(update.message.from_user.id)
    await update.message.reply_text(f"{count}")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    if not is_owner(user.username):
        await update.message.reply_text("شما دسترسی ندارید.")
        return
    
    chat_id = update.message.chat_id
    enabled = is_group_enabled(chat_id)
    status_text = "فعال" if enabled else "غیرفعال"
    await update.message.reply_text(f"وضعیت: {status_text}")

def main():
    init_db()
    app = Application.builder().token(TOKEN).build()
    
    # دستورات
    app.add_handler(CommandHandler("enable", enable))
    app.add_handler(CommandHandler("disable", disable))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("offenses", my_offenses))
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(ChatMemberHandler(on_join, ChatMemberHandler.CHAT_MEMBER))
    
    # ارسال خودکار فکت هر 4 ساعت
    app.job_queue.run_repeating(send_fact_to_all, interval=14400, first=30)
    
    print(f"شروع شد. مالک: @{OWNER_USERNAME}")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
