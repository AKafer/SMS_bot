import logging
import os
import sys
import time
from datetime import datetime, timedelta
from http import HTTPStatus

import pytz
import requests
import schedule
import telegram
from dotenv import load_dotenv
from my_store.exceptions import NotStatusOkException, NotTokenException
from my_store.devino_integration import ClassDevinoAPI
from my_store.mts_integration import ClassMtsAPI

load_dotenv()
utc = pytz.UTC

#  write your sms clint name mts or devino
SMS_CLIENT = 'mts'

TOKEN_ADMIN = os.getenv('TOKEN_ADMIN')
ENDPOINT = os.getenv('ENDPOINT')
TELEGRAM_TOKEN_AKAFER = os.getenv('TELEGRAM_TOKEN_AKAFER')
TELEGRAM_TOKEN_ANTRASHA = os.getenv('TELEGRAM_TOKEN_ANTRASHA')
TELEGRAM_TOKEN = TELEGRAM_TOKEN_ANTRASHA
TELEGRAM_CHAT_ID_MY = os.getenv('TELEGRAM_CHAT_ID_MY')
TELEGRAM_CHAT_ID_ALEX = os.getenv('TELEGRAM_CHAT_ID_ALEX')
SMS_TEXT = os.getenv('SMS_TEXT')
DEVINO_LOGIN = os.getenv('DEVINO_LOGIN')
DEVINO_PASSWORD = os.getenv('DEVINO_PASSWORD')
DEVINO_SOURCE_ADDRESS = os.getenv('DEVINO_SOURCE_ADDRESS')
MTS_LOGIN = os.getenv('MTS_LOGIN')
MTS_PASSWORD = os.getenv('MTS_PASSWORD')
MTS_NAME = os.getenv('MTS_NAME')

TURN_SENDING_SMS = True
HEADERS = {'Authorization': f'Bearer {TOKEN_ADMIN}'}
LIST_OF_CHAT_ID = [TELEGRAM_CHAT_ID_MY, TELEGRAM_CHAT_ID_ALEX]
DAYS_TO_RUN = [1, 4]
ERROR_KEY = (
    'Не обнаружен один из ключей'
    'TOKEN_ADMIN'
    'TELEGRAM_TOKEN_AKAFER'
    'TELEGRAM_TOKEN_ANTRASHA'
    'TELEGRAM_CHAT_ID_MY'
    'TELEGRAM_CHAT_ID_ALEX'
    'ENDPOINT'
    'DEVINO_LOGIN'
    'DEVINO_PASSWORD'
    'DEVINO_SOURCE_ADDRESS'
    'SMS_TEXT'
    'MTS_LOGIN'
    'MTS_PASSWORD'
    'MTS_NAME'
)


def send_message(bot, message):
    """Отправляет сообщение в Телеграм."""
    logging.info('Отправляю сообщение в Телеграм')
    for chat_id in LIST_OF_CHAT_ID:
        bot.send_message(chat_id, message)
    logging.info('Отправлено сообщение в Телеграм')


def send_file(bot, file):
    """Отправляет файл в Телеграм."""
    logging.info('Отправляю файл в Телеграм')
    try:
        with open(file, 'rb') as f:
            for chat_id in LIST_OF_CHAT_ID:
                bot.send_document(chat_id, f)
    except Exception as e:
        logging.error(f'Проблема с отправкой файла: {e}')
    finally:
        file_remove(file)
    logging.info('Файл отправлен')


def round_sec(bad_date):
    """Округляет секунды в переменной типа дата"""
    sample_date = datetime(2022, 1, 1, 12, 0, 0)
    dt = sample_date - bad_date
    td2 = timedelta(seconds=int(dt.total_seconds()))
    return sample_date - td2


def get_api_answer(start_date):
    """Направляет запрос к API Мой склад и возращает ответ."""
    start_date = round_sec(start_date)
    try:
        logging.info('Отправляю запрос к API Мой Склад')
        response = requests.get(
            ENDPOINT + f'/?filter=lastDemandDate>{start_date}',
            headers=HEADERS,
        )
        if response.status_code != HTTPStatus.OK:
            logging.error('Недоступность эндпоинта')
            raise NotStatusOkException('Недоступность эндпоинта')
        return response.json()
    except ConnectionError:
        logging.error('Сбой при запросе к эндпоинту')
        raise ConnectionError('Сбой при запросе к эндпоинту')


