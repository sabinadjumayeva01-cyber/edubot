import os
import aiosqlite
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from database import (
    add_user, set_user_status, get_lesson, get_task,
    add_submission, set_submission_status,
    add_final_answer, get_all_final_answers, add_final_result
)
from config import ADMIN_ID
from utils.keyboards import user_ready_kb, finish_day_kb, task_submit_kb

user_router = Router()

# ===============================
# START — Регистрация
# ===============================
@user_router.message(Command("start"))
async def cmd_start(message: Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Siz admin sifatida tizimdasiz.")
        return
    await message.answer(
        "Assalomu alaykum! Iltimos ismingizni va familiyangizni yuboring (format: Ism Familiya).\nMasalan: Djumayeva Sabina"
    )

@user_router.message(lambda m: m.text and len(m.text.split()) >= 2)
async def name_received(message: Message):
    if message.from_user.id == ADMIN_ID:
        return  # Админ пропускает регистрацию
    parts = message.text.split()
    first = parts[0]
    last = " ".join(parts[1:])
    await message.answer("Iltimos, telefon raqamingizni yuboring (misol: +998901234567)")
    open(f"tmp_{message.from_user.id}.txt", "w", encoding="utf-8").write(f"{first}\n{last}")

@user_router.message(lambda m: m.text and m.text.startswith("+"))
async def phone_received(message: Message):
    if message.from_user.id == ADMIN_ID:
        return  # Админ не проходит регистрацию
    uid = message.from_user.id
    tmp_file = f"tmp_{uid}.txt"
    if not os.path.exists(tmp_file):
        await message.answer("Iltimos, avval ismingiz va familiyangizni yuboring.")
        return

    first, last = open(tmp_file, encoding="utf-8").read().splitlines()
    phone = message.text.strip()

    async with aiosqlite.connect("bot.db") as db:
        await add_user(db, uid, first, last, phone)

    await message.answer("Iltimos, hisobingiz tasdiqlanishini kuting!")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Tasdiqlash ✅", callback_data=f"admin_accept_{uid}"),
            InlineKeyboardButton(text="Rad etish ❌", callback_data=f"admin_reject_{uid}")
        ]
    ])
    await message.bot.send_message(
        ADMIN_ID,
        f"🆕 Yangi foydalanuvchi:\n\n👤 {first} {last}\n📞 {phone}\n🆔 {uid}",
        reply_markup=kb
    )
    os.remove(tmp_file)

# ===============================
# READY BUTTON — START LESSONS
# ===============================
@user_router.callback_query(F.data == "ready")
async def ready_to_start(cb: CallbackQuery):
    await cb.answer()
    uid = cb.from_user.id
    async with aiosqlite.connect("bot.db") as db:
        await set_user_status(db, uid, "in_progress")
        await db.execute("UPDATE users SET current_day = 1 WHERE tg_id = ?", (uid,))
        await db.commit()
        await send_lesson(cb.bot, uid, 1)

# ===============================
# Отправка урока
# ===============================
async def send_lesson(bot, uid: int, day: int):
    async with aiosqlite.connect("bot.db") as db:
        lesson = await get_lesson(db, day)
        if not lesson:
            await bot.send_message(uid, f"{day}-kun dars topilmadi. Admin bilan bog‘laning.")
            return

        file_type = lesson[3]
        file_id = lesson[4]

        await bot.send_message(uid, f"{day}-kun darsligi:")

        if file_type == "photo":
            await bot.send_photo(uid, file_id)
        elif file_type == "video":
            await bot.send_video(uid, file_id)
        elif file_type == "video_note":
            await bot.send_video_note(uid, file_id)
        elif file_type == "document":
            await bot.send_document(uid, file_id)
        else:
            await bot.send_message(uid, "Dars mavjud, ammo turini aniqlab bo‘lmadi.")

        await bot.send_message(uid, "Darsni tugatdingizmi?", reply_markup=finish_day_kb())

