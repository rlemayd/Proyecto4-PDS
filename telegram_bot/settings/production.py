import os # noqa

from pymongo import MongoClient # noqa

from telegram_bot.settings.base import *  # noqa

DEBUG = True

ALLOWED_HOSTS.append("proyecto-4-rich-kath.herokuapp.com")

# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases
mongodb_user = "rlemayd"
mongodb_password = "test123"
mongodb_host = "cluster0.o8ztz.mongodb.net/cluster0"
MONGO_CLIENT = MongoClient(f"mongodb+srv://{mongodb_user}:{mongodb_password}@{mongodb_host}")

MONGO_DB = MONGO_CLIENT.telegram_bot
