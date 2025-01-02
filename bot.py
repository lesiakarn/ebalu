import asyncio
import asyncpg
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command

# Токен вашого бота
API_TOKEN = "5207732731:AAFXqa0bgsYyHXQnNt5MrrQVZA0kO1APt4I"

# Налаштування бази даних
DB_HOST = "localhost"
DB_USER = "your_user"
DB_PASSWORD = "your_password"
DB_NAME = "your_database"

# Ініціалізація бота і диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Пул підключень до бази даних
db_pool = None


async def init_db():
    """Ініціалізація підключення до бази даних."""
    global db_pool
    db_pool = await asyncpg.create_pool(
        host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME
    )
    await create_tables()


async def create_tables():
    """Створення необхідних таблиць."""
    async with db_pool.acquire() as conn:
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            user_id BIGINT UNIQUE NOT NULL,
            username TEXT NOT NULL,
            points INT DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS admins (
            id SERIAL PRIMARY KEY,
            user_id BIGINT UNIQUE NOT NULL
        );
        """)


async def is_admin(user_id):
    """Перевірка, чи є користувач адміністратором."""
    async with db_pool.acquire() as conn:
        result = await conn.fetchval("SELECT EXISTS(SELECT 1 FROM admins WHERE user_id = $1)", user_id)
        return result


async def add_admin(user_id):
    """Додавання адміністратора."""
    async with db_pool.acquire() as conn:
        await conn.execute("INSERT INTO admins (user_id) VALUES ($1) ON CONFLICT DO NOTHING", user_id)


async def remove_admin(user_id):
    """Видалення адміністратора."""
    async with db_pool.acquire() as conn:
        await conn.execute("DELETE FROM admins WHERE user_id = $1", user_id)


async def register_user(user_id, username):
    """Реєстрація нового користувача."""
    async with db_pool.acquire() as conn:
        await conn.execute("""
        INSERT INTO users (user_id, username) 
        VALUES ($1, $2) 
        ON CONFLICT (user_id) DO NOTHING
        """, user_id, username)


async def update_points(user_id, points):
    """Оновлення балів користувача."""
    async with db_pool.acquire() as conn:
        await conn.execute("UPDATE users SET points = points + $1 WHERE user_id = $2", points, user_id)


async def get_user_points(user_id):
    """Отримання балів користувача."""
    async with db_pool.acquire() as conn:
        return await conn.fetchval("SELECT points FROM users WHERE user_id = $1", user_id)


async def get_admins():
    """Отримання списку адміністраторів."""
    async with db_pool.acquire() as conn:
        return await conn.fetch("SELECT user_id FROM admins")


# Команди
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
        user_id = await conn.fetchval("SELECT user_id FROM users WHERE username = $1", username)

    if not user_id:
        await message.answer(f"👤 Користувача @{username} не знайдено.")
        return

    await add_admin(user_id)
    await message.answer(f"✅ Користувач @{username} доданий до списку адміністраторів.")


@dp.message(Command("un"))
async def remove_admin_command(message: Message):
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас немає прав для цієї команди.")
        return

    args = message.text.split()
    if len(args) != 2:
        await message.answer("⚠️ Невірний формат команди. Використовуйте: /un @username")
        return

    username = args[1].lstrip('@')
    async with db_pool.acquire() as conn:
        user_id = await conn.fetchval("SELECT user_id FROM users WHERE username = $1", username)

    if not user_id:
        await message.answer(f"👤 Користувача @{username} не знайдено.")
        return

    await remove_admin(user_id)
    await message.answer(f"❌ Користувач @{username} видалений зі списку адміністраторів.")


@dp.message(Command("rating"))
async def show_rating(message: Message):
    async with db_pool.acquire() as conn:
        users = await conn.fetch("SELECT username, points FROM users ORDER BY points DESC")

    if not users:
        await message.answer("📉 Рейтинг порожній.")
        return

    rating = "\n".join([f"@{user['username']}: {user['points']} балів" for user in users])
    await message.answer(f"🏆 Рейтинг користувачів:\n{rating}")


@dp.message(Command("balance"))
async def show_balance(message: Message):
    points = await get_user_points(message.from_user.id)
    if points is None:
        await message.answer("⚠️ Ви ще не зареєстровані в системі.")
        return

    await message.answer(f"💰 Ваш баланс: {points} балів.")


@dp.message()
async def auto_register_user(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username
    if username:
        await register_user(user_id, username)


async def main():
    print("Бот запущено...")
    await init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
