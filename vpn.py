from datetime import datetime, timezone


def is_active(user_row) -> bool:
    until = user_row["subscription_until"]
    if not until:
        return False
    return datetime.fromisoformat(until) > datetime.now(timezone.utc)


def get_key(user_id, until):
    """Создать или продлить ключ пользователя до даты until.

    Сейчас это заглушка. Когда появится сервер с панелью
    (например Marzban или 3x-ui), здесь будет запрос к её API,
    и функция вернёт ссылку-подписку для клиента.
    """
    return None


def access_text(user_row) -> str:
    if not is_active(user_row):
        return (
            "🔑 Твой VPN\n\n"
            "У тебя нет активной подписки.\n"
            "Оформить её можно в разделе «💳 Подписка»."
        )

    until = user_row["subscription_until"]
    link = get_key(user_row["user_id"], until)

    if link is None:
        return (
            "🔑 Твой VPN\n\n"
            f"Подписка активна до {until[:10]}.\n"
            "Ключ появится здесь после запуска VPN-серверов."
        )

    return (
        "🔑 Твой VPN\n\n"
        f"Подписка активна до {until[:10]}.\n\n"
        f"Твоя ссылка:\n{link}"
    )
