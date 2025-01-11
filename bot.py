import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from datetime import datetime
from datetime import datetime
import asyncpg

# Токен вашого бота
API_TOKEN = "7867439762:AAG_ZLt6Jamj89ju8FpYb9DqRRlGfzXNi5Y"
ADMIN_ID = "1360055963"
MAX_BALANCE = 1000

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# URL підключення до PostgreSQL
DATABASE_URL = "postgresql://postgres:GbiDFCpQQvWbQGxjNrrzxOkVsNzdinhx@viaduct.proxy.rlwy.net:23347/railway"
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

@dp.message(lambda message: message.text in ["🛒 Купити", "🔙 Назад"])
async def handle_buy_menu_or_back(message: types.Message):
    if message.text == "🛒 Купити":
        await message.answer(
            "🛍 Оберіть, що ви хочете придбати:\n"
            "🛡 Старійшина - 10 балів\n"
            "⚔️ Підкріплення - 5 балів",
            reply_markup=buy_keyboard,  # Меню з кнопкою "Назад"
        )
    elif message.text == "🔙 Назад":
        await message.answer(
            "🔙 Ви повернулися до головного меню:",
            reply_markup=main_keyboard,  # Повертаємо головну клавіатуру
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

# Приклад реалізації функції для отримання балансу
user_balances = {}  # Це простий приклад, в реальному коді замініть на доступ до бази даних

async def get_user_balance(user_id: int) -> int:
    return user_balances.get(user_id, 0)  # Повертаємо 0, якщо користувача немає в словнику

MAX_POINTS = 1000  # Максимальна кількість балів, які можна додати чи зняти за один раз
MAX_BALANCE = 1000  # Максимальний баланс користувача
MIN_BALANCE = 0     # Мінімальний баланс користувача

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
    if points > MAX_POINTS:
        await message.answer(f"⚠️ Неможливо додати більше ніж {MAX_POINTS} балів за один раз.")
        return

    user_id = await get_user_id_by_username(username)

    if not user_id:
        await message.answer(f"👤 Користувача @{username} не знайдено.")
        return

    # Отримуємо поточний баланс користувача
    current_balance = await get_user_balance(user_id)

    # Додаємо бали, не даючи балансу перевищувати MAX_BALANCE
    new_balance = min(MAX_BALANCE, current_balance + points)

    # Оновлюємо баланс користувача в базі даних
    user_balances[user_id] = new_balance

    # Повідомлення адміністратору
    admin_username = message.from_user.username
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    await bot.send_message(
        ADMIN_ID, 
        f"Адміністратор @{admin_username} додав {points} балів користувачу @{username}.\n"
        f"Новий баланс: {new_balance}.\n"
        f"Дія виконана: {current_time}."
    )

    # Повідомлення користувачу
    await message.answer(f"✅ Додано {points} балів користувачу @{username}. Новий баланс: {new_balance} балів.")
    await bot.send_message(user_id, f"✅ Вам додано {points} балів. Ваш новий баланс: {new_balance} балів.")

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
    if points > MAX_POINTS:
        await message.answer(f"⚠️ Неможливо зняти більше ніж {MAX_POINTS} балів за один раз.")
        return

    user_id = await get_user_id_by_username(username)

    if not user_id:
        await message.answer(f"👤 Користувача @{username} не знайдено.")
        return

    # Отримуємо поточний баланс користувача
    current_balance = await get_user_balance(user_id)

    # Знімаємо бали, не даючи балансу йти в мінус
    new_balance = max(MIN_BALANCE, current_balance - points)

    # Оновлюємо баланс користувача в базі даних
    user_balances[user_id] = new_balance

    # Повідомлення адміністратору
    admin_username = message.from_user.username
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    await bot.send_message(
        ADMIN_ID, 
        f"Адміністратор @{admin_username} зняв {points} балів з користувача @{username}.\n"
        f"Новий баланс: {new_balance}.\n"
        f"Дія виконана: {current_time}."
    )

    # Повідомлення користувачу
    await message.answer(f"✅ Знято {points} балів з користувача @{username}. Новий баланс: {new_balance} балів.")
    await bot.send_message(user_id, f"❌ У вас знято {points} балів. Ваш новий баланс: {new_balance} балів.")

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
