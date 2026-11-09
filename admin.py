import os

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

import db

router = Router()


def is_admin(message: Message) -> bool:
    try:
        admin_id = int(os.getenv("ADMIN_ID", ""))
    except ValueError:
        return False
    return message.from_user.id == admin_id


@router.message(Command("admin"))
async def admin_help(message: Message):
    if not is_admin(message):
        return
    await message.answer(
        "🛠 Админ-команды:\n\n"
        "/stats — статистика\n"
        "/user ID — данные пользователя\n"
        "/give ID дни — выдать дни подписки"
    )


@router.message(Command("stats"))
async def stats(message: Message):
    if not is_admin(message):
        return
    await message.answer(
        f"📊 Пользователей: {db.count_users()}\n"
        f"✅ С активной подпиской: {db.count_active()}"
    )


@router.message(Command("user"))
async def user_info(message: Message, command: CommandObject):
    if not is_admin(message):
        return
    arg = (command.args or "").strip()
    if not arg.isdigit():
        await message.answer("Формат: /user ID")
        return
    row = db.get_user(int(arg))
    if row is None:
        await message.answer("Пользователь не найден.")
        return
    until = row["subscription_until"]
    await message.answer(
        f"ID: {row['user_id']}\n"
        f"Имя: {row['full_name']}\n"
        f"Username: {row['username'] or 'не указан'}\n"
        f"Регистрация: {row['created_at'][:10]}\n"
        f"Подписка до: {until[:10] if until else 'нет'}"
    )


@router.message(Command("give"))
async def give(message: Message, command: CommandObject):
    if not is_admin(message):
        return
    parts = (command.args or "").split()
    if len(parts) != 2 or not all(p.lstrip("-").isdigit() for p in parts):
        await message.answer("Формат: /give ID дни\nПример: /give 123456789 30")
        return
    until = db.add_days(int(parts[0]), int(parts[1]))
    if until is None:
        await message.answer(
            "Пользователь не найден. Он должен хотя бы раз нажать /start."
        )
        return
    await message.answer(f"✅ Готово. Подписка до {until[:10]}")
