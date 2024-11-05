import json
import time
from datetime import datetime, timedelta

import pytz
import schedule
import logging
from logging import config as logging_config

from my_store import conf
from my_store.conf import (
    cache,
    REQUEST_REPORT_PERIOD_FROM_MY_SKLAD,
    PERIOD_TO_NOT_DISTURB,
)
from my_store.database import db, Client, Message
from my_store.exceptions import NotTokenException
from my_store.externals.http_client import HTTPClient
from my_store.externals.telegram_client import tg_client
from my_store.services import check_tokens

logging_config.dictConfig(conf.LOGGING)
logger = logging.getLogger('sms_bot')

http_client = HTTPClient()


def get_previos_attempt_params():
    """Получает параметры предыдущей попытки."""
    key_prev_attempt = f'attempt_{datetime.today().strftime("%Y-%m-%d")}'
    key_prev_succeed = f'prev_succeed_{datetime.today().strftime("%Y-%m-%d")}'
    prev_attempt = cache.get(key_prev_attempt) or 0
    prev_succeed = cache.get(key_prev_succeed) == 'true'
    logger.info(
        f'Cache: prev_attempt-{prev_attempt} - prev_succed-{prev_succeed}'
    )
    return prev_attempt, prev_succeed


def set_attempt_value(prev_attempt):
    key_prev_attempt = f'attempt_{datetime.today().strftime("%Y-%m-%d")}'
    cache.set(
        key_prev_attempt, prev_attempt, ex=timedelta(hours=conf.ttl_cache)
    )


def set_succeed_value(prev_succeed):
    key_prev_succeed = f'prev_succeed_{datetime.today().strftime("%Y-%m-%d")}'
    prev_succeed = str(prev_succeed).lower()
    cache.set(
        key_prev_succeed, prev_succeed, ex=timedelta(hours=conf.ttl_cache)
    )


def set_response_api(response):
    key_response_api = f'response_api_{datetime.today().strftime("%Y-%m-%d")}'
    cache.set(
        key_response_api,
        json.dumps(response),
        ex=timedelta(hours=conf.ttl_cache),
    )


def get_response_api():
    key_response_api = f'response_api_{datetime.today().strftime("%Y-%m-%d")}'
    raw_response = cache.get(key_response_api)
    return json.loads(raw_response) if raw_response else None


def round_sec(bad_date):
    """Округляет секунды в переменной типа дата"""
    sample_date = datetime(2022, 1, 1, 12, 0, 0)
    dt = sample_date - bad_date
    td2 = timedelta(seconds=int(dt.total_seconds()))
    return sample_date - td2


def get_api_answer(start_date):
    """Направляет запрос к API Мой склад и возращает ответ."""
    start_date = round_sec(start_date)
    return http_client.get(
        conf.ENDPOINT + f'/?filter=lastDemandDate>{start_date}',
        headers=conf.HEADERS,
    )


def check_if_today_is_workday(number_of_curren_day, prev_succeed, cur_attempt):
    if number_of_curren_day not in conf.DAYS_TO_RUN:
        logger.info(f'Сегодня выходной. СтореБот отдыхает.{cur_attempt}')
        if not prev_succeed:
            tg_client.send_message(
                f'Сегодня выходной. СтореБот отдыхает.{cur_attempt}', dev=True
            )
            set_succeed_value(True)
        return False
    return True


def check_response(response):
    """Возвращает содержимое в ответе от API Мой склад."""
    if not isinstance(response, dict):
        logger.error('API передал не словарь')
        raise TypeError('API передал не словарь')
    rows = response.get('rows')
    if rows is None:
        logger.error('API не содержит ключа homeworks')
        raise KeyError('API не содержит ключа homeworks')
    if not isinstance(rows, list):
        logger.error('Содержимое не список')
        raise TypeError('Содержимое не список')
    return rows


def correc_number(phone: str) -> str:
    """Приведение к формату 7-XXX-XXX-XXXX"""
    if phone.startswith('+7'):
        phone = phone[1:]
    elif phone.startswith('8'):
        phone = f'7{phone[1:]}'
    elif phone.startswith('7'):
        pass
    else:
        phone = 'НЕ УКАЗАН'
    return phone


