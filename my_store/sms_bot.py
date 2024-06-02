import logging
from logging import config as logging_config
import os
import time
from datetime import datetime, timedelta

import peewee
import pytz
import schedule
import telegram

from my_store import conf
from my_store.conf import cache
from my_store.database import Client, db
from my_store.exceptions import NotTokenException
from my_store.externals.http_client import HTTPClient
from my_store.mts_integration import ClassMtsAPI


logging_config.dictConfig(conf.LOGGING)
logger = logging.getLogger("sms_bot")


def send_message(bot, message):
    """Отправляет сообщение в Телеграм."""
    logger.info('Отправляю сообщение в Телеграм')
    for chat_id in conf.LIST_OF_CHAT_ID:
        bot.send_message(chat_id, message)
    logger.info('Отправлено сообщение в Телеграм')


def send_file(bot, file):
    """Отправляет файл в Телеграм."""
    logger.info('Отправляю файл в Телеграм')
    try:
        with open(file, 'rb') as f:
            for chat_id in conf.LIST_OF_CHAT_ID:
                bot.send_document(chat_id, f)
    except Exception as e:
        logger.error(f'Проблема с отправкой файла: {e}')
    finally:
        file_remove(file)
    logger.info('Файл отправлен')


def round_sec(bad_date):
    """Округляет секунды в переменной типа дата"""
    sample_date = datetime(2022, 1, 1, 12, 0, 0)
    dt = sample_date - bad_date
    td2 = timedelta(seconds=int(dt.total_seconds()))
    return sample_date - td2


def get_api_answer(start_date):
    """Направляет запрос к API Мой склад и возращает ответ."""
    start_date = round_sec(start_date)
    http_client = HTTPClient()
    return http_client.get(
        conf.ENDPOINT + f'/?filter=lastDemandDate>{start_date}',
        headers=conf.HEADERS,
    )


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
    lastDemandDate = row.get('lastDemandDate')
    if lastDemandDate is None:
        lastDemandDate = 'НЕТ ПОКУПОК'
    return {'name': name, 'phone': phone, 'lastDemandDate': lastDemandDate}


def check_tokens():
    """Проверяет наличие токенов."""
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


def sort_by_date(non_sort_list):
    """Сортирует список клиентов по дате последней покупки"""
    return sorted(
        non_sort_list,
        key=lambda x: x['lastDemandDate']
    )


def get_period(days, day):
    """Определяет промежуток в днях между днями рассылки"""
    ind = days.index(day)
    if ind == 0:
        return day + 7 - days[-1]
    else:
        return day - days[ind - 1]


def file_remove(file):
    """Удаляет файл с диска после отправки"""
    try:
        logger.info(f'Удаляю файл {file}')
        os.remove(file)
        logger.info(f'Удалил файл {file}')
    except Exception as e:
        logger.error(f'Какая-то проблема с удалением файла: {e}')


def main():
    """Основная логика работы бота."""
    key_attempt = f'attempt_{datetime.today().strftime("%Y-%m-%d")}'
    key_prev_succed = f'prev_succed_{datetime.today().strftime("%Y-%m-%d")}'
    bot = telegram.Bot(token=conf.TELEGRAM_TOKEN)
    curday = datetime.isoweekday(datetime.today())
    prev_attempt = cache.get(key_attempt) or 0
    attempt = int(prev_attempt) + 1
    prev_succed = cache.get(key_prev_succed) == 'true'
    logger.info(f'КЭШ: attempt-{attempt} - prev_succed-{prev_succed}')
    if curday not in conf.DAYS_TO_RUN:
        logger.info(f'Сегодня выходной. Рассылки не будет.{attempt}')
        if not prev_succed:
            send_message(bot, f'Сегодня выходной. Рассылки не будет.{attempt}')
            cache.set(key_prev_succed, 'true')
        cache.set(key_attempt, attempt)
        return False
    if prev_succed:
        logger.info(f'Предыдущая рассылка прошла успешно. Пропускаю попытку {attempt}')
        cache.set(key_attempt, attempt)
        return False
    send_message(
        bot,
        f"Время работать: {datetime.now(pytz.timezone('Europe/Moscow'))}. Попытка {attempt}")
    period_to_sms = get_period(conf.DAYS_TO_RUN, curday)

    try:
        final_user_list = []
        start_date = datetime.today() - timedelta(days=period_to_sms)
        response = get_api_answer(start_date)
        logger.info(f'Получил ответ от API Мой Склад: {response}')
        rows = check_response(response)
        if rows:
            for row in rows:
                final_user_list.append(parse_info(row))
        logger.info('Начинаю сортировку по дате')
        final_user_list = sort_by_date(final_user_list)
        logger.info('Сортировка завершена')
        if conf.TURN_SENDING_SMS:
            client = None
            if conf.SMS_CLIENT == 'mts':
                client = ClassMtsAPI()
            if client is None:
                raise ValueError('Не верно указан клиент')
            logger.info('Начинаю рассылку смс')
            final_user_list, start_balance = client.sms_send(final_user_list)
            logger.info('Рассылка закончена')
            logger.info('Формирование отчета по смс')
            report = client.sms_report(final_user_list, start_balance)
            send_message(bot, report)
            logger.info('Отчет сформирован')
        cache.set(key_prev_succed, 'true')
        logger.info('Начинаю запись в файл')
        with open(
            f'/tmp/RESULT-{datetime.today().strftime("%Y-%m-%d")}.txt',
            "w", encoding='utf-8'
        ) as file:
            for line in final_user_list:
                file.write(str(line) + '\n')
        logger.info('Запись в файл завершена')
        send_file(bot, file.name)
    except Exception as error:
        message = f'Сбой в работе программы: {error}'
        send_message(bot, f'Сбой в работе программы: {error}')
        logger.error(message)
    finally:
        cache.set(key_attempt, attempt)
        logger.info('Работа программы завершена')


if __name__ == '__main__':
    db.connect()
    try:
        uncle_bobi = Client(
            name='Samanta',
            last_demand_date='2022-01-01',
            phone='7-999-999-99-55',
            sms_id='123456',
        )
        uncle_bobi.save()
    except peewee.IntegrityError:
        pass
    db.close()
    bot = telegram.Bot(token=conf.TELEGRAM_TOKEN)
    if check_tokens():
        logger.info('Токены впорядке')
    else:
        logger.critical(conf.ERROR_KEY)
        send_message(bot, 'Бот не запустился. Ошибка c токенами.')
        raise NotTokenException(conf.ERROR_KEY)
    send_message(bot, f'Бот начинает дежурство.\nДни рассылок: {conf.DAYS_TO_RUN}')
    schedule.every().day.at(conf.TIME_TO_RUN_1).do(main)
    schedule.every().day.at(conf.TIME_TO_RUN_2).do(main)
    schedule.every().day.at(conf.TIME_TO_RUN_3).do(main)
    logger.info(f'Время работы: {conf.TIME_TO_RUN_1}, {conf.TIME_TO_RUN_2}, {conf.TIME_TO_RUN_3}')
    while True:
        schedule.run_pending()
        time.sleep(1)
