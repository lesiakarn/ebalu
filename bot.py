import asyncio
import os
import asyncpg
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command

# Токен вашого бота
API_TOKEN = "5207732731:AAFXqa0bgsYyHXQnNt5MrrQVZA0kO1APt4I"

# Ініціалізація бота і диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Функція для підключення до PostgreSQL
async def connect_to_db():
    db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:WRzOlUWnceycOewJnJOPBHHcKloNoyBQ@roundhouse.proxy.rlwy.net:21272/railway')
    conn = await asyncpg.connect(db_url)
    return conn

# Ініціалізація бази даних
async def init_db():
    conn = await connect_to_db()
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            user_id BIGINT UNIQUE NOT NULL,
            username TEXT,
            points INT DEFAULT 0
        );
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id SERIAL PRIMARY KEY,
            user_id BIGINT UNIQUE NOT NULL
        );
    """)
    await conn.close()

# Додаємо користувача
async def add_user(user_id, username):
    conn = await connect_to_db()
    await conn.execute("""
        INSERT INTO users (user_id, username) VALUES ($1, $2)
        ON CONFLICT (user_id) DO NOTHING;
    """, user_id, username)
    await conn.close()

# Додаємо адміністратора
async def add_admin(user_id):
    conn = await connect_to_db()
    await conn.execute("""
        INSERT INTO admins (user_id) VALUES ($1)
        ON CONFLICT (user_id) DO NOTHING;
    """, user_id)
    await conn.close()

# Перевірка, чи є користувач адміністратором
async def is_admin(user_id):
    conn = await connect_to_db()
    result = await conn.fetchval("""
        SELECT EXISTS(SELECT 1 FROM admins WHERE user_id = $1);
    """, user_id)
    await conn.close()
    return result

# Команди
@dp.message(Command("start"))
async def start_command(message: Message):
    await add_user(message.from_user.id, message.from_user.username)
    await message.answer("👋 Привіт! Ви зареєстровані в системі.")

@dp.message(Command("ad"))
async def add_admin_command(message: Message):
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас немає прав для цієї команди.")
        return

    args = message.text.split()
    if len(args) != 2:
        await message.answer("⚠️ Використовуйте: /ad @username")
        return

    username = args[1].lstrip("@")
    conn = await connect_to_db()
    user_id = await conn.fetchval("""
        SELECT user_id FROM users WHERE username = $1;
    """, username)
    await conn.close()

    if not user_id:
        await message.answer(f"👤 Користувача @{username} не знайдено.")
        return

    await add_admin(user_id)
    await message.answer(f"✅ @{username} доданий до адміністраторів.")

@dp.message(Command("admins"))
async def list_admins(message: Message):
    conn = await connect_to_db()
    rows = await conn.fetch("""
        SELECT username FROM users
        WHERE user_id IN (SELECT user_id FROM admins);
    """)
    await conn.close()

    if not rows:
        await message.answer("👑 Список адміністраторів порожній.")
        return

    admin_list = "\n".join(f"@{row['username']}" for row in rows)
    await message.answer(f"👑 Список адміністраторів:\n{admin_list}")

async def main():
    print("Запуск бота...")
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
