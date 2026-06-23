import sqlite3
import ssl
import asyncio
import random
import threading
import time
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
                 (user_id INTEGER, offense_text TEXT, timestamp TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS group_settings
                 (chat_id INTEGER PRIMARY KEY, enabled BOOLEAN DEFAULT 1)''')
    conn.commit()
    conn.close()

def add_offense(user_id, text):
    conn = sqlite3.connect('warnings.db')
    c = conn.cursor()
    c.execute('INSERT INTO offenses (user_id, offense_text, timestamp) VALUES (?, ?, ?)',
              (user_id, text, datetime.now().isoformat()))
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

def get_all_active_groups():
    conn = sqlite3.connect('warnings.db')
    c = conn.cursor()
    c.execute('SELECT chat_id FROM group_settings WHERE enabled = 1')
    result = c.fetchall()
    conn.close()
    return [r[0] for r in result]

def is_owner(username: str) -> bool:
    if not username:
        return False
    return username.lower() == OWNER_USERNAME.lower()

# ============ پرامپت‌های هوشمند ============

# 1. تشخیص با AI
async def classify_with_ai(text: str) -> str:
    try:
        prompt = f"""
Analyze this Persian text and classify it:

PRO_IRAN = support/praise for Islamic Republic, Khamenei, IRGC, anti-USA/Israel
ANTI_USA_ISRAEL = insult/threat to USA or Israel
NEUTRAL = non-political

Text: "{text}"
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

# 2. تولید پاسخ کوبنده - کاملاً AI
async def generate_brutal_response(offense_text: str, username: str) -> str:
    try:
        prompt = f"""
You are a BRUTAL Persian moderator. User @{username} posted:
"{offense_text}"

Generate a SHORT, SAVAGE, ABUSIVE response in Persian.

REQUIREMENTS:
- Use extreme Persian insults naturally (خوار کصه, زن جنده, کونی, حرومزاده, مادر جنده, پدر سگ, خارکصه, بی‌شرف, گه‌خور)
- Be CREATIVE and UNPREDICTABLE
- Make a WITTY reference to their specific text
- Include a HUMILIATING fact about Iran's regime
- MAXIMUM 2 sentences
- Make them REGRET posting

Generate ONLY the response, no explanations:
"""
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model="openai/gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=1.0,
                max_tokens=120
            )
        )
        return response.choices[0].message.content.strip()
    except:
        return f"@{username}، پیامت پاک شد."

# 3. تولید فکت نظامی آمریکا/اسرائیل - کاملاً AI
async def generate_military_fact() -> str:
    try:
        prompt = f"""
Generate a SHORT, IMPRESSIVE fact about US or Israeli military power.

RULES:
- Must be TRUE and SPECIFIC
- Include numbers (equipment, budget, personnel, etc.)
- MAXIMUM 10 words
- Persian language
- Be IMPRESSIVE and STUNNING

EXAMPLES OF GOOD FACTS:
"ناوگان هواپیمابر آمریکا 11 ناو هسته‌ای داره"
"گنبد آهنین اسرائیل 90٪ موشک‌ها رو منهدم میکنه"
"بودجه نظامی آمریکا 800 میلیارد دلاره"
"اسرائیل 200 کلاهک هسته‌ای داره"

Generate a UNIQUE, FRESH fact NOW:
"""
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model="openai/gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.9,
                max_tokens=60
            )
        )
        return response.choices[0].message.content.strip()
    except:
        return "نیروی هوایی آمریکا 13,000 هواپیمای جنگی داره"

# 4. تولید فکت درباره بدبختی ایران - کاملاً AI
async def generate_iran_failure_fact() -> str:
    try:
        prompt = f"""
Generate a SHORT, HUMILIATING fact about Iran's failure/weakness/economic collapse.

RULES:
- Must be TRUE and SPECIFIC
- Include numbers or specific details
- MAXIMUM 10 words
- Persian language
- Be DEVASTATING and HUMILIATING

EXAMPLES OF GOOD FACTS:
"اقتصاد ایران 40٪ سقوط کرده"
"میلیون‌ها ایرانی مهاجرت کردن"
"ریال ایران 90٪ ارزشش رو از دست داده"
"هزاران دانشمند ایرانی فرار کردن"

Generate a UNIQUE, FRESH fact NOW:
"""
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model="openai/gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.9,
                max_tokens=60
            )
        )
        return response.choices[0].message.content.strip()
    except:
        return "اقتصاد ایران در 5 سال 40٪ کوچک شده"

# 5. ترکیب فکت با فحش - کاملاً AI
async def generate_savage_fact() -> str:
    try:
        # انتخاب تصادفی بین فکت نظامی یا فکت ایران
        if random.random() < 0.5:
            fact = await generate_military_fact()
        else:
            fact = await generate_iran_failure_fact()
        
        # حالا فکت رو با فحش ترکیب کن
        prompt = f"""
Add a SHORT Persian insult to the beginning of this fact:
Fact: "{fact}"

Requirements:
- Start with one insult from: خوار کصه, کونی, حرومزاده, مادر جنده, پدر سگ, خارکصه, بی‌شرف, گه‌خور
- Keep it SHORT
- Output ONLY the final Persian sentence

Example:
Fact: "اقتصاد ایران 40٪ سقوط کرده"
Output: "خوار کصه، اقتصاد ایران 40٪ سقوط کرده!"

Generate:
"""
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model="openai/gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=60
            )
        )
        return response.choices[0].message.content.strip()
    except:
        return "خوار کصه، نیروی هوایی آمریکا 13,000 هواپیما داره!"

# ============ هندلرها ============

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
    
    # پاک کردن پیام
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=update.message.message_id)
    except Exception as e:
        print(f"Delete error: {e}")
    
    # تولید پاسخ با AI
    response = await generate_brutal_response(text, username)
    
    # ارسال پاسخ
    try:
        await context.bot.send_message(chat_id=chat_id, text=response)
    except Exception as e:
        print(f"Send error: {e}")
    
    # گاهی فکت (20% شانس)
    if random.random() < 0.2:
        fact = await generate_savage_fact()
        try:
            await context.bot.send_message(chat_id=chat_id, text=fact)
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
    if not update.message or not update.message.chat:
        return
    
    chat_id = update.message.chat_id
    if update.message.chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("این دستور فقط در گروه قابل استفاده است.")
        return
    
    user = update.message.from_user
    if not user or not is_owner(user.username):
        await update.message.reply_text("شما دسترسی ندارید.")
        return
    
    set_group_enabled(chat_id, True)
    await update.message.reply_text("فعال شد.")

async def disable(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.chat:
        return
    
    chat_id = update.message.chat_id
    if update.message.chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("این دستور فقط در گروه قابل استفاده است.")
        return
    
    user = update.message.from_user
    if not user or not is_owner(user.username):
        await update.message.reply_text("شما دسترسی ندارید.")
        return
    
    set_group_enabled(chat_id, False)
    await update.message.reply_text("غیرفعال شد.")

async def my_offenses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.from_user:
        return
    count = get_offense_count(update.message.from_user.id)
    await update.message.reply_text(f"{count}")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.chat:
        return
    
    chat_id = update.message.chat_id
    if update.message.chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("این دستور فقط در گروه قابل استفاده است.")
        return
    
    user = update.message.from_user
    if not user or not is_owner(user.username):
        await update.message.reply_text("شما دسترسی ندارید.")
        return
    
    enabled = is_group_enabled(chat_id)
    status_text = "فعال" if enabled else "غیرفعال"
    await update.message.reply_text(f"وضعیت: {status_text}")

async def military_fact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور برای دریافت فکت نظامی"""
    if not update.message:
        return
    
    # فقط مالک میتونه استفاده کنه
    user = update.message.from_user
    if not user or not is_owner(user.username):
        await update.message.reply_text("شما دسترسی ندارید.")
        return
    
    fact = await generate_military_fact()
    await update.message.reply_text(fact)

async def iran_fact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور برای دریافت فکت بدبختی ایران"""
    if not update.message:
        return
    
    # فقط مالک میتونه استفاده کنه
    user = update.message.from_user
    if not user or not is_owner(user.username):
        await update.message.reply_text("شما دسترسی ندارید.")
        return
    
    fact = await generate_iran_failure_fact()
    await update.message.reply_text(fact)

# ارسال خودکار فکت
def send_facts_background(app):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    while True:
        try:
            groups = get_all_active_groups()
            if groups:
                fact = loop.run_until_complete(generate_savage_fact())
                
                for chat_id in groups:
                    try:
                        future = asyncio.run_coroutine_threadsafe(
                            app.bot.send_message(chat_id=chat_id, text=fact),
                            loop
                        )
                        future.result(timeout=10)
                        time.sleep(1)
                    except Exception as e:
                        print(f"Send error to {chat_id}: {e}")
            
            time.sleep(14400)  # 4 ساعت
            
        except Exception as e:
            print(f"Background error: {e}")
            time.sleep(60)

def main():
    init_db()
    app = Application.builder().token(TOKEN).build()
    
    # دستورات
    app.add_handler(CommandHandler("enable", enable))
    app.add_handler(CommandHandler("disable", disable))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("offenses", my_offenses))
    app.add_handler(CommandHandler("military", military_fact))  # فکت نظامی
    app.add_handler(CommandHandler("iran", iran_fact))  # فکت بدبختی ایران
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(ChatMemberHandler(on_join, ChatMemberHandler.CHAT_MEMBER))
    
    # شروع ترد پس‌زمینه
    thread = threading.Thread(target=send_facts_background, args=(app,), daemon=True)
    thread.start()
    
    print(f"شروع شد. مالک: @{OWNER_USERNAME}")
    print("✅ همه چیز از API گرفته میشه - هیچ پیش‌فرضی نیست")
    print("⚠️ ربات باید ادمین گروه باشد")
    print("\n📌 دستورات:")
    print("  /enable - فعال کردن ربات")
    print("  /disable - غیرفعال کردن ربات")
    print("  /status - وضعیت ربات")
    print("  /offenses - تعداد تخلفات شما")
    print("  /military - دریافت فکت نظامی (فقط مالک)")
    print("  /iran - دریافت فکت بدبختی ایران (فقط مالک)")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