# ===============================
# Пользователь завершает урок
# ===============================
@user_router.callback_query(F.data == "finish_lesson")
async def finish_lesson(cb: CallbackQuery):
    await cb.answer()
    uid = cb.from_user.id
    await cb.bot.send_message(uid, "Tabriklaymiz! Endi topshiriqlarni bajaring 👇", reply_markup=task_submit_kb())

# ===============================
# TASKS — ПРИЕМ ЛЮБОГО ФОРМАТА
# ===============================
@user_router.callback_query(F.data == "do_task")
async def do_task(cb: CallbackQuery):
    await cb.answer()
    uid = cb.from_user.id
    async with aiosqlite.connect("bot.db") as db:
        cur = await db.execute("SELECT current_day FROM users WHERE tg_id = ?", (uid,))
        row = await cur.fetchone()
        if not row:
            await cb.bot.send_message(uid, "Foydalanuvchi topilmadi.")
            return

        day = row[0]
        task = await get_task(db, day)
        if not task:
            await cb.bot.send_message(uid, "Topshiriq topilmadi.")
            return

        await cb.bot.send_message(uid, "Quyidagi topshiriqni bajaring:")
        file_type = task[3]
        file_id = task[4]

        if file_type == "photo":
            await cb.bot.send_photo(uid, file_id)
        elif file_type == "video":
            await cb.bot.send_video(uid, file_id)
        elif file_type == "video_note":
            await cb.bot.send_video_note(uid, file_id)
        elif file_type == "document":
            await cb.bot.send_document(uid, file_id)
        else:
            await cb.bot.send_message(uid, task[2])

@user_router.callback_query(F.data == "submit_task")
async def submit_task(cb: CallbackQuery):
    await cb.answer()
    uid = cb.from_user.id
    open(f"submit_{uid}.txt", "w", encoding="utf-8").write("waiting")
    await cb.bot.send_message(uid, "Iltimos, javobingizni yuboring (matn, foto, video, video-sms, doc, audio, voice).")

# ===============================
# Пользователь отправляет задание
# ===============================
@user_router.message(F.content_type.in_({"text","photo","video","video_note","document","audio","voice"}))
async def catch_submission(message: Message):
    if message.from_user.id == ADMIN_ID:
        return  # Админ пропускает проверку
    uid = message.from_user.id
    async with aiosqlite.connect("bot.db") as db:
        cur = await db.execute("SELECT id, current_day FROM users WHERE tg_id = ?", (uid,))
        row = await cur.fetchone()
        if not row:
            await message.answer("Siz ro‘yxatdan o‘tmagansiz.")
            return
        user_id, current_day = row

        content_type = message.content_type
        file_id = None
        text = ""
        if content_type == "text":
            text = message.text
        elif content_type == "photo":
            file_id = message.photo[-1].file_id
        elif content_type == "video":
            file_id = message.video.file_id
        elif content_type == "video_note":
            file_id = message.video_note.file_id
        elif content_type == "document":
            file_id = message.document.file_id
        elif content_type == "voice":
            file_id = message.voice.file_id
        elif content_type == "audio":
            file_id = message.audio.file_id

        sub_id = await add_submission(db, user_id, current_day, content_type, file_id, text)
        await message.answer("✅ Javob qabul qilindi! Adminga yuborildi.")

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Tasdiqlash ✅", callback_data=f"confirm_{sub_id}"),
                InlineKeyboardButton(text="Rad etish ❌", callback_data=f"reject_{sub_id}")
            ]
        ])

        try:
            if content_type == "text":
                await message.bot.send_message(ADMIN_ID,
                    f"📝 Yangi topshiriq (ID={sub_id}) foydalanuvchi {uid} tomonidan yuborildi.\n\nJavob: {text}",
                    reply_markup=kb)
            elif content_type == "photo":
                await message.bot.send_photo(ADMIN_ID, file_id,
                    caption=f"📝 Yangi topshiriq (ID={sub_id}) foydalanuvchi {uid} tomonidan yuborildi.",
                    reply_markup=kb)
            elif content_type == "video":
                await message.bot.send_video(ADMIN_ID, file_id,
                    caption=f"📝 Yangi topshiriq (ID={sub_id}) foydalanuvchi {uid} tomonidan yuborildi.",
                    reply_markup=kb)
            elif content_type == "video_note":
                await message.bot.send_video_note(ADMIN_ID, file_id, reply_markup=kb)
            elif content_type == "document":
                await message.bot.send_document(ADMIN_ID, file_id,
                    caption=f"📝 Yangi topshiriq (ID={sub_id}) foydalanuvchi {uid} tomonidan yuborildi.",
                    reply_markup=kb)
            elif content_type == "voice":
                await message.bot.send_voice(ADMIN_ID, file_id,
                    caption=f"📝 Yangi topshiriq (ID={sub_id}) foydalanuvchi {uid} tomonidan yuborildi.",
                    reply_markup=kb)
            elif content_type == "audio":
                await message.bot.send_audio(ADMIN_ID, file_id,
                    caption=f"📝 Yangi topshiriq (ID={sub_id}) foydalanuvchi {uid} tomonidan yuborildi.",
                    reply_markup=kb)
        except Exception as e:
            await message.answer(f"⚠️ Xatolik yuborishda: {e}")

