from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from config import ADMIN_ID
import aiosqlite, os, ast
from database import add_lesson, add_task, add_final_answer
from utils.keyboards import user_ready_kb

admin_router = Router()

# --- ADMIN PANEL START ---
@admin_router.message(Command(commands=['start', 'admin']), F.from_user.id == ADMIN_ID)
async def admin_start(message: Message):
    await message.answer('Admin panelga xush kelibsiz. /add_lesson, /add_task, /add_final, /users')

# --- ADD LESSON ---
@admin_router.message(Command(commands=['add_lesson']), F.from_user.id == ADMIN_ID)
async def cmd_add_lesson(message: Message):
    text = message.text.replace('/add_lesson', '').strip()
    if not text or '|' not in text:
        await message.answer('Iltimos: /add_lesson <day>|<title> va keyin fayl yuboring')
        return
    day, title = text.split('|', 1)
    tmp = {'action': 'add_lesson', 'day': int(day.strip()), 'title': title.strip()}
    open('admin_tmp.json', 'w', encoding='utf-8').write(str(tmp))
    await message.answer(f'Dars uchun tayyor. Endi dars faylini yuboring.\nDay={day.strip()}, Title={title.strip()}')

# --- ADD TASK ---
@admin_router.message(Command(commands=['add_task']), F.from_user.id == ADMIN_ID)
async def cmd_add_task(message: Message):
    text = message.text.replace('/add_task', '').strip()
    if not text or '|' not in text:
        await message.answer('Iltimos: /add_task <day>|<description> va keyin fayl yuboring (yoki text)')
        return
    day, desc = text.split('|', 1)
    tmp = {'action': 'add_task', 'day': int(day.strip()), 'desc': desc.strip()}
    open('admin_tmp.json', 'w', encoding='utf-8').write(str(tmp))
    await message.answer('Endi topshiriq faylini yoki matnini yuboring.')

# --- ADD FINAL ANSWERS ---
@admin_router.message(Command(commands=['add_final']), F.from_user.id == ADMIN_ID)
async def cmd_add_final(message: Message):
    text = message.text.replace('/add_final', '').strip()
    if not text:
        await message.answer(
            "Iltimos: /add_final javoblarni yuboring textda.\n"
            "Har qator shu formatda bo‘lsin:\n\n"
            "1|Savol matni|A varianti|B varianti|C varianti|A"
        )
        return

    lines = text.splitlines()
    saved = 0

    async with aiosqlite.connect('bot.db') as db:
        for line in lines:
            parts = line.split('|')
            if len(parts) != 6:
                await message.answer(f"⚠️ Noto‘g‘ri format: {line}")
                continue

            qnum, qtext, a, b, c, correct = [p.strip() for p in parts]
            await add_final_answer(db, int(qnum), qtext, a, b, c, correct.upper())
            saved += 1

        await message.answer(f"✅ {saved} ta yakuniy savollar saqlandi.")

# --- RECEIVE FILES ---
@admin_router.message(F.content_type.in_({'photo', 'video', 'document', 'voice', 'audio'}), F.from_user.id == ADMIN_ID)
async def admin_recv_file(message: Message):
    if not os.path.exists('admin_tmp.json'):
        await message.answer('Hech qanday admin harakati topilmadi. /add_lesson yoki /add_task bilan boshlang.')
        return

    tmp = ast.literal_eval(open('admin_tmp.json', encoding='utf-8').read())
    file_type = message.content_type
    file_id = None

    if file_type == 'photo':
        file_id = message.photo[-1].file_id
    elif file_type == 'video':
        file_id = message.video.file_id
    elif file_type == 'document':
        file_id = message.document.file_id
    elif file_type in ('voice', 'audio'):
        file_id = message.voice.file_id if file_type == 'voice' else message.audio.file_id

    async with aiosqlite.connect('bot.db') as db:
        if tmp['action'] == 'add_lesson':
            await add_lesson(db, tmp['day'], tmp['title'], file_type, file_id)
            await message.answer('Dars yuklandi.')
        elif tmp['action'] == 'add_task':
            await add_task(db, tmp['day'], tmp['desc'], file_type, file_id)
            await message.answer('Topshiriq saqlandi.')

    os.remove('admin_tmp.json')

