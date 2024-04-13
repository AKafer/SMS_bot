# SMS_bot

# An application that collects information about sales for a certain period and sends SMS to customers to complete a survey in Telegram about the quality of their purchase

## Description

### Using the requests library, the application sends a request to the API endpoint of the "My Scud" application, which contains information about customers and sales. The frequency of the request and mailing can be determined through a special constant - a list containing the serial numbers of the days of the week.

### The application checks the response from the endpoint, the response format (json), and the content of the necessary information.

### If the response does not meet the requirements, a corresponding message is sent via telegram.

### If the response is valid, an SMS mailing list is forming

### The mailing is carried out using the mobile operator's API (two operators are available); based on the results of the mailing, an integral report is generated (the number of clients for the period, successfully sent SMS, the cost of sending and the current account balance), as well as a file containing information about each client. These reports are sent via telegram to the store owner.

### Application error logging has been implemented.

## How to run project locally

### Clone the repository and go to it on the command line:

```
git clone https://github.com/AKafer/my_store_sales.git
cd my_store_sales
```

### Create and activate a virtual environment:

```
python -m venv venv
source venv/Scripts/activate
```

### Install dependencies from the requirements.txt file::

```
pip install -r requirements.txt
```

### Go to the /my_store/ folder and create .env file with the following contents:

```
TOKEN_ADMIN='************'  # token for the my_scud application
TELEGRAM_TOKEN_AKAFER='************' # first telegram bot token
TELEGRAM_TOKEN_ANTRASHA='************' # second telegram bot token (must be any value if you don't use it)
TELEGRAM_CHAT_ID_MY='************' # telegram chat id
TELEGRAM_CHAT_ID_ALEX='************' # telegram chat id (must be any value if you don't use it)
ENDPOINT='https://api.moysklad.ru/api/remap/1.2/report/counterparty'
DEVINO_LOGIN='************' # first mobile operator login
DEVINO_PASSWORD='************' # first mobile operator password
DEVINO_SOURCE_ADDRESS='************' # first mobile operator source address
MTS_LOGIN='************' # second mobile operator login
MTS_PASSWORD='************' # second mobile operator password
MTS_NAME='************' # second mobile operator name
SMS_TEXT='************' # text of the SMS message
```

### Run project:

```
python sms_bot.py
```

## Run project in Docker:

### Copy docker-compose.yml file to your folder:

### Create .env file with the contents as described above

### Run the following command:

```
docker-compose up -d

```

## Stack: Python 3, requests, dotenv, telegram, logging, Docker

## Author: Sergey Storozhuk
