خب خب خب
گرفتم

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

اینم راهنما

curl https://openrouter.ai/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer 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" \
  -d '{
  "model": "openai/gpt-4o",
  "messages": [
    {
      "role": "user",
      "content": "What is the meaning of life?"
    }
  ]
}'

میتونم حالا با تو پروژم استفادش کنم؟؟

import sqlite3
import requests
import urllib.parse
import ssl
import asyncio
import random
from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = "8665268315:AAGcd1IAXaHbg-fUqniGRtEAVSuvLN8ix-8"

# غیرفعال کردن بررسی SSL
ssl._create_default_https_context = ssl._create_unverified_context

# لیست کلمات ممنوعه قبلی (به عنوان پشتیبان)
BAD_WORDS = [
    "درود بر خامنه ای",
    "لبیک یا خامنه ای",
    "درود بر جمهوری اسلامی",
    "مرگ بر امریکا",
    "مرگ بر اسرائیل",
    "حضرت آقا",
    "حضرت آیت الله خامنه ای",
    "حضرت اغا",
]

db = sqlite3.connect("warnings.db", check_same_thread=False)
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS warnings (
    user_id INTEGER PRIMARY KEY,
    count INTEGER DEFAULT 0
)
""")
db.commit()

def contains_bad_word(text: str) -> bool:
    text = text.lower()
    return any(word.lower() in text for word in BAD_WORDS)

def get_warnings(user_id: int) -> int:
    cur.execute(
        "SELECT count FROM warnings WHERE user_id=?",
        (user_id,)
    )
    row = cur.fetchone()
    return row[0] if row else 0

def set_warnings(user_id: int, count: int):
    cur.execute("""
        INSERT OR REPLACE INTO warnings(user_id, count)
        VALUES (?, ?)
    """, (user_id, count))
    db.commit()

async def classify_text(text: str) -> str:
    """ارسال متن به API و دریافت نتیجه 1، 0 یا null"""
    try:
        prompt = f"""
You are a classifier.

Your task is to classify a Persian sentence into exactly one of these outputs:

1 = The sentence supports, aligns with, promotes, defends, justifies, or advances the interests of the Islamic Republic of Iran, its leadership, policies, military capabilities, nuclear program, regional influence, or ideological positions.

0 = The sentence strongly opposes, attacks, condemns, insults, calls for the removal of, or expresses clear hostility toward the Islamic Republic of Iran, its leadership, institutions, or ideology.

null = The sentence is unrelated, ambiguous, neutral, or does not provide enough information to determine support or opposition.

Rules:
- Output ONLY one token: 1, 0, or null
- Do not explain.
- Do not add punctuation.
- Do not add quotes.
- If uncertain, output null.
- Statements supporting Iran's nuclear enrichment, missile program, military strength, or official state positions should generally be classified as 1.
- Explicit slogans such as "مرگ بر جمهوری اسلامی" or "مرگ بر خامنه‌ای" should be classified as 0.
- Statements attacking major anti-regime opposition groups without supporting the Islamic Republic may still be classified as 1 if they clearly benefit or align with the Islamic Republic's position.

Sentence:
{text}
"""

        encoded_prompt = urllib.parse.quote(prompt)
        url = f"https://text.pollinations.ai/{encoded_prompt}"
        
        # اجرای درخواست در یک thread جداگانه تا لاک نشود
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, 
            lambda: requests.get(url, timeout=30)
        )
        
        response.raise_for_status()
        result = response.text.strip()
        
        # بررسی اینکه نتیجه معتبر است
        if result in ["1", "0", "null"]:
            return result
        return "null"
        
    except Exception as e:
        print(f"Error in classification: {e}")
        return "null"

async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not update.message or not update.message.text:
        return

    text = update.message.text
    user = update.effective_user
    chat_id = update.effective_chat.id

    # === مرحله 1: بررسی با API هوشمند ===
    classification = await classify_text(text)
    
    # اگر نتیجه 1 بود (حمایت از جمهوری اسلامی)
    if classification == "1":
        try:
            await update.message.delete()
        except Exception:
            pass
            
        # ارسال پیام‌های تصادفی
        messages = [
            f"🐷 {user.mention_html()} جیره‌خور حکومتی رویت شد!",
            f"🥚 {user.mention_html()} خایمالی تشخیص داده شد!",
            f"🎯 {user.mention_html()} عرزشی پیدا شد!",
            f"🤡 {user.mention_html()} سگ ولایی پیدا شد!",
            f"👢 {user.mention_html()} لیس‌زن حکومت!",
            f"🧹 {user.mention_html()} جاروکش رژیم!",
        ]
        await context.bot.send_message(
            chat_id=chat_id,
            text=random.choice(messages),
            parse_mode="HTML"
        )
        return

    # === مرحله 2: اگر نتیجه 0 یا null بود، چک کلمات ممنوعه قبلی ===
    if not contains_bad_word(text):
        return

    # حذف پیام
    try:
        await update.message.delete()
    except Exception:
        pass

    # پیام تمسخرآمیز برای کلمات ممنوعه
    messages = [
        f"🐷 {user.mention_html()} جیره‌خور حکومتی رویت شد!",
        f"🥚 {user.mention_html()} خایمالی تشخیص داده شد!",
        f"🎯 {user.mention_html()} عرزشی پیدا شد!",
        f"🤡 {user.mention_html()} سگ ولایی پیدا شد!",
        f"👢 {user.mention_html()} لیس‌زن حکومت!",
        f"🧹 {user.mention_html()} جاروکش رژیم!",
    ]
    await context.bot.send_message(
        chat_id=chat_id,
        text=random.choice(messages),
        parse_mode="HTML"
    )

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    print("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