# ===============================
# ADMIN CONFIRM / REJECT TASK
# ===============================
@user_router.callback_query(F.data.startswith("confirm_"))
async def admin_confirm(cb: CallbackQuery):
    await cb.answer()
    sub_id = int(cb.data.split("_")[-1])
    async with aiosqlite.connect("bot.db") as db:
        await set_submission_status(db, sub_id, "approved")
        cur = await db.execute("SELECT user_id FROM submissions WHERE id = ?", (sub_id,))
        r = await cur.fetchone()
        if not r: return
        internal_user_id = r[0]

        cur2 = await db.execute("SELECT tg_id, current_day FROM users WHERE id = ?", (internal_user_id,))
        r2 = await cur2.fetchone()
        if not r2:
            await cb.message.answer("❌ Telegram ID foydalanuvchini topib bo‘lmadi.")
            return

        tg_id, current_day = r2

        if current_day < 6:
            next_day = current_day + 1
            await db.execute("UPDATE users SET current_day = ? WHERE id = ?", (next_day, internal_user_id))
            await db.commit()
            await cb.bot.send_message(tg_id, f"✅ Tabriklaymiz! Endi {next_day}-kun darsni boshlashingiz mumkin.")
            await send_lesson(cb.bot, tg_id, next_day)
        else:
            await cb.bot.send_message(
                tg_id,
                "✅ Tabriklaymiz! Siz barcha darslarni tugatdingiz. Endi oxirgi testni bajaring.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Testni boshlash", callback_data="start_final_test")]
                ])
            )

    await cb.message.answer("Topshiriq tasdiqlandi.")

@user_router.callback_query(F.data.startswith("reject_"))
async def admin_reject_submission(cb: CallbackQuery):
    await cb.answer()
    sub_id = int(cb.data.split("_")[-1])
    async with aiosqlite.connect("bot.db") as db:
        await set_submission_status(db, sub_id, "rejected")
        cur = await db.execute("SELECT user_id FROM submissions WHERE id = ?", (sub_id,))
        r = await cur.fetchone()
        if not r: return
        internal_user_id = r[0]

        cur2 = await db.execute("SELECT tg_id FROM users WHERE id = ?", (internal_user_id,))
        r2 = await cur2.fetchone()
        if not r2:
            await cb.message.answer("❌ Telegram ID foydalanuvchini topib bo‘lmadi.")
            return
        tg_id = r2[0]

        await cb.bot.send_message(
            tg_id,
            "❌ Topshiriq rad etildi. Iltimos, darsni qayta ko‘rib chiqing va qayta yuboring.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Topshiriqni qayta jo‘natish", callback_data="do_task")]
            ])
        )

    await cb.message.answer("Topshiriq rad etildi.")

