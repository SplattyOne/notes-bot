import logging
import typing

import handlers.notes as notes_handlers

logger = logging.getLogger(__name__)


class TelegramClientProtocol(typing.Protocol):
    _allowed_users: list = None

    def handle_text_message(self, callback: typing.Coroutine) -> None:
        ...

    def handle_voice_message(self, callback: typing.Coroutine) -> None:
        ...

    def handle_notes_request(self, callback: typing.Coroutine) -> None:
        ...


class TelegramService(notes_handlers.MessageServiceProtocol):
    def __init__(self, telegram_client: TelegramClientProtocol) -> None:
        self._telegram_client = telegram_client

    async def handle_messages(self, callback: typing.Coroutine) -> None:
        self._telegram_client.handle_text_message(callback)
        self._telegram_client.handle_voice_message(callback)

    async def handle_notes_request(self, callback: typing.Coroutine) -> None:
        self._telegram_client.handle_notes_request(callback)
