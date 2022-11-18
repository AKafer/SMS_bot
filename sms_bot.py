import os
import time
from datetime import datetime, timedelta
import requests
import sys
import pytz
import schedule


import telegram
import logging
from dotenv import load_dotenv
from http import HTTPStatus

from exceptions import NotStatusOkException, NotTokenException

load_dotenv()
utc = pytz.UTC

TURN = 'ON'
TOKEN_ADMIN = os.getenv('TOKEN_ADMIN')
ENDPOINT = os.getenv('ENDPOINT')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
HEADERS = {'Authorization': f'Bearer {TOKEN_ADMIN}'}
STEP = 100
PERIOD_DAYS = 5


def send_message(bot, message):
    """Отправляет сообщение в Телеграм."""
    logging.info('Отправляю сообщение в Телеграм')
    bot.send_message(TELEGRAM_CHAT_ID, message)
    logging.info('Отправлено сообщение в Телеграм')


def get_api_answer(limit, offset):
    """Направляет запрос к API Мой склад и возращает ответ."""
    try:
        logging.info('Отправляю запрос к API Мой Склад')
        response = requests.get(
            ENDPOINT + f'?limit={limit}&offset={offset}',
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
    return {name: {'phone': phone, 'lastDemandDate': lastDemandDate}}


def parse_date(homework):
    """Извлекает дату обновления работы из ответа ЯндексПракутикум."""
    date_updated = homework.get('date_updated')
    if date_updated is None:
        logging.error('В ответе API нет ключа date_updated')
        raise KeyError('В ответе API нет ключа date_updated')
    return date_updated


def check_tokens():
    """Проверяет наличие токенов."""
    flag = all([
        TOKEN_ADMIN is not None,
        TELEGRAM_TOKEN is not None,
        TELEGRAM_CHAT_ID is not None,
        ENDPOINT is not None,
    ])
    return flag


def sort_by_date(non_sort_list):
    return sorted(
        non_sort_list,
        key=lambda x: list(x.values())[0]['lastDemandDate']
    )


def main():
    """Основная логика работы бота."""
    time_in_moscow = datetime.now(pytz.timezone('Europe/Moscow'))
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    send_message(bot, f'Время работать: {time_in_moscow}')
    if TURN == 'ON':
        try:
            limit = STEP
            offset = 0
            final_user_list = []
            i = 0
            past_time = datetime.today() - timedelta(days=PERIOD_DAYS)
            while True:
                response = get_api_answer(limit, offset)
                rows = check_response(response)
                if rows:
                    for row in rows:
                        i += 1
                        result = parse_info(row)
                        last_date = list(result.values())[0]['lastDemandDate']
                        if last_date != 'НЕТ ПОКУПОК':
                            last_date = datetime.strptime(
                                last_date, '%Y-%m-%d %H:%M:%S.%f')
                            if (
                                past_time.replace(tzinfo=utc)
                                < last_date.replace(tzinfo=utc)
                                < time_in_moscow.replace(tzinfo=utc)
                            ):
                                final_user_list.append(result)
                    offset += STEP
                    logging.info(f'Обработано пользователей: {offset}')
                else:
                    break

            logging.info('Начинаю сортировку по дате')
            final_user_list = sort_by_date(final_user_list)
            logging.info('Сортировка завершена')
            logging.info('Начинаю запись в файл')
            with open("RESULT.txt", "w", encoding='utf-8') as file:
                for line in final_user_list:
                    file.write(str(line) + '\n')
            logging.info('Запись в файл завершена')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
    else:
        logging.info('TURN OFF')


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
        logging.critical(
            'Не обнаружен один из ключей'
            'TOKEN_ADMIN'
            'TELEGRAM_TOKEN'
            'TELEGRAM_CHAT_ID'
            'ENDPOINT'
        )
        send_message(bot, 'Бот не запустился. Ошибка')
        raise NotTokenException(
            'Не обнаружен один из ключей'
            'TOKEN_ADMIN'
            'TELEGRAM_TOKEN'
            'TELEGRAM_CHAT_ID'
            'ENDPOINT'
        )
    send_message(bot, 'Бот начинае нести службу')
    schedule.every().hour.at(":25").do(main)
    while True:
        schedule.run_pending()
        time.sleep(1)