# ===============================
# FINAL TEST LOGIC
# ===============================
@user_router.callback_query(F.data == "start_final_test")
async def start_final_test(cb: CallbackQuery):
    await cb.answer()
    uid = cb.from_user.id
    async with aiosqlite.connect("bot.db") as db:
        questions = await get_all_final_answers(db)
        if not questions:
            await cb.bot.send_message(uid, "Oxirgi test savollari hali mavjud emas. Admin bilan bog‘laning.")
            return
        open(f"final_test_{uid}.txt", "w", encoding="utf-8").write("0")
        open(f"final_score_{uid}.txt", "w", encoding="utf-8").write("0")
        await send_final_question(cb.bot, uid, 0, questions)

async def send_final_question(bot, uid, q_index, questions):
    if q_index >= len(questions):
        await calculate_final_score(bot, uid)
        return

    q = questions[q_index]
    question_number, question_text, option_a, option_b, option_c, correct_option = q

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=option_a, callback_data=f"final_{q_index}_A")],
        [InlineKeyboardButton(text=option_b, callback_data=f"final_{q_index}_B")],
        [InlineKeyboardButton(text=option_c, callback_data=f"final_{q_index}_C")]
    ])
    await bot.send_message(uid, f"{question_number}. {question_text}", reply_markup=kb)

@user_router.callback_query(F.data.startswith("final_"))
async def handle_final_answer(cb: CallbackQuery):
    await cb.answer()
    uid = cb.from_user.id
    parts = cb.data.split("_")
    q_index = int(parts[1])
    selected_option = parts[2]

    path = f"final_test_{uid}.txt"
    current_index = q_index + 1
    open(path, "w", encoding="utf-8").write(str(current_index))

    score_path = f"final_score_{uid}.txt"
    score = 0
    if os.path.exists(score_path):
        score = int(open(score_path).read())
    async with aiosqlite.connect("bot.db") as db:
        questions = await get_all_final_answers(db)
        correct_option = questions[q_index][5]
        if selected_option == correct_option:
            score += 5
    open(score_path, "w", encoding="utf-8").write(str(score))

    await send_final_question(cb.bot, uid, current_index, questions)

async def calculate_final_score(bot, uid):
    score_path = f"final_score_{uid}.txt"
    score = int(open(score_path).read()) if os.path.exists(score_path) else 0
    os.remove(f"final_test_{uid}.txt")
    os.remove(score_path)

    if score >= 70:
        await bot.send_message(uid, f"🎉 Tabriklaymiz! Sizning balingiz: {score}\nOxirgi testni muvaffaqiyatli yakunladingiz. Ushbu SMS ni @Aziza_Shokirovna ga yuboring va jamoamizga qo‘shiling.")
    else:
        await bot.send_message(uid, f"😔 Kechirasiz, sizning balingiz: {score}\nUshbu ko‘rsatkich 70 dan past. Iltimos, darslarni qayta boshlang va urinib ko‘ring.")

# ===============================
# ADMIN ADD FINAL QUESTION (SINGLE COMMAND)
# ===============================
@user_router.message(F.text & F.text.startswith("/add_question"))
async def add_question_single(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Siz admin emassiz.")
        return

    # Убираем команду и @username, если есть
    text = message.text
    if " " in text:
        text = text.split(" ", 1)[1].strip()
    else:
        await message.answer(
            "❌ Format noto‘g‘ri!\n"
            "To‘g‘ri format:\n"
            "/add_question номер/текст вопроса/вариант A/вариант B/вариант C/правильный вариант(A/B/C)"
        )
        return

    parts = [p.strip() for p in text.split("/")]
    if len(parts) != 6:
        await message.answer(
            "❌ Format noto‘g‘ri!\n"
            "To‘g‘ri format:\n"
            "/add_question номер/текст вопроса/вариант A/вариант B/вариант C/правильный вариант(A/B/C)"
        )
        return

    question_number, question_text, option_a, option_b, option_c, correct_option = parts
    correct_option = correct_option.upper()

    if correct_option not in ["A", "B", "C"]:
        await message.answer("❌ Правильный вариант noto‘g‘ri. Faqat A, B yoki C bo‘lishi kerak.")
        return

    async with aiosqlite.connect("bot.db") as db:
        await add_final_answer(db, question_text, option_a, option_b, option_c, correct_option)

    await message.answer(f"✅ Savol muvaffaqiyatli qo‘shildi! Nomeri: {question_number}")
