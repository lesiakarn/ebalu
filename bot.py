import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
import asyncpg

# Токен вашого бота
API_TOKEN = "7867439762:AAG_ZLt6Jamj89ju8FpYb9DqRRlGfzXNi5Y"

# URL підключення до PostgreSQL
DATABASE_URL = "postgresql://postgres:GbiDFCpQQvWbQGxjNrrzxOkVsNzdinhx@viaduct.proxy.rlwy.net:23347/railway"

# Ініціалізація бота і диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Підключення до бази даних
async def init_db():
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            username TEXT,
            points INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS administrators (
            user_id BIGINT PRIMARY KEY
        );
    ''')
    await conn.close()

# Функції для роботи з базою даних
async def is_admin(user_id):
    conn = await asyncpg.connect(DATABASE_URL)
    result = await conn.fetchval("SELECT EXISTS(SELECT 1 FROM administrators WHERE user_id = $1)", user_id)
    await conn.close()
    return result

async def is_user_in_group(user_id):
    conn = await asyncpg.connect(DATABASE_URL)
    result = await conn.fetchval("SELECT EXISTS(SELECT 1 FROM users WHERE user_id = $1)", user_id)
    await conn.close()
    return result

async def register_user(user_id, username):
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute(
        "INSERT INTO users (user_id, username) VALUES ($1, $2) ON CONFLICT (user_id) DO NOTHING",
        user_id, username
    )
    await conn.close()

async def get_user_id_by_username(username):
    conn = await asyncpg.connect(DATABASE_URL)
    user_id = await conn.fetchval("SELECT user_id FROM users WHERE username = $1", username)
    await conn.close()
    return user_id

async def add_admin(user_id):
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("INSERT INTO administrators (user_id) VALUES ($1) ON CONFLICT DO NOTHING", user_id)
    await conn.close()

async def remove_admin(user_id):
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("DELETE FROM administrators WHERE user_id = $1", user_id)
    await conn.close()

async def get_admins():
    conn = await asyncpg.connect(DATABASE_URL)
    rows = await conn.fetch("SELECT user_id FROM administrators")
    await conn.close()
    return [row["user_id"] for row in rows]

async def update_points(user_id, points):
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("UPDATE users SET points = points + $1 WHERE user_id = $2", points, user_id)
    await conn.close()

async def get_users():
    conn = await asyncpg.connect(DATABASE_URL)
    rows = await conn.fetch("SELECT username, points FROM users ORDER BY points DESC")
    await conn.close()
    return rows

# Команди бота
@dp.message(Command("ad"))
async def handle_add_admin(message: Message):
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас немає прав для цієї команди.")
        return

    args = message.text.split()
    if len(args) != 2:
        await message.answer("⚠️ Невірний формат команди. Використовуйте: /ad @username")
        return

    username = args[1].lstrip('@')
    user_id = await get_user_id_by_username(username)

    if not user_id:
        await message.answer(f"👤 Користувача @{username} не знайдено.")
        return

    await add_admin(user_id)
    await message.answer(f"✅ Користувач @{username} доданий до списку адміністраторів.")

@dp.message(Command("un"))
async def handle_remove_admin(message: Message):
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас немає прав для цієї команди.")
        return

    args = message.text.split()
    if len(args) != 2:
        await message.answer("⚠️ Невірний формат команди. Використовуйте: /un @username")
        return

    username = args[1].lstrip('@')
    user_id = await get_user_id_by_username(username)

    if not user_id:
        await message.answer(f"👤 Користувача @{username} не знайдено.")
        return

    await remove_admin(user_id)
    await message.answer(f"❌ Користувач @{username} видалений зі списку адміністраторів.")

@dp.message(Command("admins"))
async def handle_list_admins(message: Message):
    admin_ids = await get_admins()
    if not admin_ids:
        await message.answer("📜 Список адміністраторів порожній.")
        return

    admin_usernames = []
    for admin_id in admin_ids:
        conn = await asyncpg.connect(DATABASE_URL)
        username = await conn.fetchval("SELECT username FROM users WHERE user_id = $1", admin_id)
        await conn.close()
        if username:
            admin_usernames.append(f"@{username}")

    admin_list = "\n".join(admin_usernames)
    await message.answer(f"👑 Список адміністраторів:\n{admin_list}")

@dp.message(Command("rating"))
async def handle_show_rating(message: Message):
    users = await get_users()
    if not users:
        await message.answer("📉 Рейтинг порожній.")
        return

    rating = "\n".join([f"@{row['username']}: {row['points']} балів" for row in users])
    await message.answer(f"🏆 Рейтинг користувачів:\n{rating}")

@dp.message(Command("give"))
async def handle_give_points(message: Message):
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас немає прав для цієї команди.")
        return

    args = message.text.split()
    if len(args) != 3:
        await message.answer("⚠️ Невірний формат команди. Використовуйте: /give @username <кількість>")
        return

    username, points = args[1].lstrip('@'), int(args[2])
    user_id = await get_user_id_by_username(username)

    if not user_id:
        await message.answer(f"👤 Користувача @{username} не знайдено.")
        return

    await update_points(user_id, points)
    await message.answer(f"✅ Додано {points} балів для @{username}.")
    await bot.send_message(user_id, f"🎉 Вам додано {points} балів.")

@dp.message(Command("take"))
async def handle_take_points(message: Message):
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас немає прав для цієї команди.")
        return

    args = message.text.split()
    if len(args) != 3:
        await message.answer("⚠️ Невірний формат команди. Використовуйте: /take @username <кількість>")
        return

    username, points = args[1].lstrip('@'), int(args[2])
    user_id = await get_user_id_by_username(username)

    if not user_id:
        await message.answer(f"👤 Користувача @{username} не знайдено.")
        return

    await update_points(user_id, -points)
    await message.answer(f"❌ Знято {points} балів у @{username}.")
    await bot.send_message(user_id, f"⚠️ У вас знято {points} балів.")

@dp.message()
async def auto_register_user(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username

    if username and not await is_user_in_group(user_id):
        await register_user(user_id, username)

async def main():
    print("Бот запущено...")
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
