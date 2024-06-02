import logging
import os
from logging import config as logging_config

from my_store import conf


logging_config.dictConfig(conf.LOGGING)
logger = logging.getLogger("sms_bot")


def check_tokens():
    """Check the presence of tokens in env."""
    return all([
        conf.TOKEN_ADMIN is not None,
        conf.TELEGRAM_TOKEN_AKAFER is not None,
        conf.TELEGRAM_TOKEN_ANTRASHA is not None,
        conf.TELEGRAM_CHAT_ID_MY is not None,
        conf.TELEGRAM_CHAT_ID_ALEX is not None,
        conf.ENDPOINT is not None,
        conf.DEVINO_LOGIN is not None,
        conf.DEVINO_PASSWORD is not None,
        conf.DEVINO_SOURCE_ADDRESS is not None,
        conf.SMS_TEXT is not None,
        conf.MTS_LOGIN is not None,
        conf.MTS_PASSWORD is not None,
        conf.MTS_NAME is not None,
    ])


def file_remove(file):
    """Remove file from disk after sending."""
    try:
        logger.info(f'Удаляю файл {file}')
        os.remove(file)
        logger.info(f'Удалил файл {file}')
    except Exception as e:
        logger.error(f'Проблема с удалением файла: {e}')
