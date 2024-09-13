import typing


class MessageServiceProtocol(typing.Protocol):
    async def get_message(self) -> dict:
        ...


class NotesServiceProtocol(typing.Protocol):
    async def create_note(self) -> None:
        ...


class NotesHandler:
    def __init__(self, message_service: MessageServiceProtocol, notes_service: NotesServiceProtocol) -> None:
        self._message_service = message_service
        self._notes_service = notes_service

    async def transmit_message(self) -> None:
        message = await self._message_service.get_message()
        self._notes_service.create_note(message)
