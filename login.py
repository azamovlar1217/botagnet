"""Qo'ng'iroqchi (ikkinchi) Telegram akkauntga bir marta kirish.
Natijada caller.session fayli yaratiladi, bot keyin shu fayldan foydalanadi."""
import asyncio
import os

from dotenv import load_dotenv
from telethon import TelegramClient

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))


async def main():
    print("=" * 60)
    print(" IKKINCHI (qo'ng'iroq qiladigan) akkaunt raqamini kiriting!")
    print(" Masalan: +998901234567")
    print(" Kod Telegram ilovasiga (shu akkauntga) keladi.")
    print("=" * 60)
    client = TelegramClient("caller", int(os.environ["TG_API_ID"]), os.environ["TG_API_HASH"])
    await client.start()
    me = await client.get_me()
    print(f"\n✅ Kirildi: {me.first_name} ({me.phone})")
    await client.disconnect()


asyncio.run(main())
input("\nOynani yopish uchun Enter bosing...")
