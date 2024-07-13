from typing import Optional

import requests
import time
import os
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

from my_store.externals.http_client import HTTPClient

load_dotenv()

MTS_LOGIN = os.getenv('MTS_LOGIN')
MTS_PASSWORD = os.getenv('MTS_PASSWORD')
MTS_NAME = os.getenv('MTS_NAME')
SMS_TEXT = os.getenv('SMS_TEXT')


class ClassMtsAPI:
    sleep_time = 60
    http_client = HTTPClient()

    def correc_number(self, phone: str) -> str:
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

    def sent_message(
            self,
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
        return self.http_client.post(
            url, data=body, auth=HTTPBasicAuth(login, password)
        )


    def check_balance(self, login: str, password: str) -> int:
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

    def check_message(
            self, login: str, password: str, message_id: str
    ) -> (Optional[bool], Optional[str]):
        url = 'https://omnichannel.mts.ru/http-api/v1/messages/info'
        body = {"int_ids": [message_id]}
        try:
            response = self.http_client.post(url, data=body, auth=HTTPBasicAuth(login, password))
            event_code = response["events_info"][0]["events_info"][0]["status"]
            if event_code == 200:
                return True, None
            elif event_code == 201:
                error_reason = response["events_info"][0]["events_info"][0]['internal_errors']
                return False, error_reason
        except Exception:
            return None, None

    def sms_send(self, user_list: list) -> (list, int):
        """Отправляет смс клиентам из списка."""
        start_balance = self.check_balance(MTS_LOGIN, MTS_PASSWORD)
        final_user_list = []
        for user in user_list:
            phone = self.correc_number(user['phone'])
            user['phone'] = phone
            if phone != 'НЕ УКАЗАН':
                response = self.sent_message(MTS_LOGIN, MTS_PASSWORD, MTS_NAME, phone, SMS_TEXT)
                message_id = response['messages'][0]["internal_id"]
                user['sms_id'] = message_id
            final_user_list.append(user)
        return final_user_list, start_balance

    def sms_report(self, final_user_list: list, start_balance: int) -> dict:
        """Формирует отчет об отправленных смс."""
        time.sleep(self.sleep_time)
        unsuccess_sms = 0
        for user in final_user_list:
            phone = user['phone']
            if phone != 'НЕ УКАЗАН':
                sms_id = user['sms_id']
                sms_status, error_reason = self.check_message(MTS_LOGIN, MTS_PASSWORD, sms_id)
                if sms_status:
                    user['status'] = 'ДОСТАВЛЕНО'
                elif sms_status is None:
                    user['status'] = 'НЕ ИЗВЕСТНО'
                else:
                    unsuccess_sms += 1
                    user['status'] = 'НЕ ДОСТАВЛЕНО'
                    user['error_reason'] = error_reason
        final_balance = self.check_balance(MTS_LOGIN, MTS_PASSWORD)
        return {
            'Clients': len(final_user_list),
            'Unsuccess': unsuccess_sms,
            'Costs': int(start_balance) - int(final_balance),
            'Balance': final_balance
        }
