import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from datetime import datetime
import asyncpg

# Константи
API_TOKEN = "5207732731:AAFXqa0bgsYyHXQnNt5MrrQVZA0kO1APt4I"
ADMIN_ID = "5085585811"
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
        [KeyboardButton(text="🛒 Купити")],
        [KeyboardButton(text="📜 Команди"), KeyboardButton(text="💰 Баланс")],
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
            user_id BIGINT PRIMARY KEY
        );
    ''')
    await conn.close()
    print("База даних ініціалізована.")

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

async def get_user_balance_by_username(username):
    conn = await asyncpg.connect(DATABASE_URL)
    balance = await conn.fetchval("SELECT balance FROM users WHERE username = $1", username)
    await conn.close()
    return balance

async def update_user_balance(user_id, amount):
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("UPDATE users SET balance = balance + $1 WHERE user_id = $2", amount, user_id)
    await conn.close()

async def is_admin(user_id):
    conn = await asyncpg.connect(DATABASE_URL)
    result = await conn.fetchval("SELECT EXISTS(SELECT 1 FROM administrators WHERE user_id = $1)", user_id)
    await conn.close()
    return result

async def get_users():
    conn = await asyncpg.connect(DATABASE_URL)
    rows = await conn.fetch("SELECT username, balance FROM users ORDER BY balance DESC")
    await conn.close()
    return rows

async def get_admins():
    conn = await asyncpg.connect(DATABASE_URL)
    admins = await conn.fetch("SELECT user_id FROM administrators")
    await conn.close()
    return admins

async def log_action(action, user_id, details=""):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{current_time}] ACTION: {action}, USER_ID: {user_id}, DETAILS: {details}")

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
    if len(args) == 1:  # Без аргументів, перевіряємо баланс поточного користувача
        user_id = message.from_user.id
        balance = await get_user_balance(user_id)
        await message.answer(f"💰 Ваш баланс: {balance or 0} балів.")
    elif len(args) == 2:  # З аргументом, перевіряємо баланс іншого користувача
        username = args[1].lstrip('@')
        balance = await get_user_balance_by_username(username)
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
async def handle_admins(message: Message):
    admins = await get_admins()
    if not admins:
        await message.answer("❌ Список адміністраторів порожній.")
        return
    admin_list = "\n".join([f"ID: {admin['user_id']}" for admin in admins])
    await message.answer(f"👑 Список адміністраторів:\n{admin_list}")

@dp.message(lambda message: message.text == "🛒 Купити")
async def handle_buy_menu(message: Message):
    await message.answer("🛍 Оберіть товар:", reply_markup=buy_keyboard)

@dp.message(lambda message: message.text == "🔙 Назад")
async def handle_back(message: Message):
    await message.answer("🔙 Повернення до головного меню:", reply_markup=main_keyboard)

@dp.message(lambda message: message.text in ["🛡 Старійшина", "⚔️ Підкріплення"])
async def handle_buy_item(message: Message):
    items = {"🛡 Старійшина": 10, "⚔️ Підкріплення": 5}
    cost = items[message.text]
    user_id = message.from_user.id
    balance = await get_user_balance(user_id)

    if balance is None or balance < cost:
        await message.answer(f"❌ Недостатньо балів для покупки {message.text}.")
    else:
        await update_user_balance(user_id, -cost)
        await message.answer(f"✅ Ви придбали {message.text}!")
        await log_action("buy", user_id, f"Purchased {message.text}")

async def main():
    print("Бот запущено...")
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
