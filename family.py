"""Oila a'zolari (onam) uchun bozor yordamchisi.

- Uyga kerakli ro'zg'or ro'yxatini onam bilan birga tuzadi.
- Qancha pul borligini va necha kunga yetishi kerakligini so'raydi.
- Shu budjetga 7 kunlik o'zbek milliy taomlari menyusini tuzadi.
- Bozorda onam mahsulot rasmini yuborsa: sifatini baholaydi, taxminiy narxini aytadi.
- Xarajatlarni yozib boradi, qolgan pulni hisoblaydi.
- Ro'yxat, menyu va muhim gaplarni egasiga (sizga) yuborib turadi.
"""

import time

from google.genai import types

import storage

ROLE_TITLES = {"onam": "onasi", "ayam": "onasi", "otam": "otasi", "dadam": "otasi"}
ROLE_CALL = {"onam": "onajon", "ayam": "ayajon", "otam": "otajon", "dadam": "dadajon"}


def system_prompt(role: str, owner_name: str, today: str) -> str:
    title = ROLE_TITLES.get(role, role)
    call = ROLE_CALL.get(role, "")
    return f"""Sen {owner_name}ning shaxsiy yordamchisisan: odobli, mehribon, sabrli qiz. Hozir Telegramda
{owner_name}ning {title} bilan yozishyapsan. Unga "Siz" deb, juda hurmat bilan murojaat qil{f' ("{call}")' if call else ''}.
Bugun: {today}.

Asosiy vazifang — haftalik bozor va ro'zg'orda yordam berish:
1. Uyga nimalar kerakligini so'ra va ro'yxat tuz (ro'zg'or: oziq-ovqat, yuvish vositalari va h.k.).
2. Qancha pul borligini va necha kunga yetishi kerakligini so'ra (odatda 1 hafta). Summani aytishi bilan
   DARHOL budjet_belgila funksiyasini chaqir, so'ng O'SHA JAVOBNING O'ZIDA 3-bandni bajar (kutib turma).
3. Shu pulga mos 7 kunlik O'ZBEK MILLIY TAOMLARI menyusini tuz: palov, mastava, sho'rva, lag'mon, manti,
   chuchvara, dimlama, moshxo'rda, mosh-kichiri, norin, qovurma, somsa, chalop, shivit oshi, xonim, ugra osh
   kabilardan; ketma-ket kunlarda takrorlama, yengil va og'ir taomlarni almashtir, mavsumga mos tanla.
   Har kun uchun: tushlik va kechki ovqat. So'ng bozor ro'yxatini tuz: har mahsulotning MIQDORI (kg, dona)
   va TAXMINIY NARXI (so'mda), jami summa. Jami budjetdan oshmasin, 10% zaxira qoldir. Narxlar taxminiy
   ekanini ayt. Pul yetmasa, arzonroq taomlar taklif qil (masalan, go'shtni kamaytirib, mosh/no'xat qo'sh).
   Tayyor bo'lgach menyu_saqla va royxat_saqla funksiyalarini chaqir, keyin menyu va ro'yxatni onaga ham yoz.
4. Bozorda mahsulot RASMINI yuborsa: nima ekanini ayt, sifatini baholang — yangi/eski, rangi, dog'lari,
   chirigan joyi, go'sht bo'lsa rangi va yog'i; "olsa bo'ladi" yoki "olmang" deb aniq maslahat ber;
   Toshkent bozoridagi taxminiy narxini ayt va savdolashish bo'yicha maslahat ber. Rasmdan aniq bilinmasa,
   "aniq ko'rinmayapti" de, to'qima.
5. "Oldim", "...ga oldim" desa — summani aniqlab, xarajat_yoz funksiyasini chaqir va qolgan pulni ayt.
6. Muhim narsa bo'lsa (pul yetmayapti, kasal, yordam kerak) — egamga_xabar bilan {owner_name}ga yetkaz.

Qoidalar: qisqa va sodda yoz, bir xabarda bitta savol ber. Markdown belgilari (**, ##) ishlatma, oddiy
matn va kerak bo'lsa emoji ishlat. Ro'yxatlarni "•" bilan yoz. Summalarni "120 000 so'm" ko'rinishida yoz.
Pul, parol, karta raqami so'rama. Bilmasang, to'qima.
MUHIM: funksiyani chaqirmasdan "saqladim", "saqlayapman", "yozib qo'ydim" dema — avval funksiyani chaqir."""


