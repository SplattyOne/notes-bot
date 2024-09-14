import asyncio
import logging
import os

from config.settings import get_settings
from config.logging import configure_logging
import handlers.notes as notes_handlers
import repositories.teamly as teamly_repositories
import repositories.telegram as telegram_repositories
import services.teamly as teamly_services
import services.telegram as telegram_services

logger = logging.getLogger(__name__)


class App:
    def __init__(self) -> None:
        self._settings = get_settings()
        configure_logging(self._settings)
        self._configure_dirs()

    def _configure_dirs(self):
        if not os.path.exists(self._settings.tmp_dir):
            os.mkdir(self._settings.tmp_dir)

    async def run_async(self) -> None:
        async with teamly_repositories.teamly_session_context() as teamly_session, \
                telegram_repositories.telegram_app_context(self._settings.telegram.token) as telegram_app:
            self._teamly_client = teamly_repositories.TeamlyClient(
                teamly_session,
                self._settings.teamly.database_id,
                self._settings.tmp_dir
            ).with_session(
                self._settings.teamly.integration_id,
                self._settings.teamly.integration_url,
                self._settings.teamly.client_secret,
                self._settings.teamly.client_auth_code
            )
            self._teamly_service = teamly_services.TeamlyService(self._teamly_client)
            self._telegram_client = telegram_repositories.TelegramClient(telegram_app, self._settings.tmp_dir)
            self._telegram_service = telegram_services.TelegramService(self._telegram_client)
            self._notes_handler = notes_handlers.NotesHandler(self._telegram_service, self._teamly_service)
            await self._notes_handler.transmit_messages()
            while True:
                await asyncio.sleep(0)

    def run(self) -> None:
        logger.warning('Starting app...')
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.run_async())

    def close(self) -> None:
        logger.warning('Closing app...')


if __name__ == '__main__':
    app = App()
    try:
        app.run()
    except KeyboardInterrupt:
        pass
    finally:
        app.close()
