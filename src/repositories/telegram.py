import asyncio
import logging
import os
import typing
from contextlib import asynccontextmanager
from functools import wraps

from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, ContextTypes, CommandHandler, MessageHandler, filters

from services.telegram import TelegramClientProtocol
from utils.recognizer import SpeechRecognizerProtocol

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


def check_user_allowed(func):
    @wraps(func)
    async def _implementation(self: TelegramClientProtocol, update: Update, *func_args, **func_kwargs):
        """Check if user allowed and send message if not"""
        def _is_user_allowed(self: TelegramClientProtocol, update: Update):
            """User allow rules"""
            if not self._allowed_users:
                return True
            if not update.effective_user:
                return False
            user = update.effective_user
            if str(user.id) in self._allowed_users:
                return True
            return False
        #
        if _is_user_allowed(self, update):
            return await func(self, update, *func_args, **func_kwargs)
        if update.effective_user:
            await update.message.reply_html(
                rf"Hi {update.effective_user.mention_html()}! You are not allowed to use this bot, contact admin.")
        else:
            await update.message.reply_html(
                "Hi! You are not allowed to use this bot, contact admin.")
        return
    return _implementation


class TelegramClient(TelegramClientProtocol):
    _message_callback: typing.Callable = None
    _voice_callback: typing.Callable = None
    _allowed_users: list = None

    def __init__(self, telegram_app: Application, recognizer_app: SpeechRecognizerProtocol, tmp_dir: str = 'tmp',
                 allowed_users: list = []) -> None:
        self._telegram_app = telegram_app
        self._tmp_dir = tmp_dir
        self._allowed_users = allowed_users
        self._recognizer = recognizer_app
        self._handle_default_commands()

    @check_user_allowed
    async def _text_message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.debug('Got message from telegram: %s', update.message.text)
        await self._message_callback(update.message.text)
        await update.message.reply_text('Message recieved.')
        await update.message.delete()

    @check_user_allowed
    async def _voice_message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.debug('Got voice from telegram: %s', update.message.voice.file_id)
        new_file = await context.bot.get_file(update.message.voice.file_id)
        voice_file_path = os.path.join(self._tmp_dir, update.message.voice.file_id + '.ogg')
        await new_file.download_to_drive(voice_file_path)
        text = await self._recognizer.async_recognize(voice_file_path) or update.message.voice.file_id
        await self._voice_callback(text)
        os.unlink(voice_file_path)
        await update.message.reply_text('Voice recieved.')
        await update.message.delete()

    @check_user_allowed
    async def _notes_request_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.debug('Got notes request from telegram: %s', update.message.text)
        user = update.effective_user
        reply_message = await update.message.reply_html(
            f'Hi {user.mention_html()}! Your current notes:\n{await self._notes_request_callback()}'
        )
        await update.message.delete()
        await asyncio.sleep(10)
        await reply_message.delete()

    async def _start_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send a message when the command /start is issued."""
        user = update.effective_user
        keyboard = [
            [KeyboardButton("/notes"),],
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_html(
            f"Hi {user.mention_html()}! This bot can read your message/speech and convert it to note.",
            reply_markup=reply_markup
        )

    def _handle_default_commands(self):
        self._telegram_app.add_handler(
            CommandHandler("start", self._start_handler, block=False))

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

    def handle_notes_request(self, callback: typing.Coroutine) -> None:
        self._notes_request_callback = callback
        self._telegram_app.add_handler(
            CommandHandler("notes", self._notes_request_handler, block=False))
