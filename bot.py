import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
import asyncpg

# Токен вашого бота
API_TOKEN = "YOUR_BOT_TOKEN"

# Ініціалізація бота і диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Параметри підключення до бази даних
DB_HOST = "localhost"
DB_USER = "your_user"
DB_PASSWORD = "your_password"
DB_NAME = "your_database"

# Функції для взаємодії з базою даних
async def init_db():
    return await asyncpg.create_pool(
        host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME
    )

async def is_admin(pool, user_id):
    async with pool.acquire() as conn:
        return await conn.fetchval("SELECT EXISTS(SELECT 1 FROM admins WHERE user_id=$1)", user_id)

async def add_admin(pool, user_id):
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO admins (user_id) VALUES ($1) ON CONFLICT DO NOTHING", user_id)

async def remove_admin(pool, user_id):
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM admins WHERE user_id=$1", user_id)

async def get_admins(pool):
    async with pool.acquire() as conn:
        return await conn.fetch("SELECT user_id FROM admins")

async def is_user_registered(pool, user_id):
    async with pool.acquire() as conn:
        return await conn.fetchval("SELECT EXISTS(SELECT 1 FROM users WHERE user_id=$1)", user_id)

async def register_user(pool, user_id, username):
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO users (user_id, username) VALUES ($1, $2) ON CONFLICT (user_id) DO NOTHING",
            user_id, username
        )

async def update_points(pool, user_id, points):
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET points = points + $1 WHERE user_id=$2", points, user_id
        )

async def get_points(pool, user_id):
    async with pool.acquire() as conn:
        return await conn.fetchval("SELECT points FROM users WHERE user_id=$1", user_id)

async def get_users(pool):
    async with pool.acquire() as conn:
        return await conn.fetch("SELECT username, points FROM users ORDER BY points DESC")

# Команди
@dp.message(Command("ad"))
async def add_admin_command(message: Message, pool):
    if not await is_admin(pool, message.from_user.id):
        await message.answer("❌ У вас немає прав для цієї команди.")
        return

    args = message.text.split()
    if len(args) != 2:
        await message.answer("⚠️ Використовуйте: /ad @username")
        return

    username = args[1].lstrip('@')
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT user_id FROM users WHERE username=$1", username)
    if not user:
        await message.answer(f"👤 Користувача @{username} не знайдено.")
        return

    await add_admin(pool, user["user_id"])
    await message.answer(f"✅ @{username} додано до адміністраторів.")

@dp.message(Command("un"))
async def remove_admin_command(message: Message, pool):
    if not await is_admin(pool, message.from_user.id):
        await message.answer("❌ У вас немає прав для цієї команди.")
        return

    args = message.text.split()
    if len(args) != 2:
        await message.answer("⚠️ Використовуйте: /un @username")
        return

    username = args[1].lstrip('@')
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT user_id FROM users WHERE username=$1", username)
    if not user:
        await message.answer(f"👤 Користувача @{username} не знайдено.")
        return

    await remove_admin(pool, user["user_id"])
    await message.answer(f"❌ @{username} видалено з адміністраторів.")

@dp.message(Command("rating"))
async def show_rating_command(message: Message, pool):
    users = await get_users(pool)
    if not users:
        await message.answer("📉 Рейтинг порожній.")
        return

    rating = "\n".join([f"@{user['username']}: {user['points']} балів" for user in users])
    await message.answer(f"🏆 Рейтинг користувачів:\n{rating}")

@dp.message(Command("balance"))
async def show_balance_command(message: Message, pool):
    user_id = message.from_user.id
    points = await get_points(pool, user_id)
    if points is None:
        await message.answer("⚠️ Ви не зареєстровані.")
        return

    await message.answer(f"💰 Ваш баланс: {points} балів.")

# Автоматична реєстрація користувачів
@dp.message()
async def auto_register_user(message: Message, pool):
    user_id = message.from_user.id
    username = message.from_user.username
    if username:
        await register_user(pool, user_id, username)

# Головна функція
async def main():
    pool = await init_db()
    dp.update.middleware(lambda _, h: h(pool=pool))
    print("Бот запущено...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
