import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.client.bot import DefaultBotProperties
from aiogram.enums import ParseMode

from dotenv import load_dotenv
import os

TOKEN = '7535946244:AAH1EfK5cbUs6tIq3jf3XZDBhgZeq4qHTwE'
load_dotenv()
bot = Bot(os.getenv('TOKEN'), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


@dp.message(CommandStart())
async def start(message: Message):
    await message.answer('Привет')
    
    
@dp.message()
async def echo(message: Message):
    await message.answer(message.text)




async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)
    
    
    
if __name__ == '__main__':
    asyncio.run(main())    