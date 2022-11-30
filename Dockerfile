FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt /app

RUN pip3 install -r requirements.txt --no-cache-dir

COPY my_store/ /app

CMD ["python3", "sms_bot.py"] 