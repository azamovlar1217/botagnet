"""Ikkinchi akkauntga QR-kod orqali kirish (kod kelmasa)."""
import asyncio
import getpass
import os
import tempfile

import qrcode
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "login.log")


def note(msg):
    print(msg)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


async def main():
    client = TelegramClient("caller", int(os.environ["TG_API_ID"]), os.environ["TG_API_HASH"])
    await client.connect()
    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"✅ Allaqachon kirilgan: {me.first_name}")
        return
    print("=" * 60)
    print(" IKKINCHI akkaunt telefonida:")
    print(" Telegram -> Settings (Sozlamalar) -> Devices (Qurilmalar)")
    print("   -> Link Desktop Device (Kompyuterni ulash)")
    print(" va ekrandagi QR-kodni skanerlang.")
    print("=" * 60)
    try:
        qr = await client.qr_login()
    except SessionPasswordNeededError:
        # QR allaqachon skanerlangan, faqat parol qoldi
        note("Ikki bosqichli parol so'ralmoqda")
        while True:
            pwd = getpass.getpass("\nIkki bosqichli himoya parolini kiriting (yozganda ko'rinmaydi) va Enter bosing: ")
            try:
                await client.sign_in(password=pwd)
                break
            except Exception as e:
                note(f"Parol noto'g'ri yoki xato: {type(e).__name__}. Qayta urinib ko'ring.")
        me = await client.get_me()
        note(f"\n✅ KIRILDI: {me.first_name}")
        await client.disconnect()
        return
    while True:
        path = os.path.join(tempfile.gettempdir(), "telegram_login_qr.png")
        qrcode.make(qr.url).save(path)
        try:
            import subprocess

            subprocess.Popen(["mspaint.exe", path])
            note("QR rasmi ochildi: " + path)
        except Exception as e:
            note(f"QR rasmini ochib bo'lmadi: {e}")
        q = qrcode.QRCode(border=1)
        q.add_data(qr.url)
        q.print_ascii(invert=True)
        note("QR tayyor, skanerlash kutilmoqda (60 soniya)...")
        try:
            await qr.wait(timeout=60)
            break
        except asyncio.TimeoutError:
            note("QR eskirdi, yangisi ochilmoqda...")
            await qr.recreate()
        except SessionPasswordNeededError:
            note("Ikki bosqichli parol so'ralmoqda")
            pwd = getpass.getpass("Ikki bosqichli himoya paroli (ko'rinmaydi): ")
            await client.sign_in(password=pwd)
            break
    me = await client.get_me()
    note(f"\n✅ KIRILDI: {me.first_name}")
    await client.disconnect()


try:
    asyncio.run(main())
except Exception as e:
    note(f"XATO: {type(e).__name__}: {e}")
input("\nOynani yopish uchun Enter bosing...")