def check_response(response):
    """Возвращает содержимое в ответе от API Мой склад."""
    if not isinstance(response, dict):
        logging.error('API передал не словарь')
        raise TypeError('API передал не словарь')
    rows = response.get('rows')
    if rows is None:
        logging.error('API не содержит ключа homeworks')
        raise KeyError('API не содержит ключа homeworks')
    if not isinstance(rows, list):
        logging.error('Содержимое не список')
        raise TypeError('Содержимое не список')
    return rows


def parse_info(row):
    """Извлекает данные пользователя из записи в rows"""
    counterparty = row.get('counterparty')
    if counterparty is None:
        logging.error('В ответе API нет ключа counterparty')
        raise KeyError('В ответе API нет ключа counterparty')
    name = counterparty.get('name')
    if name is None:
        logging.error('В ответе API нет ключа name')
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
        TOKEN_ADMIN is not None,
        TELEGRAM_TOKEN_AKAFER is not None,
        TELEGRAM_TOKEN_ANTRASHA is not None,
        TELEGRAM_CHAT_ID_MY is not None,
        TELEGRAM_CHAT_ID_ALEX is not None,
        ENDPOINT is not None,
        DEVINO_LOGIN is not None,
        DEVINO_PASSWORD is not None,
        DEVINO_SOURCE_ADDRESS is not None,
        SMS_TEXT is not None,
        MTS_LOGIN is not None,
        MTS_PASSWORD is not None,
        MTS_NAME is not None,
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
        logging.info(f'Удаляю файл {file}')
        os.remove(file)
        logging.info(f'Удалил файл {file}')
    except Exception as e:
        logging.error(f'Какая-то проблема с удалением файла: {e}')


def main():
    """Основная логика работы бота."""
    time_in_moscow = datetime.now(pytz.timezone('Europe/Moscow'))
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    curday = datetime.isoweekday(datetime.today())
    if curday not in DAYS_TO_RUN:
        send_message(bot, 'Сегодня выходной. Рассылки не будет.')
        return False
    send_message(bot, f'Время работать: {time_in_moscow}')
    period_to_sms = get_period(DAYS_TO_RUN, curday)

    try:
        final_user_list = []
        start_date = datetime.today() - timedelta(days=period_to_sms)
        response = get_api_answer(start_date)
        rows = check_response(response)
        if rows:
            for row in rows:
                final_user_list.append(parse_info(row))
        logging.info('Начинаю сортировку по дате')
        final_user_list = sort_by_date(final_user_list)
        logging.info('Сортировка завершена')
        if TURN_SENDING_SMS:
            client = None
            if SMS_CLIENT == 'mts':
                client = ClassMtsAPI()
            elif SMS_CLIENT == 'devino':
                client = ClassDevinoAPI()
            if client is None:
                raise ValueError('Не верно указан клиент')
            logging.info('Начинаю рассылку смс')
            final_user_list, start_balance = client.sms_send(final_user_list)
            logging.info('Рассылка закончена')
            logging.info('Формирование отчета по смс')
            report = client.sms_report(final_user_list, start_balance)
            send_message(bot, report)
            logging.info('Отчет сформирован')
        logging.info('Начинаю запись в файл')
        with open(
            f'/tmp/RESULT-{datetime.today().strftime("%Y-%m-%d")}.txt',
            "w", encoding='utf-8'
        ) as file:
            for line in final_user_list:
                file.write(str(line) + '\n')
        logging.info('Запись в файл завершена')
        send_file(bot, file.name)

    except Exception as error:
        message = f'Сбой в работе программы: {error}'
        send_message(bot, f'Сбой в работе программы: {error}')
        logging.error(message)


if __name__ == '__main__':
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    logging.basicConfig(
        level=logging.INFO,
        format=(
            '%(asctime)s - [%(levelname)s][%(lineno)s][%(filename)s]'
            '[%(funcName)s]- %(message)s'
        ),
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    if check_tokens():
        logging.info('Токены впорядке')
    else:
        logging.critical(ERROR_KEY)
        send_message(bot, 'Бот не запустился. Ошибка c токенами.')
        raise NotTokenException(ERROR_KEY)
    send_message(bot, f'Бот начинает дежурство.\nДни рассылок: {DAYS_TO_RUN}')
    schedule.every().day.at("14:30").do(main)
    while True:
        schedule.run_pending()
        time.sleep(1)
