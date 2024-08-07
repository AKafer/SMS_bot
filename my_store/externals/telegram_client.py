import logging
from logging import config as logging_config

import telegram

from my_store import conf
from my_store.services import file_remove

logging_config.dictConfig(conf.LOGGING)
logger = logging.getLogger("sms_bot")


class TelegramClient:

    bot = telegram.Bot(token=conf.TELEGRAM_TOKEN)

    def send_message(self, message, dev=False):
        """Отправляет сообщение в Телеграм."""
        logger.info('Отправляю сообщение в Телеграм')
        chat_ids_list = conf.LIST_OF_CHAT_ID_DEV if dev else conf.LIST_OF_CHAT_ID_PUBLIC
        message = f'[def={dev}] {message}' if dev else message
        for chat_id in chat_ids_list:
            self.bot.send_message(chat_id, message)
        logger.info('Отправлено сообщение в Телеграм')

    def send_file(self, file):
        """Отправляет файл в Телеграм."""
        logger.info('Отправляю файл в Телеграм')
        try:
            with open(file, 'rb') as f:
                for chat_id in conf.LIST_OF_CHAT_ID_PUBLIC:
                    self.bot.send_document(chat_id, f)
        except Exception as e:
            logger.error(f'Проблема с отправкой файла: {e}')
        finally:
            file_remove(file)
        logger.info('Файл отправлен')


tg_client = TelegramClient()
