import asyncio
import os
import asyncpg
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
import json

# Токен вашого бота
API_TOKEN = "5207732731:AAFXqa0bgsYyHXQnNt5MrrQVZA0kO1APt4I"

# Ініціалізація бота і диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Параметри підключення до PostgreSQL
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:GbiDFCpQQvWbQGxjNrrzxOkVsNzdinhx@viaduct.proxy.rlwy.net:23347/railway')

# Підключення до PostgreSQL
async def connect_to_db():
    conn = await asyncpg.connect(DATABASE_URL)
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

# Перевірка, чи є користувач в системі
async def is_user_in_system(user_id):
    conn = await connect_to_db()
    result = await conn.fetchval("""
        SELECT EXISTS(SELECT 1 FROM users WHERE user_id = $1);
    """, user_id)
    await conn.close()
    return result

# Отримуємо список користувачів
async def get_users():
    conn = await connect_to_db()
    users = await conn.fetch("SELECT user_id, username, points FROM users")
    await conn.close()
    return users

# Команди бота
@dp.message(Command("start"))
async def start_command(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username

    if not await is_user_in_system(user_id):
        await add_user(user_id, username)

    await message.answer("👋 Привіт! Ви зареєстровані в системі.")

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
    conn = await connect_to_db()
    user_id = await conn.fetchval("""
        SELECT user_id FROM users WHERE username = $1;
    """, username)
    await conn.close()

    if not user_id:
        await message.answer(f"👤 Користувача @{username} не знайдено.")
        return

    conn = await connect_to_db()
    await conn.execute("""
        DELETE FROM admins WHERE user_id = $1;
    """, user_id)
    await conn.close()
    
    await message.answer(f"❌ @{username} видалений зі списку адміністраторів.")

@dp.message(Command("rating"))
async def show_rating(message: Message):
    users = await get_users()
    sorted_users = sorted(users, key=lambda x: x['points'], reverse=True)
    rating = "\n".join([f"@{user['username']}: {user['points']} балів" for user in sorted_users])
    await message.answer(f"🏆 Рейтинг користувачів:\n{rating}")

@dp.message(Command("give"))
async def give_points(message: Message):
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас немає прав для цієї команди.")
        return

    args = message.text.split()
    if len(args) != 3:
        await message.answer("⚠️ Невірний формат команди. Використовуйте: /give @username <кількість>")
        return

    username, points = args[1].lstrip('@'), int(args[2])
    conn = await connect_to_db()
    user_id = await conn.fetchval("""
        SELECT user_id FROM users WHERE username = $1;
    """, username)
    await conn.close()

    if not user_id:
        await message.answer(f"👤 Користувача @{username} не знайдено.")
        return

    conn = await connect_to_db()
    await conn.execute("""
        UPDATE users SET points = points + $1 WHERE user_id = $2;
    """, points, user_id)
    await conn.close()

    await message.answer(f"✅ Додано {points} балів для @{username}.")
    await bot.send_message(user_id, f"🎉 Вам додано {points} балів.")

@dp.message(Command("take"))
async def take_points(message: Message):
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас немає прав для цієї команди.")
        return

    args = message.text.split()
    if len(args) != 3:
        await message.answer("⚠️ Невірний формат команди. Використовуйте: /take @username <кількість>")
        return

    username, points = args[1].lstrip('@'), int(args[2])
    conn = await connect_to_db()
    user_id = await conn.fetchval("""
        SELECT user_id FROM users WHERE username = $1;
    """, username)
    await conn.close()

    if not user_id:
        await message.answer(f"👤 Користувача @{username} не знайдено.")
        return

    conn = await connect_to_db()
    current_points = await conn.fetchval("""
        SELECT points FROM users WHERE user_id = $1;
    """, user_id)
    
    if points > current_points:
        points = current_points

    await conn.execute("""
        UPDATE users SET points = points - $1 WHERE user_id = $2;
    """, points, user_id)
    await conn.close()

    await message.answer(f"❌ Знято {points} балів у @{username}.")
    await bot.send_message(user_id, f"⚠️ У вас знято {points} балів.")

@dp.message(Command("balance"))
async def show_balance(message: Message):
    user_id = str(message.from_user.id)
    conn = await connect_to_db()

    if not await is_user_in_system(message.from_user.id):
        await message.answer("⚠️ Ви ще не зареєстровані в системі. Надішліть будь-яке повідомлення, щоб зареєструватися.")
        return

    user = await conn.fetchrow("""
        SELECT username, points FROM users WHERE user_id = $1;
    """, message.from_user.id)
    await conn.close()

    await message.answer(f"💰 Ваш баланс: {user['points']} балів.\nКористувач: @{user['username']}.")

# Автоматична реєстрація користувача
@dp.message()
async def auto_register_user(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username

    if not username:
        return

    if not await is_user_in_system(user_id):
        await add_user(user_id, username)

async def main():
    print("Бот запущено...")
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
