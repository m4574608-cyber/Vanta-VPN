import os
import asyncio
import logging
from pathlib import Path
from urllib.parse import quote

from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandObject, CommandStart
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
import tariffs
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


def fmt_until(value):
    return value[:16].replace("T", " ") + " UTC"


def parse_referrer(args):
    if args and args.startswith("ref_") and args[4:].isdigit():
        return int(args[4:])
    return None


def main_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔑 Мой VPN", callback_data="my_vpn")],
            [
                InlineKeyboardButton(text="🌍 Серверы", callback_data="servers"),
                InlineKeyboardButton(text="💳 Подписка", callback_data="subscription"),
            ],
            [
                InlineKeyboardButton(text="👥 Друзья", callback_data="friends"),
                InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
            ],
            [InlineKeyboardButton(text="🆘 Поддержка", callback_data="support")],
        ]
    )


def back_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
        ]
    )


def subscription_menu():
    rows = []
    for tariff_id, t in tariffs.TARIFFS.items():
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"💳 {t['title']} — {t['price']}",
                    callback_data=f"buy_{tariff_id}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


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
async def start(message: Message, command: CommandObject):
    user = message.from_user

    referrer_id = parse_referrer(command.args)
    if referrer_id is not None:
        if referrer_id == user.id or db.get_user(referrer_id) is None:
            referrer_id = None

    db.add_user(user.id, user.username, user.full_name, referrer_id)
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
async def my_vpn(callback: CallbackQuery, bot: Bot):
    user = callback.from_user
    db.add_user(user.id, user.username, user.full_name)

    referrer_id = db.confirm_referral(user.id)
    if referrer_id:
        until = db.claim_referral_reward(
            referrer_id,
            tariffs.REF_PER_REWARD,
            tariffs.REF_REWARD_DAYS,
            tariffs.REF_COOLDOWN_DAYS,
        )
        if until:
            try:
                await bot.send_message(
                    referrer_id,
                    "🎉 Твои друзья присоединились!\n"
                    f"Тебе добавлено {tariffs.REF_REWARD_DAYS} дн. доступа "
                    f"(до {fmt_until(until)}).",
                )
            except Exception as e:
                logging.warning("referrer notify failed: %s", e)

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
    user = callback.from_user
    db.add_user(user.id, user.username, user.full_name)
    row = db.get_user(user.id)

    if vpn.is_active(row):
        status = "активна до " + fmt_until(row["subscription_until"])
    else:
        status = "нет активной подписки"

    await show(
        callback,
        "💳 Подписка\n\n"
        f"Статус: {status}\n\n"
        "Выбери тариф. Бесплатные дни можно получить за приглашение "
        "друзей в разделе «👥 Друзья».",
        markup=subscription_menu(),
    )


@dp.callback_query(F.data.startswith("buy_"))
async def buy(callback: CallbackQuery):
    await show(
        callback,
        "💳 Оплата скоро появится.\n\n"
        "Мы сообщим, когда её можно будет подключить.",
    )


@dp.callback_query(F.data == "friends")
async def friends(callback: CallbackQuery, bot: Bot):
    user = callback.from_user
    db.add_user(user.id, user.username, user.full_name)

    me = await bot.me()
    link = f"https://t.me/{me.username}?start=ref_{user.id}"

    per = tariffs.REF_PER_REWARD
    days = tariffs.REF_REWARD_DAYS
    cooldown = tariffs.REF_COOLDOWN_DAYS
    status = db.referral_status(user.id, per, cooldown)

    text = (
        "👥 Друзья\n\n"
        f"За каждых {per} приглашённых друзей ты получаешь +{days} дн. доступа. "
        f"Награду можно получать раз в {cooldown} дн., отсчёт идёт с момента "
        "последней награды.\n\n"
        "Друг засчитывается, когда зайдёт по твоей ссылке и нажмёт «🔑 Мой VPN».\n\n"
        f"Приглашено: {status['counted']}\n"
    )
    if status["need"]:
        text += f"До награды: ещё {status['need']}\n"
    if status["wait_days"]:
        text += f"Следующая награда через {status['wait_days']} дн.\n"
    if status["can_claim"]:
        text += "🎁 Награда готова! Нажми кнопку ниже.\n"
    text += f"\nТвоя ссылка:\n{link}"

    share_url = (
        "https://t.me/share/url?url=" + quote(link)
        + "&text=" + quote("Попробуй VANTA VPN")
    )
    rows = []
    if status["can_claim"]:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"🎁 Забрать +{days} дн.", callback_data="claim_ref"
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="📤 Поделиться ссылкой", url=share_url)])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back")])

    await show(callback, text, markup=InlineKeyboardMarkup(inline_keyboard=rows))


@dp.callback_query(F.data == "claim_ref")
async def claim_ref(callback: CallbackQuery):
    user = callback.from_user
    db.add_user(user.id, user.username, user.full_name)
    until = db.claim_referral_reward(
        user.id,
        tariffs.REF_PER_REWARD,
        tariffs.REF_REWARD_DAYS,
        tariffs.REF_COOLDOWN_DAYS,
    )
    if until is None:
        text = "🎁 Награда пока недоступна."
    else:
        text = (
            f"🎁 Тебе добавлено {tariffs.REF_REWARD_DAYS} дн. доступа!\n"
            f"Подписка активна до {fmt_until(until)}."
        )
    await show(callback, text)


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
