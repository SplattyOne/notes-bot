import logging
import typing

import handlers.notes as notes_handlers

logger = logging.getLogger(__name__)


class TelegramClientProtocol(typing.Protocol):
    _allowed_users: list

    def handle_text_message(
        self,
        message_callback: typing.Callable[[str], typing.Coroutine[typing.Any, typing.Any, None]],
        search_callback: typing.Callable[[str], typing.Coroutine[typing.Any, typing.Any, tuple[str, list[str]]]]
    ) -> None:
        ...

    def handle_voice_message(
        self,
        callback: typing.Callable[[str], typing.Coroutine[typing.Any, typing.Any, None]]
    ) -> None:
        ...

    def handle_notes_request(
        self,
        callback: typing.Callable[[], typing.Coroutine[typing.Any, typing.Any, str]]
    ) -> None:
        ...


class TelegramService(notes_handlers.MessageServiceProtocol):
    def __init__(self, chat_client: TelegramClientProtocol) -> None:
        self._chat_client = chat_client

    async def handle_messages(
        self,
        message_callback: typing.Callable[[str], typing.Coroutine[typing.Any, typing.Any, None]],
        search_callback: typing.Callable[[str], typing.Coroutine[typing.Any, typing.Any, tuple[str, list[str]]]]
    ) -> None:
        self._chat_client.handle_text_message(message_callback, search_callback)
        self._chat_client.handle_voice_message(message_callback)

    async def handle_notes_request(
        self,
        callback: typing.Callable[[], typing.Coroutine[typing.Any, typing.Any, str]]
    ) -> None:
        self._chat_client.handle_notes_request(callback)
