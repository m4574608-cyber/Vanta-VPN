
import os
import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()


def main_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔑 Мой VPN",
                    callback_data="my_vpn"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🌍 Серверы",
                    callback_data="servers"
                ),
                InlineKeyboardButton(
                    text="💳 Подписка",
                    callback_data="subscription"
                )
            ],
            [
                InlineKeyboardButton(
                    text="👤 Профиль",
                    callback_data="profile"
                ),
                InlineKeyboardButton(
                    text="🆘 Поддержка",
                    callback_data="support"
                )
            ]
        ]
    )


@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "🚀 Добро пожаловать в VANTA VPN!\n\n"
        "Твой доступ к безопасному и стабильному соединению.\n\n"
        "Выбери нужный раздел:",
        reply_markup=main_menu()
    )


@dp.callback_query(F.data == "my_vpn")
async def my_vpn(callback):
    await callback.answer()
    await callback.message.answer(
        "🔑 Твой VPN\n\n"
        "Пока у тебя нет активной конфигурации.\n"
        "После подключения VPN-сервера здесь появится твой ключ."
    )


@dp.callback_query(F.data == "servers")
async def servers(callback):
    await callback.answer()
    await callback.message.answer(
        "🌍 Список серверов\n\n"
        "Серверы пока находятся в разработке."
    )


@dp.callback_query(F.data == "subscription")
async def subscription(callback):
    await callback.answer()
    await callback.message.answer(
        "💳 Подписка\n\n"
        "Система тарифов скоро появится."
    )


@dp.callback_query(F.data == "profile")
async def profile(callback):
    await callback.answer()
    user = callback.from_user
    await callback.message.answer(
        f"👤 Твой профиль\n\n"
        f"ID: {user.id}\n"
        f"Имя: {user.full_name}\n"
        f"Username: @{user.username or 'не указан'}"
    )


@dp.callback_query(F.data == "support")
async def support(callback):
    await callback.answer()
    await callback.message.answer(
        "🆘 Поддержка VANTA VPN\n\n"
        "Раздел находится в разработке."
    )


async def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN не настроен!")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