# --- LIST USERS ---
@admin_router.message(Command(commands=['users']), F.from_user.id == ADMIN_ID)
async def cmd_users(message: Message):
    async with aiosqlite.connect('bot.db') as db:
        cur = await db.execute("SELECT tg_id, first_name, last_name, phone, status FROM users")
        rows = await cur.fetchall()
        if not rows:
            await message.answer("Hozircha foydalanuvchilar yo'q.")
            return
        text = 'Foydalanuvchilar:\n' + '\n'.join([f"{r[0]} - {r[1]} {r[2]} - {r[3]} - {r[4]}" for r in rows])
        await message.answer(text)

# --- CLEAR FINAL ANSWERS ---
@admin_router.message(Command(commands=['clear_final']), F.from_user.id == ADMIN_ID)
async def clear_final_answers(message: Message):
    async with aiosqlite.connect('bot.db') as db:
        # Если хочешь удалить только последние 20, поставь это:
        await db.execute("""
            DELETE FROM final_answers
            WHERE id IN (
                SELECT id FROM final_answers
                ORDER BY id DESC
                LIMIT 20
            )
        """)
        # Если хочешь очищать ВСЕ, то замени строку выше на просто:
        # await db.execute("DELETE FROM final_answers")

        await db.commit()
        await message.answer("🧹 Последние 20 финальных ответов успешно удалены!")


# --- NOTIFY ADMIN ABOUT NEW USER ---
async def notify_admin_about_user(bot, user_id, first_name, last_name, phone):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Tasdiqlash ✅", callback_data=f"admin_accept_{user_id}"),
            InlineKeyboardButton(text="Rad etish ❌", callback_data=f"admin_reject_{user_id}")
        ]
    ])
    text = f"🆕 Yangi foydalanuvchi:\n\n👤 {first_name} {last_name}\n📞 {phone}\n\nTasdiqlaysizmi?"
    await bot.send_message(chat_id=ADMIN_ID, text=text, reply_markup=kb)

# --- ADMIN CONFIRM USER ---
@admin_router.callback_query(F.data.startswith("admin_accept_"))
async def approve_user(callback: CallbackQuery):
    print("✅ CALLBACK:", callback.data)
    await callback.answer()
    user_id = int(callback.data.split("_")[-1])
    async with aiosqlite.connect('bot.db') as db:
        await db.execute("UPDATE users SET status = 'approved' WHERE tg_id = ?", (user_id,))
        await db.commit()

    await callback.message.edit_text("✅ Foydalanuvchi tasdiqlandi!")

    try:
        await callback.bot.send_message(
            chat_id=user_id,
            text="✅ Sizning hisobingiz tasdiqlandi!\nDarslarni boshlash uchun 'Tayyorman' tugmasini bosing 👇",
            reply_markup=user_ready_kb()
        )
    except Exception as e:
        print(f"⚠️ Foydalanuvchiga xabar yuborilmadi: {e}")


@admin_router.callback_query(F.data.startswith("admin_reject_"))
async def reject_user(callback: CallbackQuery):
    print("❌ CALLBACK:", callback.data)
    await callback.answer()
    user_id = int(callback.data.split("_")[-1])
    async with aiosqlite.connect('bot.db') as db:
        await db.execute("UPDATE users SET status = 'rejected' WHERE tg_id = ?", (user_id,))
        await db.commit()

    await callback.message.edit_text("❌ Foydalanuvchi rad etildi.")
    try:
        await callback.bot.send_message(
            chat_id=user_id,
            text="❌ Afsus, sizning so'rovingiz rad etildi. Iltimos, admin bilan bog'laning."
        )
    except Exception as e:
        print(f"⚠️ Foydalanuvchiga xabar yuborilmadi: {e}")

