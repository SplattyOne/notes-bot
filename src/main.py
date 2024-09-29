import asyncio
import logging
import os

from config.settings import get_settings
from config.logging import configure_logging
import handlers.notes as notes_handlers
import repositories.teamly as teamly_repositories
import repositories.yonote as yonote_repositories
import repositories.telegram as telegram_repositories
import utils.recognizer as recognizer_repositories
import services.teamly as teamly_services
import services.yonote as yonote_services
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
                yonote_repositories.yonote_session_context() as yonote_client, \
                telegram_repositories.telegram_app_context(self._settings.telegram.token) as telegram_app:
            self._teamly_auth = teamly_repositories.TeamlyAuthClient(
                teamly_session,
                self._settings.tmp_dir,
                self._settings.teamly.integration_id,
                self._settings.teamly.integration_url,
                self._settings.teamly.client_secret,
                self._settings.teamly.client_auth_code
            )
            self._teamly_client = teamly_repositories.TeamlyClient(
                teamly_session,
                self._teamly_auth,
                self._settings.teamly.database_id,
                self._settings.teamly.status_field_id,
                self._settings.teamly.status_field_value,
                self._settings.teamly.done_field_id
            )
            self._yonote_client = yonote_repositories.YonoteClient(
                yonote_client,
                self._settings.yonote.yonote_token,
                self._settings.yonote.database_id,
                self._settings.yonote.collection_id,
                self._settings.yonote.status_field_id,
                self._settings.yonote.status_field_value,
                self._settings.yonote.done_field_id
            )
            self._teamly_service = teamly_services.TeamlyService(self._teamly_client)
            self._yonote_service = yonote_services.YonoteService(self._yonote_client)
            self._recognizer = recognizer_repositories.SpeechRecognizer(self._settings.tmp_dir)
            self._telegram_client = telegram_repositories.TelegramClient(
                telegram_app, self._recognizer, self._settings.tmp_dir, self._settings.telegram.allowed_users)
            self._telegram_service = telegram_services.TelegramService(self._telegram_client)
            self._notes_handler = notes_handlers.NotesHandler(self._telegram_service)\
                .with_notes_service(self._yonote_service)
            #    .with_notes_service(self._teamly_service)
            await self._notes_handler.transmit_messages()
            while True:
                await asyncio.sleep(60)

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
