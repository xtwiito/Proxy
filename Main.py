from keep_alive import keep_alive
keep_alive()

import os
import asyncio
import re
import aiohttp
import time
import random
import socket
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import MessageEntityTextUrl
from urllib.parse import parse_qs

# --- گرفتن اطلاعات محرمانه از متغیرهای محیطی ---
api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
session_str = os.getenv("SESSION_STRING")
ipinfo_token = os.getenv("IPINFO_TOKEN")
proxy_channels = os.getenv("CHANNELS").split(',')
target_channel = os.getenv("TARGET_CHANNEL")

# ساخت کلاینت تلگرام
client = TelegramClient(StringSession(session_str), api_id, api_hash)

regex_tg = re.compile(r'tg://proxy\?server=([^&]+)&port=(\d+)&secret=([a-fA-F0-9]+)')
regex_http = re.compile(r'https://t\.me/proxy\?([^ \n\r\t]+)')

async def ping_tcp(server, port, timeout=3):
    try:
        start = time.perf_counter()
        conn = asyncio.open_connection(server, int(port))
        reader, writer = await asyncio.wait_for(conn, timeout=timeout)
        end = time.perf_counter()
        writer.close()
        await writer.wait_closed()
        return int((end - start) * 1000)
    except:
        return None

async def get_country(address):
    try:
        try:
            ip = socket.gethostbyname(address)
        except:
            ip = address

        headers = {"Authorization": f"Bearer {ipinfo_token}"}
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://ipinfo.io/{ip}/json", headers=headers, timeout=5) as resp:
                data = await resp.json()
                return data.get("country", "Unknown"), data.get("country", "Unknown")
    except:
        return "Unknown", ""

def build_message(server, port, secret, fake_ping, country, country_code):
    proxy_link = f"tg://proxy?server={server}&port={port}&secret={secret}"
    flag = '🇺🇳'
    if country_code and len(country_code) == 2:
        flag = chr(0x1F1E6 + ord(country_code[0].upper()) - ord('A')) + chr(0x1F1E6 + ord(country_code[1].upper()) - ord('A'))
    score = round(10 - min(fake_ping / 100, 10), 1)
    connect_text = f'<a href="{proxy_link}">🔗 Connect Now 🔗</a>'
    spacer = " " * 18

    return f"""⚡⚡ <b>Tested and ready to connect</b> ⚡⚡

🌐 <b>Server:</b> {server}
📡 <b>Ping:</b> {fake_ping} ms
{flag} <b>Country:</b> {country}
⭐️ <b>Score:</b> {score}/10

{spacer}{connect_text}
""", proxy_link

def extract_proxies(text):
    proxies = []
    if not text:
        return proxies
    proxies += regex_tg.findall(text)
    for match in regex_http.findall(text):
        params = parse_qs(match)
        s, p, sec = params.get('server', [''])[0], params.get('port', [''])[0], params.get('secret', [''])[0]
        if s and p and sec:
            proxies.append((s, p, sec))
    return proxies

def extract_proxies_from_buttons(msg):
    proxies = []
    if msg.reply_markup and hasattr(msg.reply_markup, 'inline_keyboard'):
        for row in msg.reply_markup.inline_keyboard:
            for btn in row:
                url = getattr(btn, 'url', None)
                if url:
                    proxies += extract_proxies(url)
    return proxies

def extract_proxies_from_entities(msg):
    proxies = []
    if msg.entities:
        for entity in msg.entities:
            if isinstance(entity, MessageEntityTextUrl):
                proxies += extract_proxies(entity.url)
    return proxies

async def get_best_proxy():
    proxies, checked, valid = [], set(), []
    for ch in proxy_channels:
        print(f"📥 بررسی کانال: {ch}")
        try:
            async for msg in client.iter_messages(ch, limit=100):
                proxies += extract_proxies(msg.message)
                proxies += extract_proxies_from_buttons(msg)
                proxies += extract_proxies_from_entities(msg)
        except Exception as e:
            print(f"⚠️ خطا در کانال {ch}: {e}")

    print(f"🔍 مجموع پروکسی‌ها: {len(proxies)}")

    for server, port, secret in proxies:
        key = (server, port, secret)
        if key in checked:
            continue
        checked.add(key)
        country, code = await get_country(server)
        ping = await ping_tcp(server, port)
        if ping and ping < 300:
            # مرتب‌سازی بر اساس پینگ واقعی
            valid.append((server, port, secret, ping, country, code))

    valid.sort(key=lambda x: x[3])
    return valid[0] if valid else None

async def run_bot():
    await client.start()
    while True:
        print("\n🌀 شروع اسکن جدید...")
        best = await get_best_proxy()
        if best:
            s, p, sec, ping, country, code = best
            # اضافه کردن عدد رندوم فقط هنگام ساخت پیام
            fake_ping = ping + random.randint(50, 150)
            msg, link = build_message(s, p, sec, fake_ping, country, code)
            try:
                await client.send_message(target_channel, msg, parse_mode='html')
                print("✅ پروکسی ارسال شد.")
            except Exception as e:
                print(f"❌ خطا در ارسال: {e}")
        else:
            print("❌ پروکسی سالم پیدا نشد.")
        await asyncio.sleep(60)  # هر 60 ثانیه اسکن می‌کند

# اجرای برنامه
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_bot())
