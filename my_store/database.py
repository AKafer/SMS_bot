import os
from peewee import *
import logging
from logging import config as logging_config

from dotenv import load_dotenv

from my_store import conf

load_dotenv()

logging_config.dictConfig(conf.LOGGING)
logger = logging.getLogger("sms_bot")


db = PostgresqlDatabase(
    database=os.getenv('POSTGRES_DB'),
    user=os.getenv('POSTGRES_USER'),
    password=os.getenv('POSTGRES_PASSWORD'),
    host=os.getenv('DB_HOST'),
    port=os.getenv('DB_PORT')
)


class Client(Model):
    phone = CharField(primary_key=True)
    name = CharField(null=True)

    class Meta:
        database = db


class Message(Model):
    client = ForeignKeyField(Client, backref='messages')
    created_at = DateTimeField()
    last_demand_date = CharField(null=True)
    status = CharField(null=True)
    sms_id = CharField(null=True)
    error_reason = CharField(null=True)
    tried_times = IntegerField(default=0)

    class Meta:
        database = db


# db initialization
db.connect()
db.create_tables([Client, Message])
db.close()

logger.info('Database initialized')
