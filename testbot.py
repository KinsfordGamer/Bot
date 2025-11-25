import asyncio
from aiogram import Bot, Dispatcher, F, types
from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    Message, CallbackQuery
)
from aiogram.filters import Command

# ========================= CONFIG =========================
TOKEN = "Y8282203716:AAEXHUXopTojRn2G8mqS11eex1VEqWnz580"
KANAL_ID = -1002796484683          # Kanal ID
KANAL_OBUNACHI = -1003497782220     # Kanal Obunachi
KANAL_HAVOLASI = "https://t.me/Matematik_Zone"
ADMIN_ID = 6820003521               # Admin user ID
# ==========================================================

bot = Bot(TOKEN)
dp = Dispatcher()

user_data = {}       # Foydalanuvchi ma'lumotlari FSM uchun
all_users = set()    # Botdan foydalanganlar
admin_state = {}     # Admin broadcast holati


# ============= Helper: obuna tekshirish =============
async def check_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(KANAL_ID, user_id)
        return member.status in ("member", "administrator", "creator")
    except:
        return False


# ============= Helper: ro‘yxatdan o‘tganlar formati =============
def format_info(data: dict) -> str:
    return (
        f"📄 *Yangi ro‘yxatdan o‘tuvchi:*\n\n"
        f"1. 🏫 Ta’lim muassasasi: {data['school']}\n"
        f"2. 🎒 Sinf/Kurs: {data['class']}\n"
        f"3. 👤 F.I.Sh: {data['name']}\n"
        f"4. 📞 Telefon: {data['phone']}"
    )


# ==================== /start ====================
@dp.message(Command("start"))
async def start_cmd(msg: Message):
    all_users.add(msg.from_user.id)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="MATEMATIK ZONE 💪🏻", url=KANAL_HAVOLASI)],
        [InlineKeyboardButton(text="✅ Obuna bo‘ldim", callback_data="check_sub")]
    ])

    await msg.answer(
        "Assalomu aleykum 👋\n"
        "Olimpiadada qatnashish uchun avval kanalga a’zo bo‘ling 👇🏻",
        reply_markup=kb
    )


# ============= Obuna tekshirish =============
@dp.callback_query(F.data == "check_sub")
async def check_sub_cb(call: CallbackQuery):
    user_id = call.from_user.id

    if not await check_subscription(user_id):
        await call.answer("❌ Siz kanalga a'zo bo‘lmagansiz!", show_alert=True)
        return

    await call.message.delete()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✍🏻 Ro‘yxatdan o‘tish", callback_data="register")]
    ])

    await call.message.answer(
        "A'zo bo‘lish tasdiqlandi! 🎉\n"
        "Ro‘yxatdan o‘tish uchun tugmani bosing 👇🏻",
        reply_markup=kb
    )


# ============= Ro‘yxatdan o‘tishni boshlash =============
@dp.callback_query(F.data == "register")
async def register_start(call: CallbackQuery):
    user_id = call.from_user.id

    user_data[user_id] = {"step": "school"}

    await call.message.delete()
    await call.message.answer("🏫 Ta’lim muassasingizni kiriting:")
    await call.answer()


# ============= Admin panel /m_zone =============
@dp.message(Command("m_zone"))
async def admin_panel(msg: Message):
    if msg.from_user.id != ADMIN_ID:
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Statistikalar", callback_data="admin_stat")],
        [InlineKeyboardButton(text="📋 Ro‘yxatdan o‘tganlar", callback_data="admin_list")],
        [InlineKeyboardButton(text="📢 Xabar yuborish", callback_data="admin_broadcast")],
    ])

    await msg.answer("Admin paneliga xush kelibsiz 👇🏻", reply_markup=kb)


