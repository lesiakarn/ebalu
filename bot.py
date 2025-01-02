import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
import json

# Токен вашого бота
API_TOKEN = "5207732731:AAFXqa0bgsYyHXQnNt5MrrQVZA0kO1APt4I"

# Ініціалізація бота і диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Файли для збереження даних
DATA_FILE = 'data.json'
ADMINS_FILE = 'administrators.txt'


# Завантаження даних з файлу
def load_data():
    try:
        with open(DATA_FILE, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"users": {}}


def save_data(data):
    with open(DATA_FILE, 'w') as file:
        json.dump(data, file, indent=4)


def load_admins():
    try:
        with open(ADMINS_FILE, 'r') as file:
            return {line.strip() for line in file.readlines()}
    except FileNotFoundError:
        return set()


def save_admins(admins):
    with open(ADMINS_FILE, 'w') as file:
        file.write("\n".join(admins))


# Ініціалізація даних
data = load_data()
admins = load_admins()


def is_admin(user_id):
    return str(user_id) in admins


def is_user_in_group(user_id):
    return str(user_id) in data["users"]


def register_user(user_id, username):
    if str(user_id) not in data["users"]:
        data["users"][str(user_id)] = {"username": username, "points": 0}


# Команда для додавання адміністратора
@dp.message(Command("ad"))
async def add_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас немає прав для цієї команди.")
        return

    args = message.text.split()
    if len(args) != 2:
        await message.answer(
            "⚠️ Невірний формат команди. Використовуйте: /ad @username")
        return

    username = args[1].lstrip('@')
    user_id = next((uid for uid, info in data["users"].items()
                    if info["username"] == username), None)

    if not user_id:
        await message.answer(f"👤 Користувача @{username} не знайдено.")
        return

    admins.add(user_id)
    save_admins(admins)
    await message.answer(
        f"✅ Користувач @{username} доданий до списку адміністраторів.")


# Команда для видалення адміністратора
@dp.message(Command("un"))
async def remove_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас немає прав для цієї команди.")
        return

    args = message.text.split()
    if len(args) != 2:
        await message.answer(
            "⚠️ Невірний формат команди. Використовуйте: /un @username")
        return

    username = args[1].lstrip('@')
    user_id = next((uid for uid, info in data["users"].items()
                    if info["username"] == username), None)

    if not user_id or user_id not in admins:
        await message.answer(
            f"👤 Користувача @{username} не знайдено серед адміністраторів.")
        return

    admins.remove(user_id)
    save_admins(admins)
    await message.answer(
        f"❌ Користувач @{username} видалений зі списку адміністраторів.")


# Команда для перегляду списку адміністраторів
@dp.message(Command("admins"))
async def list_admins(message: Message):
    if not admins:
        await message.answer("📜 Список адміністраторів порожній.")
        return

    admin_usernames = [
        f"@{data['users'][admin_id]['username']}" for admin_id in admins
        if admin_id in data["users"]
    ]
    admin_list = "\n".join(admin_usernames)
    await message.answer(f"👑 Список адміністраторів:\n{admin_list}")


# Інші команди: /rating, /give, /take залишаються без змін
@dp.message(Command("rating"))
async def show_rating(message: Message):
    if not data["users"]:
        await message.answer("📉 Рейтинг порожній.")
        return

    sorted_users = sorted(data["users"].values(),
                          key=lambda x: x["points"],
                          reverse=True)
    rating = "\n".join([
        f"@{user['username']}: {user['points']} балів" for user in sorted_users
    ])
    await message.answer(f"🏆 Рейтинг користувачів:\n{rating}")


@dp.message(Command("give"))
async def give_points(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас немає прав для цієї команди.")
        return

    args = message.text.split()
    if len(args) != 3:
        await message.answer(
            "⚠️ Невірний формат команди. Використовуйте: /give @username <кількість>"
        )
        return

    username, points = args[1].lstrip('@'), int(args[2])
    user_id = next((uid for uid, info in data["users"].items()
                    if info["username"] == username), None)

    if not user_id:
        await message.answer(f"👤 Користувача @{username} не знайдено.")
        return

    data["users"][str(user_id)]["points"] += points
    save_data(data)
    await message.answer(f"✅ Додано {points} балів для @{username}.")
    await bot.send_message(user_id, f"🎉 Вам додано {points} балів.")


@dp.message(Command("take"))
async def take_points(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас немає прав для цієї команди.")
        return

    args = message.text.split()
    if len(args) != 3:
        await message.answer(
            "⚠️ Невірний формат команди. Використовуйте: /take @username <кількість>"
        )
        return

    username, points = args[1].lstrip('@'), int(args[2])
    user_id = next((uid for uid, info in data["users"].items()
                    if info["username"] == username), None)

    if not user_id:
        await message.answer(f"👤 Користувача @{username} не знайдено.")
        return

    current_points = data["users"][str(user_id)]["points"]

    # Знімаємо максимум доступних балів, якщо запит більше поточного балансу
    if points > current_points:
        points = current_points

    data["users"][str(user_id)]["points"] -= points
    save_data(data)

    await message.answer(f"❌ Знято {points} балів у @{username}.")
    await bot.send_message(user_id, f"⚠️ У вас знято {points} балів.")


@dp.message(Command("balance"))
async def show_balance(message: Message):
    args = message.text.split()

    if len(args) == 1:  # Перегляд власного балансу
        user_id = str(message.from_user.id)

        if user_id not in data["users"]:
            await message.answer(
                "⚠️ Ви ще не зареєстровані в системі. Надішліть будь-яке повідомлення, щоб зареєструватися."
            )
            return

        username = data["users"][user_id]["username"]
        points = data["users"][user_id]["points"]

        await message.answer(
            f"💰 Ваш баланс: {points} балів.\nКористувач: @{username}.")
    elif len(args) == 2:  # Перегляд балансу іншого користувача
        username = args[1].lstrip('@')
        user_id = next((uid for uid, info in data["users"].items()
                        if info["username"] == username), None)

        if not user_id:
            await message.answer(f"👤 Користувача @{username} не знайдено.")
            return

        points = data["users"][str(user_id)]["points"]
        await message.answer(
            f"💰 Баланс користувача @{username}: {points} балів.")
    else:
        await message.answer(
            "⚠️ Невірний формат команди. Використовуйте:\n- /balance (щоб побачити свій баланс)\n- /balance @username (щоб побачити баланс іншого користувача)"
        )


@dp.message()
async def auto_register_user(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username

    if not username:
        return

    if not is_user_in_group(user_id):
        register_user(user_id, username)
        save_data(data)


async def main():
    print("Бот запущено...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
