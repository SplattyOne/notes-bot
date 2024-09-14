import logging
import os
import typing
from contextlib import asynccontextmanager

from telegram import Update
from telegram.ext import Application, ContextTypes, CommandHandler, MessageHandler, filters

from services.telegram import TelegramClientProtocol
from utils.speech import SpeechRecognizer

logger = logging.getLogger(__name__)


@asynccontextmanager
async def telegram_app_context(telegram_token: str) -> typing.AsyncGenerator[Application, None]:
    """Context manager for Telegram app"""
    try:
        application = Application.builder().token(telegram_token).concurrent_updates(True).build()
        await application.initialize()
        await application.start()
        await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        yield application
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()


class TelegramClient(TelegramClientProtocol):
    def __init__(self, telegram_app: Application, tmp_dir: str = 'tmp') -> None:
        self._telegram_app = telegram_app
        self._tmp_dir = tmp_dir
        self._message_callback = None
        self._voice_callback = None
        self._telegram_app.add_handler(
            CommandHandler("start", self._start_handler, block=False))
        self._recognizer = SpeechRecognizer(self._tmp_dir)

    async def _text_message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.debug('Got message from telegram: %s', update.message.text)
        await self._message_callback(update.message.text)
        await update.message.reply_text('Message recieved.')

    async def _voice_message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.debug('Got voice from telegram: %s', update.message.voice.file_id)
        new_file = await context.bot.get_file(update.message.voice.file_id)
        voice_file_path = os.path.join(self._tmp_dir, update.message.voice.file_id + '.ogg')
        await new_file.download_to_drive(voice_file_path)
        text = self._recognizer.recognize(voice_file_path) or update.message.voice.file_id
        await self._voice_callback(text)
        os.unlink(voice_file_path)
        await update.message.reply_text('Voice recieved.')

    async def _start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send a message when the command /start is issued."""
        user = update.effective_user
        await update.message.reply_html(
            rf"Hi {user.mention_html()}! This bot can read your message/speech and convert it to note."
        )

    def handle_text_message(self, callback: typing.Coroutine) -> None:
        self._message_callback = callback
        self._telegram_app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            self._text_message_handler,
            block=False
        ))

    def handle_voice_message(self, callback: typing.Coroutine) -> None:
        self._voice_callback = callback
        self._telegram_app.add_handler(MessageHandler(
            filters.VOICE,
            self._voice_message_handler,
            block=False
        ))
