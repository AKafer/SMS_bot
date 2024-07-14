import os

import redis
from dotenv import load_dotenv

load_dotenv()


#  envs variables
SMS_CLIENT = 'mts'  # mts or devino
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

#  bot settings
TURN_SENDING_SMS = True
HEADERS = {'Authorization': f'Bearer {TOKEN_ADMIN}'}
LIST_OF_CHAT_ID_PUBLIC = [TELEGRAM_CHAT_ID_MY, TELEGRAM_CHAT_ID_ALEX]
LIST_OF_CHAT_ID_DEV = [TELEGRAM_CHAT_ID_MY]
DAYS_TO_RUN = [1, 4]
TIME_TO_RUN_STORE_BOT_1 = '10:00'
TIME_TO_RUN_STORE_BOT_2 = '11:00'
TIME_TO_RUN_STORE_BOT_3 = '13:00'
TIME_TO_RUN_SMS_BOT = '14:00'
MAX_TRIED_TIMES = 5  # times for try end message


#  error messages
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

#  requests params
ALLOWED_RETRIES = 3
BACKOFF_SECONDS = 0.1

# logging
LOG_LEVEL = 'DEBUG'
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': (
                '%(asctime)s - [%(levelname)s][%(lineno)s]'
                '[%(filename)s][%(funcName)s]- %(message)s'
            )
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': LOG_LEVEL,
            'formatter': 'simple',
        },
    },
    'loggers': {
        'sms_bot': {
            'handlers': ['console'],
            'level': LOG_LEVEL,
        },
    },
}

#  cache
cache = redis.Redis(host='redis', port=6379, decode_responses=True)
ttl_cache = 6  # hours
