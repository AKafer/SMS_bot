class NotStatusOkException(Exception):
    """Исключение статуса ответа."""

    pass


class NotTokenException(Exception):
    """Исключение - нет всех токенов."""

    pass


class HTTPClientError(Exception):
    """Исключение клиента HTTP."""

    pass
