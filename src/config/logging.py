import logging

from config.settings import AppSettings


def configure_logging(settings: AppSettings) -> None:
    # console handler
    console_formatter = logging.Formatter(
        '%(asctime)s: %(levelname)s | %(name)s - %(message)s')
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(settings.log_level)
    # basicConfig
    logging.basicConfig(
        level='DEBUG',
        handlers=[console_handler],
        force=True
    )
    # change default loggers
    logging.getLogger('httpcore').setLevel('WARNING')
    logging.getLogger('httpx').setLevel('WARNING')
    logging.getLogger('telegram').setLevel('WARNING')
