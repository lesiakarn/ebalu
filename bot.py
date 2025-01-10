import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
import asyncpg

# Токен вашого бота
API_TOKEN = "7867439762:AAG_ZLt6Jamj89ju8FpYb9DqRRlGfzXNi5Y-"

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

async def update_points(user_id, points):
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("UPDATE users SET points = points + $1 WHERE user_id = $2", points, user_id)
    await conn.close()

async def get_user_points(user_id):
    conn = await asyncpg.connect(DATABASE_URL)
    points = await conn.fetchval("SELECT points FROM users WHERE user_id = $1", user_id)
    await conn.close()
    return points

async def notify_admins(message):
    conn = await asyncpg.connect(DATABASE_URL)
    admin_ids = await conn.fetch("SELECT user_id FROM administrators")
    await conn.close()

    for admin in admin_ids:
        await bot.send_message(admin["user_id"], message)

# Основні команди
@dp.message(Command("commands"))
async def handle_commands(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="\ud83d\udd16 Команди", callback_data="commands")],
        [InlineKeyboardButton(text="\ud83d\udcb3 Баланс", callback_data="balance")],
        [InlineKeyboardButton(text="\ud83c\udf10 \u041a\u0443\u043f\u0438\u0442\u0438", callback_data="buy")]
    ])
    await message.answer("\u041e\u0431\u0435\u0440\u0456\u0442\u044c дію", reply_markup=keyboard)

@dp.callback_query(lambda callback: callback.data == "commands")
async def show_commands(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(
        "\u0421\u043f\u0438\u0441\u043e\u043a \u043a\u043e\u043c\u0430\u043d\u0434:\n"
        "\u2022 /balance - \u043f\u043e\u043a\u0430\u0437\u0430\u0442\u0438 \u0431\u0430\u043b\u0430\u043d\u0441\n"
        "\u2022 /rating - \u0440\u0435\u0439\u0442\u0438\u043d\u0433 \u043a\u043e\u0440\u0438\u0441\u0442\u0443\u0432\u0430\u0447\u0456\u0432"
    )

@dp.callback_query(lambda callback: callback.data == "balance")
async def show_balance(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    points = await get_user_points(user_id)
    await callback_query.message.edit_text(f"\ud83d\udcb3 \u0412\u0430\u0448 \u0431\u0430\u043b\u0430\u043d\u0441: {points} \u0431\u0430\u043b\u0456\u0432")

@dp.callback_query(lambda callback: callback.data == "buy")
async def buy_menu(callback_query: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="\ud83c\udf1f \u0421\u0442\u0430\u0440\u0456\u0439\u0448\u0438\u043d\u0430", callback_data="buy_elder")],
        [InlineKeyboardButton(text="\ud83c\udfc6 \u041f\u0456\u0434\u043a\u0440\u0456\u043f\u043b\u0435\u043d\u043d\u044f", callback_data="buy_support")]
    ])
    await callback_query.message.edit_text("\u041e\u0431\u0435\u0440\u0456\u0442\u044c \u043f\u0440\u0435\u0434\u043c\u0435\u0442 \u0434\u043b\u044f \u043a\u0443\u043f\u0456\u0432\u043b\u0456:", reply_markup=keyboard)

@dp.callback_query(lambda callback: callback.data.startswith("buy_"))
async def handle_buy(callback_query: types.CallbackQuery):
    item = "\u0421\u0442\u0430\u0440\u0456\u0439\u0448\u0438\u043d\u0430" if callback_query.data == "buy_elder" else "\u041f\u0456\u0434\u043a\u0440\u0456\u043f\u043b\u0435\u043d\u043d\u044f"

    user_id = callback_query.from_user.id
    username = callback
