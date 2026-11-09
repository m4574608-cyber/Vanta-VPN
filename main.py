import os
import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from dotenv import load_dotenv

import db

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

dp = Dispatcher()

WELCOME_TEXT = (
    "🚀 Добро пожаловать в VANTA VPN!\n\n"
    "Твой доступ к безопасному и стабильному соединению.\n\n"
    "Выбери нужный раздел:"
)


def main_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔑 Мой VPN", callback_data="my_vpn")],
            [
                InlineKeyboardButton(text="🌍 Серверы", callback_data="servers"),
                InlineKeyboardButton(text="💳 Подписка", callback_data="subscription"),
            ],
            [
                InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
                InlineKeyboardButton(text="🆘 Поддержка", callback_data="support"),
            ],
        ]
    )


def back_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
        ]
    )


async def show(callback: CallbackQuery, text: str, markup=None):
    await callback.answer()
    try:
        await callback.message.edit_text(
            text, reply_markup=markup or back_menu()
        )
    except TelegramBadRequest:
        pass


@dp.message(CommandStart())
async def start(message: Message):
    user = message.from_user
    db.add_user(user.id, user.username, user.full_name)
    await message.answer(WELCOME_TEXT, reply_markup=main_menu())


@dp.callback_query(F.data == "back")
async def back(callback: CallbackQuery):
    await show(callback, WELCOME_TEXT, main_menu())


@dp.callback_query(F.data == "my_vpn")
async def my_vpn(callback: CallbackQuery):
    await show(
        callback,
        "🔑 Твой VPN\n\n"
        "Пока у тебя нет активной конфигурации.\n"
        "После подключения VPN-сервера здесь появится твой ключ.",
    )


@dp.callback_query(F.data == "servers")
async def servers(callback: CallbackQuery):
    await show(
        callback,
        "🌍 Список серверов\n\nСерверы пока находятся в разработке.",
    )


@dp.callback_query(F.data == "subscription")
async def subscription(callback: CallbackQuery):
    await show(callback, "💳 Подписка\n\nСистема тарифов скоро появится.")


@dp.callback_query(F.data == "profile")
async def profile(callback: CallbackQuery):
    user = callback.from_user
    db.add_user(user.id, user.username, user.full_name)
    row = db.get_user(user.id)

    registered = row["created_at"][:10]
    if row["subscription_until"]:
        sub = "активна до " + row["subscription_until"][:10]
    else:
        sub = "нет активной подписки"
    username = f"@{user.username}" if user.username else "не указан"

    await show(
        callback,
        "👤 Твой профиль\n\n"
        f"ID: {user.id}\n"
        f"Имя: {user.full_name}\n"
        f"Username: {username}\n"
        f"Регистрация: {registered}\n"
        f"Подписка: {sub}",
    )


@dp.callback_query(F.data == "support")
async def support(callback: CallbackQuery):
    await show(
        callback,
        "🆘 Поддержка VANTA VPN\n\nРаздел находится в разработке.",
    )


async def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN не настроен!")

    db.init_db()
    bot = Bot(token=TOKEN)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
