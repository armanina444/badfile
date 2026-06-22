import sqlite3
import requests
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
from openai import OpenAI

TOKEN = "8665268315:AAGcd1IAXaHbg-fUqniGRtEAVSuvLN8ix-8"
OPENROUTER_API_KEY = "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"

# غیرفعال کردن بررسی SSL
ssl._create_default_https_context = ssl._create_unverified_context

# تنظیم کلاینت OpenRouter
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

# بقیه کدهای شما (BAD_WORDS, db, contains_bad_word, get_warnings, set_warnings) به همین صورت می‌مانند...

async def classify_text(text: str) -> str:
    """ارسال متن به OpenRouter و دریافت نتیجه 1، 0 یا null"""
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
        
        # استفاده از OpenRouter
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model="openai/gpt-4o",  # یا هر مدل دیگری که می‌خواهید
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # برای دقت بالاتر
                max_tokens=10
            )
        )
        
        result = response.choices[0].message.content.strip()
        
        # بررسی اینکه نتیجه معتبر است
        if result in ["1", "0", "null"]:
            return result
        return "null"
        
    except Exception as e:
        print(f"Error in classification: {e}")
        return "null"

# بقیه کدهای شما (handle_message, main) به همین صورت می‌مانند...
