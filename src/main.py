import asyncio
import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from config.settings import get_settings
from config.logging import configure_logging
import repositories.teamly as teamly_repositories

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}! This bot can read your message/speech and convert it to note."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text('Help is coming soon.')


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo the user message."""
    await update.message.reply_text(update.message.text)


async def get_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Get basic info about the voice note file and prepare it for downloading."""
    new_file = await context.bot.get_file(update.message.voice.file_id)
    await new_file.download_to_drive('tmp/voice_note.ogg')
    await update.message.reply_text('Voice recognition is coming soon.')


def main(token) -> None:
    """Start the bot."""
    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start, block=False))
    application.add_handler(CommandHandler("help", help_command, block=False))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo, block=False))
    application.add_handler(MessageHandler(filters.VOICE, get_voice, block=False))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


class App:
    def __init__(self) -> None:
        self._settings = get_settings()
        configure_logging(self._settings)

    async def run_async(self) -> None:
        async with teamly_repositories.teamly_session_context() as teamly_session:
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
            await self._teamly_client.create_note('Вот это заметка что надо!')
        # while True:
        #     await asyncio.sleep(3)

    def run(self) -> None:
        logger.warning('Starting app...')
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.run_async())
        # main(self._settings.telegram.token)

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
