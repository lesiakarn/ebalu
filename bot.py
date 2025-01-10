import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
import asyncpg

# Токен вашого бота
API_TOKEN = "7867439762:AAG_ZLt6Jamj89ju8FpYb9DqRRlGfzXNi5Y"

# URL підключення до PostgreSQL
DATABASE_URL = "postgresql://postgres:GbiDFCpQQvWbQGxjNrrzxOkVsNzdinhx@viaduct.proxy.rlwy.net:23347/railway"
# Створення кнопок
commands_button = KeyboardButton(text="📜 Команди")
balance_button = KeyboardButton(text="💰 Баланс")
buy_button = KeyboardButton(text="🛒 Купити")

# Створення кнопок для "Купити"
elder_button = KeyboardButton(text="🛡 Старійшина")
reinforcement_button = KeyboardButton(text="⚔️ Підкріплення")

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

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
    ],
    resize_keyboard=True,
)


@dp.message(Command("start"))
async def handle_start(message: types.Message):
    await message.answer(
        "👋 Вітаємо у боті! Оберіть дію з меню нижче:",
        reply_markup=main_keyboard,
    )


@dp.message(lambda message: message.text == "📜 Команди")
async def handle_commands_menu(message: types.Message):
    await message.answer(
        "🛠 Ось список доступних команд:\n"
        "/balance - Перевірити баланс\n"
        "/rating - Переглянути рейтинг\n"
        "/give - Додати бали користувачеві (адміністраторам)\n"
        "/take - Зняти бали у користувача (адміністраторам)",
        reply_markup=main_keyboard,
    )


@dp.message(lambda message: message.text == "💰 Баланс")
async def handle_balance_button(message: types.Message):
    user_id = message.from_user.id
    conn = await asyncpg.connect(DATABASE_URL)
    points = await conn.fetchval("SELECT points FROM users WHERE user_id = $1", user_id)
    await conn.close()

    if points is None:
        await message.answer("⚠️ Ваш обліковий запис не зареєстровано в системі.")
    else:
        await message.answer(f"💰 Ваш баланс: {points} балів.")


@dp.message(lambda message: message.text == "🛒 Купити")
async def handle_buy_menu(message: types.Message):
    await message.answer(
        "🛍 Оберіть, що ви хочете придбати:",
        reply_markup=buy_keyboard,
    )


@dp.message(lambda message: message.text in ["🛡 Старійшина", "⚔️ Підкріплення"])
async def handle_buy_item(message: types.Message):
    item = "Старійшина" if message.text == "🛡 Старійшина" else "Підкріплення"
    cost = 10 if item == "Старійшина" else 5
    user_id = message.from_user.id
    username = message.from_user.username

    conn = await asyncpg.connect(DATABASE_URL)
    points = await conn.fetchval("SELECT points FROM users WHERE user_id = $1", user_id)

    if points is None or points < cost:
        await message.answer(
            f"❌ Недостатньо балів для покупки '{item}'. Необхідно: {cost} балів."
        )
    else:
        # Списати бали
        await conn.execute(
            "UPDATE users SET points = points - $1 WHERE user_id = $2", cost, user_id
        )
        # Відправка повідомлення адміністраторам
        admin_ids = await get_admins()
        for admin_id in admin_ids:
            await bot.send_message(admin_id, f"@{username} купив '{item}'.")

        await message.answer(
            f"✅ Ви успішно придбали '{item}'.", reply_markup=main_keyboard
        )


@dp.message(lambda message: message.text == "💰 Баланс")
async def handle_balance_button(message: Message):
    user_id = message.from_user.id
    conn = await asyncpg.connect(DATABASE_URL)
    points = await conn.fetchval("SELECT points FROM users WHERE user_id = $1", user_id)
    await conn.close()

    if points is None:
        await message.answer("⚠️ Ваш обліковий запис не зареєстровано в системі.")
    else:
        await message.answer(f"💰 Ваш баланс: {points} балів.")

@dp.message(lambda message: message.text == "🛒 Купити")
async def handle_buy_menu(message: Message):
    await message.answer(
        "🛍 Оберіть, що ви хочете придбати:",
        reply_markup=buy_keyboard
    )

@dp.message(lambda message: message.text in ["🛡 Старійшина", "⚔️ Підкріплення"])
async def handle_buy_item(message: Message):
    item = "Старійшина" if message.text == "🛡 Старійшина" else "Підкріплення"
    cost = 10 if item == "Старійшина" else 5
    user_id = message.from_user.id
    username = message.from_user.username

    conn = await asyncpg.connect(DATABASE_URL)
    points = await conn.fetchval("SELECT points FROM users WHERE user_id = $1", user_id)

    if points is None or points < cost:
        await message.answer(f"❌ Недостатньо балів для покупки '{item}'. Необхідно: {cost} балів.")
    else:
        # Списати бали
        await conn.execute(
            "UPDATE users SET points = points - $1 WHERE user_id = $2",
            cost, user_id
        )
        # Відправка повідомлення адміністраторам
        admin_ids = await get_admins()
        for admin_id in admin_ids:
            await bot.send_message(admin_id, f"@{username} купив '{item}'.")

        await message.answer(f"✅ Ви успішно придбали '{item}'.", reply_markup=main_keyboard)
    
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

# Хендлери
@dp.message(Command("start"))
async def handle_start(message: Message):
    await message.answer(
        "👋 Вітаємо у боті! Оберіть дію з меню нижче:",
        reply_markup=main_keyboard
    )

@dp.message(lambda message: message.text == "📜 Команди")
async def handle_commands_menu(message: Message):
    await message.answer(
        "🛠 Ось список доступних команд:\n"
        "/balance - Перевірити баланс\n"
        "/rating - Переглянути рейтинг\n"
        "/give - Додати бали користувачеві (адміністраторам)\n"
        "/take - Зняти бали у користувача (адміністраторам)",
        reply_markup=main_keyboard
    )

@dp.message(lambda message: message.text == "💰 Баланс")
async def handle_balance_button(message: Message):
    user_id = message.from_user.id
    conn = await asyncpg.connect(DATABASE_URL)
    points = await conn.fetchval("SELECT points FROM users WHERE user_id = $1", user_id)
    await conn.close()

    if points is None:
        await message.answer("⚠️ Ваш обліковий запис не зареєстровано в системі.")
    else:
        await message.answer(f"💰 Ваш баланс: {points} балів.")

@dp.message(lambda message: message.text == "🛒 Купити")
async def handle_buy_menu(message: Message):
    await message.answer(
        "🛍 Оберіть, що ви хочете придбати:",
        reply_markup=buy_keyboard
    )

@dp.message(lambda message: message.text in ["🛡 Старійшина", "⚔️ Підкріплення"])
async def handle_buy_item(message: Message):
    item = "Старійшина" if message.text == "🛡 Старійшина" else "Підкріплення"
    username = message.from_user.username

    # Відправка повідомлення адміністраторам
    admin_ids = await get_admins()
    for admin_id in admin_ids:
        await bot.send_message(admin_id, f"@{username} купив \"{item}\".")

    await message.answer(f"✅ Ви успішно придбали \"{item}\".", reply_markup=main_keyboard)

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
