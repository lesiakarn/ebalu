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
async def get_user_balance(user_id):
    conn = await asyncpg.connect(DATABASE_URL)
    balance = await conn.fetchval("SELECT balance FROM users WHERE user_id = $1", user_id)
    await conn.close()
    return balance or 0

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

async def log_action(action, user_id, details=""):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{current_time}] ACTION: {action}, USER_ID: {user_id}, DETAILS: {details}")

# Хендлери
@dp.message(Command("start"))
async def handle_start(message: Message):
    await message.answer("👋 Вітаємо у боті! Оберіть дію з меню:", reply_markup=main_keyboard)

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
        "⚔️ Підкріплення - 5 балів",
        reply_markup=buy_keyboard
    )

@dp.message(lambda message: message.text in ["🛡 Старійшина", "⚔️ Підкріплення"])
async def handle_buy_item(message: Message):
    items = {"🛡 Старійшина": 10, "⚔️ Підкріплення": 5}
    cost = items[message.text]
    user_id = message.from_user.id
    balance = await get_user_balance(user_id)

    if balance < cost:
        await message.answer(f"❌ Недостатньо балів для покупки {message.text}.")
    else:
        await update_user_balance(user_id, -cost)
        await message.answer(f"✅ Ви придбали {message.text}!")
        await log_action("buy", user_id, f"Purchased {message.text}")

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

    if not user_id:
        await conn.close()
        await message.answer(f"👤 Користувача @{username} не знайдено.")
        return

    current_balance = await get_user_balance(user_id)
    new_balance = max(MIN_BALANCE, min(current_balance + points, MAX_BALANCE))
    await update_user_balance(user_id, points)
    await log_action("adjust", message.from_user.id, f"Updated @{username}'s balance by {points}")
    await message.answer(f"✅ Баланс користувача @{username} оновлено: {new_balance} балів.")

# Основна функція
async def main():
    print("Бот запущено...")
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