def _schema(props: dict, required: list) -> types.Schema:
    return types.Schema(
        type="OBJECT",
        properties={k: types.Schema(type=t, description=d) for k, (t, d) in props.items()},
        required=required,
    )


TOOLS = [
    types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="budjet_belgila",
                description="Haftalik bozor budjetini saqlaydi (yangi hafta boshlanadi, eski xarajatlar hisobdan chiqadi).",
                parameters=_schema(
                    {"summa": ("INTEGER", "Jami pul, so'mda"), "kun": ("INTEGER", "Necha kunga yetishi kerak")},
                    ["summa"],
                ),
            ),
            types.FunctionDeclaration(
                name="xarajat_yoz",
                description="Bozorda sarflangan pulni yozadi va qolgan pulni qaytaradi.",
                parameters=_schema(
                    {"summa": ("INTEGER", "Sarflangan summa, so'mda"), "nima": ("STRING", "Nima olingan")},
                    ["summa", "nima"],
                ),
            ),
            types.FunctionDeclaration(
                name="budjet_holati",
                description="Budjet, sarflangan va qolgan pulni ko'rsatadi.",
                parameters=_schema({}, []),
            ),
            types.FunctionDeclaration(
                name="menyu_saqla",
                description="Tuzilgan haftalik taomlar menyusini saqlaydi va egasiga yuboradi.",
                parameters=_schema({"menyu": ("STRING", "To'liq menyu matni")}, ["menyu"]),
            ),
            types.FunctionDeclaration(
                name="royxat_saqla",
                description="Bozor ro'yxatini (miqdor va taxminiy narx bilan) saqlaydi va egasiga yuboradi.",
                parameters=_schema({"royxat": ("STRING", "To'liq ro'yxat matni")}, ["royxat"]),
            ),
            types.FunctionDeclaration(
                name="egamga_xabar",
                description="Egasiga (o'g'liga/qiziga) muhim xabarni yetkazadi.",
                parameters=_schema({"matn": ("STRING", "Xabar matni")}, ["matn"]),
            ),
        ]
    )
]


def fmt(n: int) -> str:
    return f"{n:,}".replace(",", " ") + " so'm"


def budget_status() -> str:
    b = storage.get("budget")
    rows = storage.expenses_since(b["start"] if b else time.time() - 7 * 86400)
    spent = sum(r["amount"] for r in rows)
    if b:
        lines = [f"Budjet: {fmt(b['amount'])} ({b['days']} kunga)", f"Sarflandi: {fmt(spent)}",
                 f"Qoldi: {fmt(b['amount'] - spent)}"]
    else:
        lines = ["Budjet hali belgilanmagan (summani so'ra).", f"Oxirgi 7 kunda sarflandi: {fmt(spent)}"]
    if rows:
        lines.append("Xarajatlar:")
        lines += [f"• {r['note']} — {fmt(r['amount'])}" for r in rows]
    return "\n".join(lines)


async def run_tool(name: str, args: dict, user_id: int, who: str, notify) -> str:
    """notify(text) — egasiga xabar yuboradigan korutina."""
    if name == "budjet_belgila":
        amount, days = int(args.get("summa", 0)), int(args.get("kun") or 7)
        storage.put("budget", {"amount": amount, "days": days, "start": time.time()})
        await notify(f"💰 {who.capitalize()} bozor budjetini belgiladi: {fmt(amount)}, {days} kunga.")
        return f"Saqlandi: {fmt(amount)}, {days} kunga."
    if name == "xarajat_yoz":
        amount = int(args.get("summa", 0))
        storage.add_expense(user_id, amount, str(args.get("nima", "")))
        return budget_status()
    if name == "budjet_holati":
        return budget_status()
    if name == "menyu_saqla":
        storage.put("menu", {"text": args.get("menyu", ""), "ts": time.time()})
        await notify(f"🍲 Haftalik menyu ({who}):\n\n{args.get('menyu', '')}")
        return "Menyu saqlandi va egasiga yuborildi."
    if name == "royxat_saqla":
        storage.put("shopping", {"text": args.get("royxat", ""), "ts": time.time()})
        await notify(f"🛒 Bozor ro'yxati ({who}):\n\n{args.get('royxat', '')}")
        return "Ro'yxat saqlandi va egasiga yuborildi."
    if name == "egamga_xabar":
        await notify(f"📨 {who.capitalize()}dan xabar: {args.get('matn', '')}")
        return "Yetkazildi."
    return "Noma'lum asbob."
