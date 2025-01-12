import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from datetime import datetime
import asyncpg

# Константи
API_TOKEN = "7867439762:AAG_ZLt6Jamj89ju8FpYb9DqRRlGfzXNi5Y"
ADMIN_ID = 1360055963  # Адміністраторський ID
MAX_POINTS = 1000
MAX_BALANCE = 1000
MIN_BALANCE = 0

DATABASE_URL = "postgresql://postgres:GbiDFCpQQvWbQGxjNrrzxOkVsNzdinhx@viaduct.proxy.rlwy.net:23347/railway"

# Ініціалізація бота і диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Клавіатури
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📜 Команди")],
        [KeyboardButton(text="🛒 Купити"), KeyboardButton(text="💰 Баланс")],
    ],
    resize_keyboard=True,
)
buy_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🛡 Старійшина"), KeyboardButton(text="⚔️ Підкріплення")],
        [KeyboardButton(text="🔙 Назад")],
    ],
    resize_keyboard=True,
)

# Ініціалізація бази даних
async def init_db():
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            username TEXT,
            balance INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS administrators (
            user_id BIGINT PRIMARY KEY,
            username TEXT
        );
    ''')
    await conn.close()
    print("База даних ініціалізована.")

# Отримати список усіх користувачів з бази даних
async def get_users():
    conn = await asyncpg.connect(DATABASE_URL)
    users = await conn.fetch("SELECT username, balance FROM users ORDER BY balance DESC")
    await conn.close()
    return users

# Отримати список адміністраторів
async def get_admins():
    conn = await asyncpg.connect(DATABASE_URL)
    admins = await conn.fetch("SELECT user_id FROM administrators")
    await conn.close()
    return admins

# Перевіряє, чи є користувач адміністратором
async def is_admin(user_id):
    conn = await asyncpg.connect(DATABASE_URL)
    is_admin = await conn.fetchval("SELECT user_id FROM administrators WHERE user_id = $1", user_id)
    await conn.close()
    return is_admin is not None

# Функції для роботи з базою даних
async def register_user(user_id, username):
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute(
        "INSERT INTO users (user_id, username) VALUES ($1, $2) ON CONFLICT (user_id) DO NOTHING",
        user_id, username
    )
    await conn.close()

async def get_user_balance(user_id):
    conn = await asyncpg.connect(DATABASE_URL)
    balance = await conn.fetchval("SELECT balance FROM users WHERE user_id = $1", user_id)
    await conn.close()
    return balance

async def update_user_balance(user_id, amount):
    conn = await asyncpg.connect(DATABASE_URL)
    balance = await conn.fetchval("SELECT balance FROM users WHERE user_id = $1", user_id)
    if balance is None:
        await conn.close()
        return False
    new_balance = max(MIN_BALANCE, min(balance + amount, MAX_BALANCE))
    await conn.execute("UPDATE users SET balance = $1 WHERE user_id = $2", new_balance, user_id)
    await conn.close()
    return True

async def log_action(action, user_id, username, details=""):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[{current_time}] ACTION: {action}, USER_ID: {user_id}, USER_NAME {username}, DETAILS: {details}"
    print(log_message)
    # Надсилаємо лог адміністратору
    await bot.send_message(ADMIN_ID, f"📋 Лог дій:\n{log_message}")
    if action == "buy":
        for admin in admins:
            await bot.send_message(admin["user_id"], f"🛒 Користувач {username} здійснив покупку: {details}")

# Хендлери
@dp.message(Command("start"))
async def handle_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "unknown"
    await register_user(user_id, username)
    await message.answer("👋 Вітаємо у боті! Оберіть дію з меню:", reply_markup=main_keyboard)

@dp.message(Command("balance"))
async def handle_balance_command(message: Message):
    args = message.text.split()
    if len(args) == 1:  # Перевіряємо баланс поточного користувача
        user_id = message.from_user.id
        balance = await get_user_balance(user_id)
        await message.answer(f"💰 Ваш баланс: {balance or 0} балів.")
    elif len(args) == 2:  # Перевіряємо баланс іншого користувача
        username = args[1].lstrip('@')
        conn = await asyncpg.connect(DATABASE_URL)
        balance = await conn.fetchval("SELECT balance FROM users WHERE username = $1", username)
        await conn.close()
        if balance is not None:
            await message.answer(f"💰 Баланс @{username}: {balance} балів.")
        else:
            await message.answer(f"❌ Користувача @{username} не знайдено.")

@dp.message(Command("rating"))
async def handle_rating(message: Message):
    users = await get_users()
    if not users:
        await message.answer("📉 Рейтинг порожній.")
        return
    rating = "\n".join([f"@{row['username']}: {row['balance']} балів" for row in users])
    await message.answer(f"🏆 Рейтинг користувачів:\n{rating}")

@dp.message(Command("admins"))
async def handle_admins(message: types.Message):
    conn = await asyncpg.connect(DATABASE_URL)
    admins = await conn.fetch("SELECT username FROM administrators")
    await conn.close()

    if not admins:
        await message.answer("❌ Список адміністраторів порожній.")
        return

    admin_list = "\n".join([f"@{admin['username']}" for admin in admins])
    await message.answer(f"👑 Список адміністраторів:\n{admin_list}")

@dp.message(Command("add"))
async def handle_add_admin(message: types.Message):
    if str(message.from_user.id) != ADMIN_ID:
        await message.answer("❌ У вас немає прав для цієї команди.")
        return

    args = message.text.split()
    if len(args) != 2:
        await message.answer("⚠️ Невірний формат команди. Використовуйте: /add @username")
        return

    username = args[1].lstrip('@')
    conn = await asyncpg.connect(DATABASE_URL)
    user_id = await conn.fetchval("SELECT user_id FROM users WHERE username = $1", username)

    if not user_id:
        await conn.close()
        await message.answer(f"👤 Користувача @{username} не знайдено.")
        return

    await conn.execute(
        "INSERT INTO administrators (user_id, username) VALUES ($1, $2) ON CONFLICT (user_id) DO NOTHING",
        user_id, username
    )
    await conn.close()

    await message.answer(f"✅ Користувач @{username} доданий до списку адміністраторів.")
    await log_action("add_admin", message.from_user.id, f"Added @{username}")

@dp.message(Command("remove"))
async def handle_remove_admin(message: types.Message):
    if str(message.from_user.id) != ADMIN_ID:
        await message.answer("❌ У вас немає прав для цієї команди.")
        return

    args = message.text.split()
    if len(args) != 2:
        await message.answer("⚠️ Невірний формат команди. Використовуйте: /remove @username")
        return

    username = args[1].lstrip('@')
    conn = await asyncpg.connect(DATABASE_URL)
    user_id = await conn.fetchval("SELECT user_id FROM administrators WHERE username = $1", username)

    if not user_id:
        await conn.close()
        await message.answer(f"👤 Користувача @{username} не знайдено у списку адміністраторів.")
        return

    await conn.execute("DELETE FROM administrators WHERE user_id = $1", user_id)
    await conn.close()

    await message.answer(f"❌ Користувач @{username} видалений зі списку адміністраторів.")
    await log_action("remove_admin", message.from_user.id, f"Removed @{username}")


@dp.message(lambda message: message.text == "📜 Команди")
async def handle_commands(message: Message):
    await message.answer(
        "🛠 Список команд:\n"
        "/balance - Перевірити баланс\n"
        "/rating - Переглянути рейтинг\n"
        "/adjust - Змінити баланс користувача\n"
        "/admins - Переглянути список адміністраторів\n",
        reply_markup=main_keyboard
    )

@dp.message(lambda message: message.text == "💰 Баланс")
async def handle_balance(message: Message):
    user_id = message.from_user.id
    balance = await get_user_balance(user_id)
    if balance is None:
        await message.answer("⚠️ Ви не зареєстровані в системі.")
    else:
        await message.answer(f"💰 Ваш баланс: {balance} балів.")

@dp.message(lambda message: message.text == "🛒 Купити")
async def handle_buy_menu(message: Message):
    await message.answer(
        "🛍 Оберіть товар:\n"
        "🛡 Старійшина - 10 балів\n"
        "⚔️ Підкріплення - 2 бали",
        reply_markup=buy_keyboard
    )

@dp.message(lambda message: message.text in ["🛡 Старійшина", "⚔️ Підкріплення"])
async def handle_buy_item(message: Message):
    items = {"🛡 Старійшина": 10, "⚔️ Підкріплення": 2}
    cost = items[message.text]
    user_id = message.from_user.id
    balance = await get_user_balance(user_id)

    if balance is None or balance < cost:
        await message.answer(f"❌ Недостатньо балів для покупки {message.text}.")
    else:
        await update_user_balance(user_id, -cost)
        await message.answer(f"✅ Ви придбали {message.text}!")
        await log_action("buy", user_id, f"Purchased {message.text}")

#Повертає користувача в головне меню
@dp.message(lambda message: message.text == "🔙 Назад")
async def handle_back(message: Message):
    await message.answer("🔙 Ви повернулись до головного меню.", reply_markup=main_keyboard)

@dp.message(Command("adjust"))
async def handle_adjust_command(message: Message):
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас немає прав для цієї команди.")
        return

    args = message.text.split()
    if len(args) != 3:
        await message.answer("⚠️ Невірний формат. Використовуйте: /adjust @username <кількість>")
        return

    username = args[1].lstrip('@')
    try:
        points = int(args[2])
    except ValueError:
        await message.answer("⚠️ Кількість балів має бути числом.")
        return

    conn = await asyncpg.connect(DATABASE_URL)
    user_id = await conn.fetchval("SELECT user_id FROM users WHERE username = $1", username)
    await conn.close()

    if not user_id:
        await message.answer(f"❌ Користувача @{username} не знайдено.")
        return
        
    success = await update_user_balance(user_id, points)
    if success:
        username = args[1].lstrip('@')
        conn = await asyncpg.connect(DATABASE_URL)
        balance = await conn.fetchval("SELECT balance FROM users WHERE username = $1", username)
        await conn.close()
        await log_action("adjust", message.from_user.id, f"Updated @{username}'s balance by {points}")
        await message.answer(f"✅ Баланс @{username} змінено, тепер він становить {balance} балів.")
    else:
        await message.answer(f"⚠️ Помилка оновлення балансу @{username}.")

async def main():
    print("Бот запущено...")
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
