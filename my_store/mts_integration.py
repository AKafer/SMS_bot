import requests
import time
import os
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv()

MTS_LOGIN = os.getenv('MTS_LOGIN')
MTS_PASSWORD = os.getenv('MTS_PASSWORD')
MTS_NAME = os.getenv('MTS_NAME')
SMS_TEXT = os.getenv('SMS_TEXT')
to = '79032002566'


ClassMTSAPI:

    def correc_number(number: str) -> str:
        """Приведение к формату 7-XXX-XXX-XXXX"""
        if number.startswith('+7'):
            number = number[1:]
        elif number.startswith('8'):
            number = f'7{number[1:]}'
        elif number.startswith('7'):
            pass
        else:
            number = 'НЕ УКАЗАН'
        return number


    def sent_message(login, password, naming, to, text_message):
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
        resp = requests.post(url, json=body, auth=HTTPBasicAuth(login, password))
        return resp


    def check_balance(login: str, password: str) -> int:
        url = 'https://omnichannel.mts.ru/http-api/v1/messages/balanceManagement/balance/full'
        resp_info = requests.post(url, auth=HTTPBasicAuth(login, password))
        if resp_info.status_code == 200:
            try:
                balance = float(resp_info.json()["balance"])
            except (KeyError, AttributeError, TypeError):
                balance = 0
        else:
            balance = 0
        return balance


    def check_message(login, password, message_id):
        url = 'https://omnichannel.mts.ru/http-api/v1/messages/info'
        body = {"int_ids": [message_id]}
        resp_info = requests.post(url, json=body, auth=HTTPBasicAuth(login, password))
        return resp_info


    def mts_sms_send(user_list):
        """Отправляет смс клиентам из списка."""
        start_balance = check_balance(MTS_LOGIN, MTS_PASSWORD)
        final_user_list = []
        for user in user_list:
            phone = correc_number(user['phone'])
            if phone != 'НЕ УКАЗАН':
                response = sent_message(MTS_LOGIN, MTS_PASSWORD, MTS_NAME, phone, SMS_TEXT)
                if response.status_code == 200:
                    message_id = response.json()['messages'][0]["internal_id"]
                    user['sms_id'] = message_id
                else:
                    user['sms_id'] = '0'
            final_user_list.append(user)
        return final_user_list, start_balance


    def mts_sms_report(final_user_list: list, start_balance: int) -> dict:
        """Формирует отчет об отправленных смс."""
        time.sleep(120)
        costs = 0
        unsuccess_sms = 0
        for user in final_user_list:
            phone = user['phone']
            if phone != 'НЕ УКАЗАН':
                sms_id = user['sms_id']
                resp_info = check_message(MTS_LOGIN, MTS_PASSWORD, sms_id)
                response = requests.post(URL).json()
                if response['StateDescription'] == "Доставлено":
                    if response["Price"]:
                        costs += float(response["Price"])
                    user['status'] = 'ДОСТАВЛЕНО'
                else:
                    unsuccess_sms += 1
                    user['status'] = 'НЕ ДОСТАВЛЕНО'
            else:
                unsuccess_sms += 1
                user['status'] = 'НЕ ДОСТАВЛЕНО'
        URL = (
            f'https://integrationapi.net/rest/v2/User/Balance?'
            f'Login={DEVINO_LOGIN}&Password={DEVINO_PASSWORD}'
        )
        final_balance = check_balance(MTS_LOGIN, MTS_PASSWORD)
        return {
            'Clients': len(final_user_list),
            'Unsuccess': unsuccess_sms,
            'Costs': int(start_balance) - int(final_balance),
            'Balance': final_balance
        }






# Отправка сообщения
resp = sent_message(MTS_LOGIN, MTS_PASSWORD, MTS_NAME, to, SMS_TEXT)
# Проверка статуса
if resp.status_code == 200:
    message_id = resp.json()['messages'][0]["internal_id"]
    print("Запрос отработал успешно message_id = " + message_id)
    resp_info = check_message(MTS_LOGIN, MTS_PASSWORD, message_id)
    print(resp_info)
    if resp_info.status_code == 200:
        event_code = resp_info.json()["events_info"][0]["events_info"][0]["status"]
        if event_code == 200:
            print("SMS отправлено получателю " + to + ". message_id = " + message_id)
        elif event_code == 201:
            print("SMS НЕ отправлено message_id = " + message_id + " Детали см по кодам ошибок в документации " + str(
                resp_info.content))
        else:
            print("Запрос не отработал. Детали: " + str(resp.content))  






print(correc_number('+79098887766'))  
print(correc_number('89098887766')) 
print(correc_number('79098887766'))
print(correc_number('079098887766'))
        
        
# assert correc_number('+79098887766') == '79098887766'

# assert correc_number('89098887766') == '79098887766'

# assert correc_number('79098887766') == '79098887766'

# assert correc_number('079098887766') == 'НЕ УКАЗАН'
        