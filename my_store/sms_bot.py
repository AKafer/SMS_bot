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
DEVINO_LOGIN = os.getenv('DEVINO_LOGIN')
DEVINO_PASSWORD = os.getenv('DEVINO_PASSWORD')
DEVINO_SOURCE_ADDRESS = os.getenv('DEVINO_SOURCE_ADDRESS')
HEADERS = {'Authorization': f'Bearer {TOKEN_ADMIN}'}
SMS_TEXT = 'Оцените вашу покупку в магазине ANTRASHA: https://t.me/AntrashaBot'
STEP = 100
PERIOD_DAYS = 1
ERROR_KEY = (
    'Не обнаружен один из ключей'
    'TOKEN_ADMIN'
    'TELEGRAM_TOKEN'
    'TELEGRAM_CHAT_ID'
    'ENDPOINT'
    'DEVINO_LOGIN'
    'DEVINO_PASSWORD'
    'DEVINO_SOURCE_ADDRESS'
)


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
    return {'name': name,  'phone': phone, 'lastDemandDate': lastDemandDate}


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
        key=lambda x: x['lastDemandDate']
    )
    

def sms_send(final_user_list):
    for user in final_user_list:
        phone = user['phone']
        URL = (
            f'https://integrationapi.net/rest/v2/Sms/Send?Login={DEVINO_LOGIN}'
            f'&Password={DEVINO_PASSWORD}'
            f'&DestinationAddress={phone}'
            f'&SourceAddress={DEVINO_SOURCE_ADDRESS}'
            f'&Data={SMS_TEXT}'
        )
        response = requests.post(URL).json()
        user['sms_id'] = response
    return final_user_list


def sms_report(final_user_list):
    time.sleep(10)
    costs = 0
    unsuccess_sms = 0
    for user in final_user_list:
        sms_id = user['sms_id'][-1]
        URL = (
            f'https://integrationapi.net/rest/v2/Sms/State?Login={DEVINO_LOGIN}'
            f'&Password={DEVINO_PASSWORD}'
            f'&messageID={sms_id}'
        )
        response = requests.post(URL).json()
        if response is dict and  response['StateDescription'] == "Отправлено":
            if response["Price"]:
               costs += float(response["Price"])
        else:
            unsuccess_sms += 1
    URL = f'https://integrationapi.net/rest/v2/User/Balance?Login={DEVINO_LOGIN}&Password={DEVINO_PASSWORD}'  
    balance = requests.get(URL).json()
    return {'Clients': len(final_user_list), 'Unsuccess': unsuccess_sms, 'Costs': costs, 'Balance': balance}


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
                        last_date = result['lastDemandDate']
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
            logging.info('Начинаю рассылку смс')
            final_user_list = sms_send(final_user_list)
            print(final_user_list)
            logging.info('Рассылка закончена')
            logging.info('Формирование отчета по смс')
            report = sms_report(final_user_list)
            print(report)
            send_message(bot, report)
            logging.info('Отчет сформирован')
            logging.info('Начинаю запись в файл')
            with open(f'RESULT-{datetime.today().strftime("%Y-%m-%d")}.txt', "w", encoding='utf-8') as file:
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
        logging.critical(ERROR_KEY)
        send_message(bot, 'Бот не запустился. Ошибка')
        raise NotTokenException(ERROR_KEY)
    send_message(bot, 'Бот начинает нести службу')
    # schedule.every().hour.at(":05").do(main)
    schedule.every().day.at("17:16").do(main)
    while True:
        schedule.run_pending()
        time.sleep(1)