def parse_info(row):
    """Извлекает данные пользователя из записи в rows"""
    counterparty = row.get('counterparty')
    if counterparty is None:
        logger.error('В ответе API нет ключа counterparty')
        raise KeyError('В ответе API нет ключа counterparty')
    name = counterparty.get('name')
    if name is None:
        logger.error('В ответе API нет ключа name')
        raise KeyError('В ответе API нет ключа name')
    phone = counterparty.get('phone')
    if phone is None:
        phone = 'НЕ УКАЗАН'
    else:
        phone = correc_number(phone)
    lastDemandDate = row.get('lastDemandDate')
    if lastDemandDate is None:
        lastDemandDate = 'НЕТ ПОКУПОК'
    return {'name': name, 'phone': phone, 'lastDemandDate': lastDemandDate}


def sort_by_date(non_sort_list):
    """Сортирует список клиентов по дате последней покупки"""
    return sorted(non_sort_list, key=lambda x: x['lastDemandDate'])


def get_list_of_new_users(user_list):
    new_user_list = []
    for user in user_list:
        if not Client.select().where(Client.phone == user['phone']):
            new_user_list.append(user)
    return new_user_list


def get_messages_list(msg_list):
    messages_list = []
    start_date = datetime.now() - timedelta(days=PERIOD_TO_NOT_DISTURB)
    for msg in msg_list:
        if Message.select().where(
            (Message.client == msg['phone'])
            & (Message.created_at >= start_date)
            & (Message.created_at <= datetime.now())
        ):
            continue
        else:
            messages_list.append(msg)
    return messages_list


def insert_to_db(user_list):
    new_user_list = get_list_of_new_users(user_list)
    with db.atomic():
        for user in new_user_list:
            Client.create(name=user['name'], phone=user['phone'])
    logger.info(f'Добавлено {len(new_user_list)} новых пользователей')
    new_message_list = get_messages_list(user_list)
    with db.atomic():
        for msg in new_message_list:
            Message.create(
                client=msg['phone'],
                created_at=datetime.now(),
                last_demand_date=msg['lastDemandDate'],
                status='NEW',
                error_reason=None,
                sms_id=None,
                tried_times=0,
            )
    logger.info(f'Добавлено {len(new_message_list)} новых сообщений')


def get_user_list(rows):
    final_user_list = []
    if rows:
        for row in rows:
            parse_row = parse_info(row)
            if parse_row['phone'] != 'НЕ УКАЗАН':
                final_user_list.append(parse_info(row))
        final_user_list = sort_by_date(final_user_list)
    return final_user_list


def get_today_night():
    return datetime(
        datetime.today().year,
        datetime.today().month,
        datetime.today().day,
        0,
        0,
        0,
    )


def main():
    db.connect()
    number_of_curren_day = datetime.isoweekday(datetime.today())
    logger.info(f'Сегодня {number_of_curren_day} день недели')
    try:
        prev_attempt, prev_succeed = get_previos_attempt_params()
        cur_attempt = int(prev_attempt) + 1
        if check_if_today_is_workday(
            number_of_curren_day, prev_succeed, cur_attempt
        ):
            tg_client.send_message(
                f"Время работать: {datetime.now(pytz.timezone('Europe/Moscow'))}."
                f' Попытка {cur_attempt}',
                dev=True,
            )
            today_night = get_today_night()
            start_date = today_night - timedelta(
                days=int(REQUEST_REPORT_PERIOD_FROM_MY_SKLAD)
            )
            response = get_response_api()
            if response is None:
                logger.info('Нет кэша')
                response = get_api_answer(start_date)
                set_response_api(response)
            else:
                logger.info('Есть кэш')
            rows = check_response(response)
            final_user_list = get_user_list(rows)
            insert_to_db(final_user_list)
            set_succeed_value(True)
    except Exception as exc:
        message = f'Сбой в работе программы: {exc}'
        tg_client.send_message(message, dev=True)
        logger.error(message)
        set_succeed_value(False)
    finally:
        db.close()
        set_attempt_value(cur_attempt)


if __name__ == '__main__':
    if check_tokens():
        logger.info('Токены впорядке')
    else:
        logger.critical(conf.ERROR_KEY)
        tg_client.send_message(
            'СторeБот не запустился. Ошибка c токенами.', dev=True
        )
        raise NotTokenException(conf.ERROR_KEY)
    tg_client.send_message(
        f'Бот начинает дежурство.\nДни рассылок: {conf.DAYS_TO_RUN}', dev=True
    )
    schedule.every().day.at(conf.TIME_TO_RUN_STORE_BOT_1).do(main)
    schedule.every().day.at(conf.TIME_TO_RUN_STORE_BOT_2).do(main)
    schedule.every().day.at(conf.TIME_TO_RUN_STORE_BOT_3).do(main)
    while True:
        schedule.run_pending()
        time.sleep(1)
