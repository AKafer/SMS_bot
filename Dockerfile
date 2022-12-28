FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt /app

RUN pip3 install -r requirements.txt --no-cache-dir

COPY my_store/ /app

ENV TOKEN_ADMIN e973865ba4e8603e69160be3256f8b53e5d3a887
ENV TELEGRAM_TOKEN_AKAFER 5298286443:AAGoasP7nhX6ciQ6GO47KdDotLJjQp5WyYE
ENV TELEGRAM_TOKEN_ANTRASHA 5973158594:AAFt5UA-I8heYuoZGS9lXs13hTbr_Nxk1pA
ENV TELEGRAM_CHAT_ID_MY 749706860
ENV TELEGRAM_CHAT_ID_ALEX 49752082
ENV ENDPOINT https://online.moysklad.ru/api/remap/1.2/report/counterparty
ENV DEVINO_LOGIN antrasha
ENV DEVINO_PASSWORD 123456
ENV DEVINO_SOURCE_ADDRESS Antrasha
ENV SMS_TEXT 'Недавно Вы совершили покупку в магазине ANTRASHA. Мы будем Вам благодарны, если оцените ее у нас в telegram: https://t.me/AntrashaBot. Достаточно будет поставить оценку от 1 до 5.'

CMD ["python3", "sms_bot.py"] 