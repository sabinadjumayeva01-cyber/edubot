import aiosqlite
import asyncio
from config import DB_PATH


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Таблица пользователей
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id INTEGER UNIQUE,
            first_name TEXT,
            last_name TEXT,
            phone TEXT,
            status TEXT DEFAULT 'pending',
            current_day INTEGER DEFAULT 0
        )
        """)

        # Таблица уроков
        await db.execute("""
        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day INTEGER,
            title TEXT,
            file_type TEXT,
            file_id TEXT
        )
        """)

        # Таблица заданий
        await db.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day INTEGER,
            description TEXT,
            file_type TEXT,
            file_id TEXT
        )
        """)

        # Таблица отправленных ответов пользователей
        await db.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            day INTEGER,
            content_type TEXT,
            file_id TEXT,
            text TEXT,
            status TEXT DEFAULT 'waiting'
        )
        """)

        # Таблица финальных тестов
        await db.execute("""
        CREATE TABLE IF NOT EXISTS final_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_number INTEGER,
            question_text TEXT,
            option_a TEXT,
            option_b TEXT,
            option_c TEXT,
            correct_option TEXT
        )
        """)

        # Таблица финальных результатов
        await db.execute("""
        CREATE TABLE IF NOT EXISTS final_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            score INTEGER
        )
        """)

        await db.commit()
        print("✅ База успешно создана!")


# ========== USERS ==========
async def add_user(db, tg_id, first_name, last_name, phone):
    await db.execute("""
        INSERT OR IGNORE INTO users (tg_id, first_name, last_name, phone)
        VALUES (?, ?, ?, ?)
    """, (tg_id, first_name, last_name, phone))
    await db.commit()

async def get_user_by_tg(db, tg_id):
    cur = await db.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,))
    return await cur.fetchone()

async def set_user_status(db, tg_id, status):
    await db.execute("UPDATE users SET status = ? WHERE tg_id = ?", (status, tg_id))
    await db.commit()

async def set_user_current_day(db, tg_id, day):
    await db.execute("UPDATE users SET current_day = ? WHERE tg_id = ?", (day, tg_id))
    await db.commit()


# ========== LESSONS ==========
async def add_lesson(db, day, title, file_type, file_id):
    # Проверяем, есть ли уже урок с таким днём
    cur = await db.execute("SELECT id FROM lessons WHERE day = ?", (day,))
    row = await cur.fetchone()

    if row:
        # Если урок есть — обновляем
        await db.execute("""
            UPDATE lessons
            SET title = ?, file_type = ?, file_id = ?
            WHERE day = ?
        """, (title, file_type, file_id, day))
    else:
        # Если нет — добавляем новый
        await db.execute("""
            INSERT INTO lessons (day, title, file_type, file_id)
            VALUES (?, ?, ?, ?)
        """, (day, title, file_type, file_id))

    await db.commit()


async def get_lesson(db, day):
    cur = await db.execute("SELECT * FROM lessons WHERE day = ?", (day,))
    return await cur.fetchone()


# ========== TASKS ==========
async def add_task(db, day, description, file_type, file_id):
    await db.execute("""
        INSERT INTO tasks (day, description, file_type, file_id)
        VALUES (?, ?, ?, ?)
    """, (day, description, file_type, file_id))
    await db.commit()

async def get_task(db, day):
    cur = await db.execute("SELECT * FROM tasks WHERE day = ?", (day,))
    return await cur.fetchone()


# ========== SUBMISSIONS ==========
async def add_submission(db, user_id, day, content_type, file_id, text):
    await db.execute("""
        INSERT INTO submissions (user_id, day, content_type, file_id, text)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, day, content_type, file_id, text))
    await db.commit()
    cur = await db.execute("SELECT last_insert_rowid()")
    return (await cur.fetchone())[0]

async def set_submission_status(db, submission_id, status):
    await db.execute("UPDATE submissions SET status = ? WHERE id = ?", (status, submission_id))
    await db.commit()


# ========== FINAL TEST ==========
async def add_final_answer(db, question_number, question_text, option_a, option_b, option_c, correct_option):
    await db.execute("""
        INSERT INTO final_answers (question_number, question_text, option_a, option_b, option_c, correct_option)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (question_number, question_text, option_a, option_b, option_c, correct_option))
    await db.commit()

async def get_all_final_answers(db):
    cur = await db.execute("""
        SELECT question_number, question_text, option_a, option_b, option_c, correct_option
        FROM final_answers
        ORDER BY question_number
    """)
    return await cur.fetchall()


# ========== FINAL RESULTS ==========
async def add_final_result(db, user_id, score):
    await db.execute("INSERT INTO final_results (user_id, score) VALUES (?, ?)", (user_id, score))
    await db.commit()


# ========== INIT ==========
if __name__ == "__main__":
    asyncio.run(init_db())
