import os
import asyncio
import asyncpg
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
from dotenv import load_dotenv

# Завантаження змінних оточення
load_dotenv()

API_TOKEN = os.getenv("5207732731:AAFXqa0bgsYyHXQnNt5MrrQVZA0kO1APt4I")
DATABASE_URL = os.getenv("postgresql://postgres:GbiDFCpQQvWbQGxjNrrzxOkVsNzdinhx@viaduct.proxy.rlwy.net:23347/railway")

# Ініціалізація бота і диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Глобальний пул підключень
db_pool = None

# Ініціалізація пулу підключень до бази даних
async def init_db_pool():
    global db_pool
    db_pool = await asyncpg.create_pool(DATABASE_URL)

# Ініціалізація бази даних
async def init_db():
    async with db_pool.acquire() as conn:
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

# Додаємо користувача
async def add_user(user_id, username):
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO users (user_id, username) VALUES ($1, $2)
            ON CONFLICT (user_id) DO NOTHING;
        """, user_id, username)

# Додаємо адміністратора
async def add_admin(user_id):
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO admins (user_id) VALUES ($1)
            ON CONFLICT (user_id) DO NOTHING;
        """)

# Перевірка, чи є користувач адміністратором
async def is_admin(user_id):
    async with db_pool.acquire() as conn:
        result = await conn.fetchval("""
            SELECT EXISTS(SELECT 1 FROM admins WHERE user_id = $1);
        """, user_id)
    return result

# Автоматична реєстрація користувача
@dp.message()
async def auto_register_user(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "Anonymous"

    async with db_pool.acquire() as conn:
        user_exists = await conn.fetchval("""
            SELECT EXISTS(SELECT 1 FROM users WHERE user_id = $1);
        """, user_id)

    if not user_exists:
        await add_user(user_id, username)
        await message.answer("🎉 Ви були автоматично зареєстровані!")

# Команда /start
@dp.message(Command("start"))
async def start_command(message: Message):
    await message.answer("👋 Вітаю! Це Telegram бот з рейтингами та адміністративними функціями!")

# Команда /ad - додавання адміністратора
@dp.message(Command("ad"))
async def add_admin_command(message: Message):
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас немає прав для цієї команди.")
        return

    args = message.text.split()
    if len(args) != 2:
        await message.answer("⚠️ Невірний формат команди. Використовуйте: /ad @username")
        return

    username = args[1].lstrip('@')
    async with db_pool.acquire() as conn:
        user_id = await conn.fetchval("""
            SELECT user_id FROM users WHERE username = $1;
        """, username)

    if not user_id:
        await message.answer(f"👤 Користувача @{username} не знайдено.")
        return

    await add_admin(user_id)
    await message.answer(f"✅ @{username} доданий до адміністраторів.")

# Команда /rating - показ рейтингу
@dp.message(Command("rating"))
async def show_rating(message: Message):
    async with db_pool.acquire() as conn:
        users = await conn.fetch("""
            SELECT username, points FROM users ORDER BY points DESC;
        """)

    if not users:
        await message.answer("📉 Рейтинг порожній.")
        return

    rating = "\n".join([f"@{user['username']}: {user['points']} балів" for user in users])
    await message.answer(f"🏆 Рейтинг користувачів:\n{rating}")

# Команда /balance - показ балансу
@dp.message(Command("balance"))
async def show_balance(message: Message):
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        user = await conn.fetchrow("""
            SELECT username, points FROM users WHERE user_id = $1;
        """, user_id)

    if user:
        await message.answer(f"💰 Ваш баланс: {user['points']} балів.")
    else:
        await message.answer("⚠️ Ви ще не зареєстровані.")

# Основна функція
async def main():
    print("Бот запущено...")
    await init_db_pool()  # Ініціалізація пулу підключень
    await init_db()  # Ініціалізація бази даних
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
