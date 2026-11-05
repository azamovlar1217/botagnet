# Telegram AI-yordamchi

## U nima qiladi
- 💬 Siz bilan bot orqali o'zbekcha suhbatlashadi.
- 📞 «Onamga tel qil, ...», «menga 30 daqiqadan keyin tel qil» desangiz, Telegram orqali ovozli qo'ng'iroq qiladi va xabarni ovoz bilan o'qib beradi.
- 🕗 Har kuni belgilangan vaqtda ota-onangizga salom qo'ng'irog'ini qiladi.
- ↩️ Telegram akkauntingizga yozganlarga sizning nomingizdan javob beradi va sizga hisobot yuboradi.

## Nima uchun ikkita akkaunt kerak
Telegram botlari qo'ng'iroq qila olmaydi. Shuning uchun qo'ng'iroqni **alohida Telegram akkaunt** (qo'ng'iroqchi) qiladi.
Buning uchun ikkinchi SIM-karta bilan yangi Telegram akkaunt oching. Asosiy akkauntingizni ishlatmang.


## v2 — yangi imkoniyatlar
- 🛒 **Onam uchun bozor yordamchisi.** Botga `/taklif onam` yozing, chiqqan havolani onangizga yuboring. Onangiz bosgach:
  - uyga kerakli narsalar ro'yxatini birga tuzadi;
  - qancha pul borligini va necha kunga yetishi kerakligini so'raydi;
  - shu pulga **7 kunlik o'zbek milliy taomlari menyusi** va bozor ro'yxatini (miqdor, taxminiy narx) tuzadi;
  - bozorda mahsulot **rasmini** yuborsa — yaxshi-yomonligini va taxminiy narxini aytadi;
  - «go'shtni 110 mingga oldim» desa — yozib, qolgan pulni aytadi;
  - menyu, ro'yxat va budjet sizga ham keladi; har yakshanba ertalab onangizga eslatma yuboradi;
  - ovozli xabarga ovoz bilan javob beradi.
- ⏰ **Eslatmalar**: «ertaga 9 da dorini eslat».
- 🧠 **Doimiy xotira**: «eslab qol: ...». Suhbat va ma'lumotlar `agent.db` da saqlanadi — qayta ishga tushganda yo'qolmaydi.
- 🌤 **Ob-havo**, 💵 **valyuta kursi** (bepul, kalitsiz), ☀️ ertalabki xulosa (`MORNING_BRIEF`).
- 🖼 **Rasm tahlili**: botga rasm yuboring.
- ⚡ Tezroq javob (`THINKING_LEVEL=low`), uzun javoblar bo'lib yuboriladi, Markdown qoldiqlari tozalanadi.

Buyruqlar: `/taklif onam`, `/bozor`, `/eslatmalar`, `/xotira`, `/oila`, `/yangi`, `/avto`, `/kontaktlar`.

**Muhim:** kompyuter o'chiq bo'lsa ham bot ishlashi uchun uni bepul serverga (Oracle Cloud Always Free) joylang:
`bash deploy/deploy.sh <SERVER_IP>`.

## O'rnatish bosqichlari

### 1. Kerakli narsalarni oling
1. **Bot tokeni.** @BotFather → `/newbot` → token. So'ng `/mybots` → botingiz → *Bot Settings* → *Business Mode* → **Turn on**.
2. **OWNER_ID.** @userinfobot ga yozing, u sizning ID raqamingizni beradi.
3. **API_ID va API_HASH.** Qo'ng'iroqchi akkaunt bilan https://my.telegram.org saytiga kiring → *API development tools*.
4. **Gemini API kaliti (bepul).** https://aistudio.google.com/apikey saytida Google akkaunt bilan kiring → **Create API key**.
   Kalit `AIza...` bilan boshlanadi. Bepul rejada kunlik limit bor, lekin shaxsiy bot uchun yetarli.
5. **Kontaktlar.** Qo'ng'iroqchi akkauntning telefon kontaktlariga o'zingizni va ota-onangizni qo'shing.
   Shu akkauntdan ularga bir marta oddiy xabar yozib qo'ying.
   Ularning maxfiylik sozlamalarida qo'ng'iroqlarga ruxsat bo'lishi kerak.

### 2. VPS'da ishga tushirish (Ubuntu)
```bash
sudo apt update && sudo apt install -y python3 python3-venv ffmpeg
cd ~/telegram-agent
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env && nano .env      # qiymatlarni to'ldiring
python bot.py                           # birinchi marta: qo'ng'iroqchi akkaunt raqami va kodini kiriting
```
Shundan keyin `caller.session` fayli paydo bo'ladi va boshqa kod so'ralmaydi. Bu faylni hech kimga bermang.

### 3. Doimiy ishlashi uchun (systemd)
`/etc/systemd/system/agent.service`:
```ini
[Unit]
Description=Telegram AI agent
After=network.target

[Service]
WorkingDirectory=/root/telegram-agent
ExecStart=/root/telegram-agent/venv/bin/python bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl enable --now agent
journalctl -u agent -f     # loglarni ko'rish
```

### 4. Avto-javobni ulash
Telegram → *Settings* → *Telegram Business* → *Chatbots* → botingizning @username'ini kiriting va xabarlarga javob berishga ruxsat bering.
Bu funksiya uchun **Telegram Premium** kerak.

## Buyruqlar
- `/yangi`: suhbatni yangidan boshlaydi.
- `/avto`: avto-javobni yoqadi yoki o'chiradi.
- `/kontaktlar`: kontaktlar ro'yxatini ko'rsatadi.

## Bilish kerak
- Qo'ng'iroq bir tomonlama: bot xabarni o'qiydi, siz bilan jonli gaplashmaydi.
- «30 daqiqadan keyin» kabi rejalashtirilgan qo'ng'iroqlar bot qayta ishga tushsa o'chib ketadi.
- Begonalar avto-javob orqali qo'ng'iroq qila olmaydi. Bu imkoniyat faqat sizga ochiq.
