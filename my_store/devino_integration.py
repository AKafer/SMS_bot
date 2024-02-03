import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

DEVINO_LOGIN = os.getenv('DEVINO_LOGIN')
DEVINO_PASSWORD = os.getenv('DEVINO_PASSWORD')
DEVINO_SOURCE_ADDRESS = os.getenv('DEVINO_SOURCE_ADDRESS')
SMS_TEXT = os.getenv('SMS_TEXT')


class ClassDevinoAPI:
    sleep_time = 10

    def check_balance(self) -> int:
        URL = (
            f'https://integrationapi.net/rest/v2/User/Balance?'
            f'Login={DEVINO_LOGIN}&Password={DEVINO_PASSWORD}'
        )
        try:
            start_balance = int(requests.get(URL).json())
        except (KeyError, AttributeError, TypeError):
            start_balance = 0
        return start_balance

    def check_message(self, sms_id: int) -> dict:
        """Проверяет статус отправленного смс."""
        URL = (
            f'https://integrationapi.net/rest/v2/'
            f'Sms/State?Login={DEVINO_LOGIN}'
            f'&Password={DEVINO_PASSWORD}'
            f'&messageID={sms_id}'
        )
        response = requests.post(URL).json()
        return response

    def sms_send(self, final_user_list: list):
        """Отправляет смс клиентам из списка."""
        start_balance = self.check_balance()
        for user in final_user_list:
            phone = user['phone']
            if phone != 'НЕ УКАЗАН':
                URL = (
                    f'https://integrationapi.net/'
                    f'rest/v2/Sms/Send?Login={DEVINO_LOGIN}'
                    f'&Password={DEVINO_PASSWORD}'
                    f'&DestinationAddress={phone}'
                    f'&SourceAddress={DEVINO_SOURCE_ADDRESS}'
                    f'&Data={SMS_TEXT}'
                )
                response = requests.post(URL).json()
                user['sms_id'] = response
        return final_user_list, start_balance

    def sms_report(self, final_user_list: list, start_balance: int) -> dict:
        """Фоирмирует отчет об отправленных смс."""
        time.sleep(self.sleep_time)
        costs = 0
        unsuccess_sms = 0
        for user in final_user_list:
            phone = user['phone']
            if phone != 'НЕ УКАЗАН':
                sms_id = user['sms_id'][-1]
                response = self.check_message(sms_id)
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
        final_balance = self.check_balance()
        return {
            'Clients': len(final_user_list),
            'Unsuccess': unsuccess_sms,
            'Costs': int(start_balance) - int(final_balance),
            'Balance': final_balance
        }