# ============= Admin statistika =============
@dp.callback_query(F.data == "admin_stat")
async def admin_stat(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return

    total = len(all_users)
    reg = len([u for u in user_data.values() if u.get("step") == "done"])

    await call.message.answer(
        f"📊 *Statistika:*\n\n"
        f"👥 Bot foydalanuvchilari: {total}\n"
        f"✅ Ro‘yxatdan o‘tganlar: {reg}",
        parse_mode="Markdown"
    )
    await call.answer()


# ============= Admin ro‘yxat =============
@dp.callback_query(F.data == "admin_list")
async def admin_list(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return

    text = "📋 *Ro‘yxatdan o‘tganlar:*\n\n"
    has = False

    for uid, data in user_data.items():
        if data.get("step") == "done":
            has = True
            text += (
                f"🏫 {data['school']}\n"
                f"🎒 {data['class']}\n"
                f"👤 {data['name']}\n"
                f"📞 {data['phone']}\n"
                "------------------------\n"
            )

    if not has:
        text = "❗ Hali birorta ham ishtirokchi ro‘yxatdan o‘tmagan."

    await call.message.answer(text)
    await call.answer()


# ============= Admin broadcast =============
@dp.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return

    admin_state[ADMIN_ID] = "broadcast"
    await call.message.answer("📢 Yuboriladigan xabar matnini kiriting:")
    await call.answer()


# ==================== FSM – Xabarlar ====================
@dp.message()
async def msg_handler(msg: Message):
    user_id = msg.from_user.id
    all_users.add(user_id)

    # ------- ADMIN BROADCAST -------
    if user_id == ADMIN_ID and admin_state.get(ADMIN_ID) == "broadcast":
        admin_state[ADMIN_ID] = None

        sent = 0
        for uid in all_users:
            try:
                await bot.send_message(uid, msg.text)
                sent += 1
            except:
                pass

        await msg.answer(f"📤 Xabar {sent} ta foydalanuvchiga yuborildi.")
        return

    # Agar foydalanuvchi ro‘yxatda bo‘lmasa → hech narsa qilinmaydi
    if user_id not in user_data:
        return

    step = user_data[user_id]["step"]

    # -------- 1) SCHOOL --------
    if step == "school":
        user_data[user_id]["school"] = msg.text
        user_data[user_id]["step"] = "class"
        await msg.answer("🎒 Sinf/Kursingizni kiriting:")
        return

    # -------- 2) CLASS --------
    if step == "class":
        user_data[user_id]["class"] = msg.text
        user_data[user_id]["step"] = "name"
        await msg.answer("👤 To‘liq ism-familiyangizni kiriting:")
        return

    # -------- 3) NAME --------
    if step == "name":
        user_data[user_id]["name"] = msg.text
        user_data[user_id]["step"] = "phone"

        kb = ReplyKeyboardMarkup(
            resize_keyboard=True,
            one_time_keyboard=True,
            keyboard=[
                [KeyboardButton(text="📱 Telefon raqamimni ulashish", request_contact=True)]
            ]
        )

        await msg.answer(
            "📞 Pastdagi tugma orqali telefon raqamingizni yuboring:",
            reply_markup=kb
        )
        return

    # -------- 4) PHONE --------
    if step == "phone":
        if not msg.contact:
            await msg.answer("❌ Iltimos, tugma orqali telefon raqamingizni yuboring!")
            return

        user_data[user_id]["phone"] = msg.contact.phone_number
        user_data[user_id]["step"] = "done"

        await msg.answer(
            "✅ Tabriklaymiz! Siz muvaffaqiyatli ro‘yxatdan o‘tdingiz!",
            reply_markup=ReplyKeyboardRemove()
        )

        info = format_info(user_data[user_id])

        # Admin ga yuboriladi
        await bot.send_message(ADMIN_ID, info, parse_mode="Markdown")

        # Kanalga yuboriladi
        await bot.send_message(KANAL_OBUNACHI, info, parse_mode="Markdown")

        return


# ==================== RUN ====================
async def main():
    print("Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
