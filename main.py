import os
import asyncio
import logging
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaAnimation,
    InputMediaPhoto,
    Message,
)
from dotenv import load_dotenv

import admin
import db
import vpn

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

dp = Dispatcher()

BASE_DIR = Path(__file__).parent
BANNER = "welcome.jpg"
_file_ids = {}

WELCOME_TEXT = (
    "🚀 Добро пожаловать в VANTA VPN!\n\n"
    "Что тебя ждёт:\n"
    "🔐 Современный протокол VLESS + REALITY\n"
    "📱 Работает в v2rayNG, V2RayTun, Hiddify и других приложениях\n"
    "🔑 Личный ключ для каждого пользователя\n"
    "👤 Личный кабинет и подписка прямо в Telegram\n\n"
    "Выбери нужный раздел:"
)


def media_file(name):
    return _file_ids.get(name) or FSInputFile(BASE_DIR / name)


def remember(name, sent):
    if not isinstance(sent, Message):
        return
    if sent.animation:
        _file_ids[name] = sent.animation.file_id
    elif sent.photo:
        _file_ids[name] = sent.photo[-1].file_id


def media_input(name, caption):
    if name.endswith(".gif"):
        return InputMediaAnimation(media=media_file(name), caption=caption)
    return InputMediaPhoto(media=media_file(name), caption=caption)


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


async def show(callback: CallbackQuery, caption: str, media=BANNER, markup=None):
    await callback.answer()
    try:
        result = await callback.message.edit_media(
            media=media_input(media, caption),
            reply_markup=markup or back_menu(),
        )
        remember(media, result)
    except TelegramBadRequest as e:
        logging.warning("edit_media failed: %s", e)


@dp.message(CommandStart())
async def start(message: Message):
    user = message.from_user
    db.add_user(user.id, user.username, user.full_name)
    sent = await message.answer_photo(
        photo=media_file(BANNER),
        caption=WELCOME_TEXT,
        reply_markup=main_menu(),
    )
    remember(BANNER, sent)


@dp.callback_query(F.data == "back")
async def back(callback: CallbackQuery):
    await show(callback, WELCOME_TEXT, BANNER, main_menu())


@dp.callback_query(F.data == "my_vpn")
async def my_vpn(callback: CallbackQuery):
    user = callback.from_user
    db.add_user(user.id, user.username, user.full_name)
    row = db.get_user(user.id)
    await show(callback, vpn.access_text(row), "my_vpn.gif")


@dp.callback_query(F.data == "servers")
async def servers(callback: CallbackQuery):
    await show(
        callback,
        "🌍 Список серверов\n\nСерверы пока находятся в разработке.",
        "servers.gif",
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
    dp.include_router(admin.router)
    bot = Bot(token=TOKEN)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
