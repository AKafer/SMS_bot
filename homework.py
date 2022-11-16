import os
import time
from datetime import datetime, timedelta
import requests
import sys
import pytz


import telegram
import logging
from dotenv import load_dotenv
from http import HTTPStatus

from exceptions import NotStatusOkException, NotTokenException

load_dotenv()
utc=pytz.UTC

TURN = 'ON'
TOKEN_ADMIN = os.getenv('TOKEN_ADMIN')
ENDPOINT = 'https://online.moysklad.ru/api/remap/1.2/report/counterparty'
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600

HEADERS = {'Authorization': f'Bearer {TOKEN_ADMIN}'}
STEP = 100


def send_message(bot, message):
    """Отправляет сообщение в Телеграм."""
    logging.info('Отправляю сообщение в Телеграм')
    bot.send_message(TELEGRAM_CHAT_ID, message)
    logging.info('Отправлено сообщение в Телеграм')


def get_api_answer(current_timestamp, limit, offset):
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
        TELEGRAM_TOKEN is not None,
        TELEGRAM_CHAT_ID is not None
    ])
    return flag


def main():
    """Основная логика работы бота."""
    DATE_API_MEMORY = None
    ERROR_MEMORY = None
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
            'Не обнаружен один из ключей PRACTICUM_TOKEN,'
            'TELEGRAM_TOKEN, TELEGRAM_CHAT_ID'
        )
        raise NotTokenException(
            'Не обнаружен один из ключей PRACTICUM_TOKEN,'
            'TELEGRAM_TOKEN, TELEGRAM_CHAT_ID'
        )
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    send_message(bot, 'Бот с вами! Начинаем работу.')
    current_timestamp = int(time.time())
    if TURN == 'ON':
        while True:
            try:
                limit = STEP
                offset = 0
                final_user_list = []
                i = 0
                time_in_moscow = datetime.now(pytz.timezone('Europe/Moscow'))
                past_time = datetime.today() - timedelta(days=5)
                while True:
                    response = get_api_answer(current_timestamp, limit, offset)
                    rows = check_response(response)
                    if rows:
                        for row in rows:
                            i += 1
                            result = parse_info(row)
                            last_date = list(result.values())[0]['lastDemandDate']
                            if last_date != 'НЕТ ПОКУПОК':
                                last_date = datetime.strptime(last_date , '%Y-%m-%d %H:%M:%S.%f')
                                if  past_time.replace(tzinfo=utc) < last_date.replace(tzinfo=utc) < time_in_moscow.replace(tzinfo=utc):
                                    final_user_list.append(result)
                        offset += STEP
                        logging.info(f'Обработано пользователей: {offset}')
                    else:
                        break
                logging.info('Начинаю запись в файл')
                with open("RESULT.txt", "w") as file:
                    for  line in final_user_list:
                        file.write(str(line) + '\n')
                logging.info('Запись в файл завершена')
            except Exception as error:
                message = f'Сбой в работе программы: {error}'
                logging.error(message)
                if str(error) != str(ERROR_MEMORY):
                    ERROR_MEMORY = error
                    send_message(bot, message)
                current_timestamp = int(time.time())
            finally:
                time.sleep(RETRY_TIME)
    else:
        logging.info('TURN OFF')

if __name__ == '__main__':
    main()
