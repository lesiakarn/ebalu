from aiogram import Bot

API_TOKEN = "5207732731:AAFXqa0bgsYyHXQnNt5MrrQVZA0kO1APt4I"

bot = Bot(token=API_TOKEN)

async def main():
    user = await bot.get_me()
    print(user)

import asyncio
asyncio.run(main())
