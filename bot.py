import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from datetime import datetime
import asyncpg

# Токен вашого бота
API_TOKEN = "5207732731:AAFXqa0bgsYyHXQnNt5MrrQVZA0kO1APt4I"
ADMIN_ID = "5085585811"
MAX_POINTS = 1000  # Максимальна кількість балів, які можна додати чи зняти за один раз
MAX_BALANCE = 1000  # Максимальний баланс користувача
MIN_BALANCE = 0     # Мінімальний баланс користувача

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# URL підключення до PostgreSQL
DATABASE_URL = "postgresql://postgres:GbiDFCpQQvWbQGxjNrrzxOkVsNzdinhx@viaduct.proxy.rlwy.net:23347/railway"

async def init_db():
    conn = await asyncpg.connect(DATABASE_URL)
    # Створюємо таблицю користувачів
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            username TEXT,
            balance INT DEFAULT 0
        )
    """)
    # Створюємо таблицю адміністраторів
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS administrators (
            user_id BIGINT PRIMARY KEY,
            username TEXT
        )
    """)
    await conn.close()


async def get_user_balance(user_id):
    conn = await asyncpg.connect(DATABASE_URL)
    balance = await conn.fetchval("SELECT balance FROM users WHERE user_id = $1", user_id)
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

async def log_action(action: str, user_id: int, details: str = ""):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{current_time}] ACTION: {action}, USER_ID: {user_id}, DETAILS: {details}")

# Створення кнопок
commands_button = KeyboardButton(text="📜 Команди")
balance_button = KeyboardButton(text="💰 Баланс")
buy_button = KeyboardButton(text="🛒 Купити")

# Головна клавіатура
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🛒 Купити")],
        [KeyboardButton(text="📜 Команди"), KeyboardButton(text="💰 Баланс")],
    ],
    resize_keyboard=True,
)

# Клавіатура для "Купити"
buy_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🛡 Старійшина"), KeyboardButton(text="⚔️ Підкріплення")],
        [KeyboardButton(text="🔙 Назад")],  # Додаємо кнопку "Назад"
    ],
    resize_keyboard=True,
)

@dp.message()
async def auto_register_user(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "unknown"

    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute(
        "INSERT INTO users (user_id, username) VALUES ($1, $2) ON CONFLICT (user_id) DO NOTHING",
        user_id, username
    )
    await conn.close()

# Handlers
@dp.message(Command("start"))
async def handle_start(message: Message):
    await message.answer("👋 Вітаємо у боті! Оберіть дію з меню:", reply_markup=main_keyboard)

@dp.message(lambda message: message.text == "📜 Команди")
async def handle_commands(message: Message):
    await message.answer(
        "🛠 Список команд:\n"
        "/balance - Перевірити баланс\n"
        "/rating - Переглянути рейтинг\n"
        "/adjust - Змінити баланс користувача"
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

@dp.message(lambda message: message.text in ["🛒 Купити", "🔙 Назад"])
async def handle_buy_menu_or_back(message: Message):
    if message.text == "🛒 Купити":
        await message.answer(
            "🛍 Оберіть товар:\n"
            "🛡 Старійшина - 10 балів\n"
            "⚔️ Підкріплення - 5 балів",
            reply_markup=buy_keyboard
        )
    else:
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
        await message.answer(f"✅ Ви придбали {message.text}!", reply_markup=main_keyboard)
        await log_action(ADMIN_ID, f"Користувач {message.from_user.username} придбав {message.text}.")

@dp.message(Command("adjust"))
async def handle_adjust_balance(message: Message):
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас немає прав для виконання цієї команди.")
        return

    args = message.text.split()
    if len(args) != 3:
        await message.answer("⚠️ Невірний формат. Використовуйте: /adjust @username <кількість>")
        return

    username, points = args[1].lstrip('@'), int(args[2])
    conn = await asyncpg.connect(DATABASE_URL)
    user_id = await conn.fetchval("SELECT user_id FROM users WHERE username = $1", username)
    await conn.close()

    if not user_id:
        await message.answer(f"👤 Користувача @{username} не знайдено.")
        return

    current_balance = await get_user_balance(user_id)
    new_balance = max(MIN_BALANCE, min(current_balance + points, MAX_BALANCE))
    await update_user_balance(user_id, points)
    await log_action(ADMIN_ID, f"Адміністратор {message.from_user.username} змінив баланс @{username} на {points}.")
    await message.answer(f"✅ Баланс користувача @{username} оновлено: {new_balance} балів.")

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

async def main():
    print("Бот запущено...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
