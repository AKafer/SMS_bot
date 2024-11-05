import logging
from datetime import datetime
from logging import config as logging_config
import os
import time
from typing import Optional

import requests
import schedule
from requests.auth import HTTPBasicAuth

from my_store import conf
from my_store.conf import PENDING_PERIOD, SLEEP_SMS_SEND_PERIOD
from my_store.database import db, Message, Client
from my_store.exceptions import NotTokenException, HTTPClientError
from my_store.externals.http_client import HTTPClient

from my_store.externals.telegram_client import tg_client
from my_store.services import check_tokens

http_client = HTTPClient()


logging_config.dictConfig(conf.LOGGING)
logger = logging.getLogger("sms_bot")


def file_remove(file):
    """Удаляет файл с диска после отправки"""
    try:
        logger.info(f'Удаляю файл {file}')
        os.remove(file)
        logger.info(f'Удалил файл {file}')
    except Exception as e:
        logger.error(f'Какая-то проблема с удалением файла: {e}')


def sent_message(
        login: str,
        password: str,
        naming: str,
        to: str,
        text_message: str
) -> requests.Response:
    url = 'https://omnichannel.mts.ru/http-api/v1/messages'
    body = {
        "messages": [
            {
                "content": {
                    "short_text": text_message
                },
                "from": {
                    "sms_address": naming
                },
                "to": [
                    {
                        "msisdn": to
                    }
                ]
            }]
    }
    return http_client.post(
        url, data=body, auth=HTTPBasicAuth(login, password)
    )


def check_message(login: str, password: str, message_id: str) -> (Optional[bool], Optional[str]):
    url = 'https://omnichannel.mts.ru/http-api/v1/messages/info'
    body = {"int_ids": [message_id]}
    response = http_client.post(url, data=body, auth=HTTPBasicAuth(login, password))
    event_code = response["events_info"][0]["events_info"][0]["status"]
    if event_code == 200:
        return True, None
    elif event_code == 201:
        error_reason = response["events_info"][0]["events_info"][0]['internal_errors']
        return False, error_reason


def get_msg_list():
    msg_list = Message.select().where(
        (Message.status == 'NEW') &
        (Message.tried_times <= conf.MAX_TRIED_TIMES)
    )
    tg_client.send_message(f'Найдено {len(msg_list)} сообщений к рассылке', dev=True)
    logger.info(f'Найдено {len(msg_list)} сообщений к рассылке')
    return msg_list


def send_messages(msg_list):
    report = []
    for msg in msg_list:
        try:
            response = sent_message(
                conf.MTS_LOGIN,
                conf.MTS_PASSWORD,
                conf.MTS_NAME,
                msg.client_id,
                conf.SMS_TEXT
            )
            sms_id = response['messages'][0]['internal_id']
            msg.sms_id = sms_id
        except HTTPClientError as e:
            msg.sms_id = None
            msg.tried_times += 1
            msg.error_reason = f'HTTPClientError: {e}'
            if msg.tried_times > conf.MAX_TRIED_TIMES:
                msg.status = 'FAILED'
            name = Client.get(Client.phone == msg.client_id).name
            report.append(
                f'NAME: {name} | PHONE: {msg.client_id} | SMS_ID: {msg.sms_id} | '
                f'ERROR: {msg.error_reason} | TRIED: {msg.tried_times} | STATUS: {msg.status}'
            )
            report.append('***' * 15)
        finally:
            msg.save()
            time.sleep(SLEEP_SMS_SEND_PERIOD)

    for i in range(30):
        time.sleep(1)
        if i % 10 == 0:
            logger.info(f'Прошло {i} секунд')

    for msg in msg_list:
        if msg.sms_id is None:
            continue
        try:
            sms_status, error_reason = check_message(
                conf.MTS_LOGIN,
                conf.MTS_PASSWORD,
                msg.sms_id
            )
            if sms_status:
                msg.status = 'SUCCESS'
                msg.error_reason = None
            if error_reason:
                msg.error_reason = error_reason
        except HTTPClientError as e:
            msg.error_reason = f'HTTPClientError: {e}'
        finally:
            name = Client.get(Client.phone == msg.client_id).name
            msg.tried_times += 1
            if msg.tried_times > conf.MAX_TRIED_TIMES:
                msg.status = 'FAILED'
            msg.save()
            report.append(
                f'NAME: {name} | PHONE: {msg.client_id} | SMS_ID: {msg.sms_id} | '
                f'ERROR: {msg.error_reason} | TRIED: {msg.tried_times} | STATUS: {msg.status}'
            )
            report.append('***' * 15)
    return report


def send_report(report):
    with open(
            f'/tmp/RESULT-{datetime.today().strftime("%Y-%m-%d")}.txt',
            "w", encoding='utf-8'
    ) as file:
        for line in report:
            file.write(str(line) + '\n')
    tg_client.send_file(file.name)


def main():
    """Основная логика работы бота."""
    db.connect()
    try:
        msg_list = get_msg_list()
        report = send_messages(msg_list)
        send_report(report)
    except Exception as error:
        message = f'Сбой в работе программы: {error}'
        tg_client.send_message(f'Сбой в работе программы: {error}', dev=True)
        logger.error(message)
    finally:
        logger.info('Работа программы завершена')
        db.close()


if __name__ == '__main__':
    if check_tokens():
        logger.info('Токены впорядке')
    else:
        logger.critical(conf.ERROR_KEY)
        tg_client.send_message('Бот не запустился. Ошибка c токенами.')
        raise NotTokenException(conf.ERROR_KEY)
    logger.info(f'Время работать')
    tg_client.send_message('СМС_Бот начинает работу.', dev=True)
    schedule.every().day.at(conf.TIME_TO_RUN_SMS_BOT).do(main)
    while True:
        schedule.run_pending()
        time.sleep(PENDING_PERIOD)
