import json
import os
import requests
from django.http import JsonResponse
from django.views import View

from .models import telegram_bot_collection

TELEGRAM_URL = "https://api.telegram.org/bot"
TUTORIAL_BOT_TOKEN = "1233503709:AAE4fJsZTy2_AVtXOlOywOX_M18HbIonoEQ"


# https://api.telegram.org/bot<token>/setWebhook?url=<url>/webhooks/tutorial/
class TutorialBotView(View):
    def post(self, request, *args, **kwargs):
        t_data = json.loads(request.body)
        t_message = t_data["message"]
        t_chat = t_message["chat"]

        try:
            text = t_message["text"].strip().lower()
        except Exception as e:
            return JsonResponse({"ok": "POST request processed"})
        if text[0] == "/":
            text = text.lstrip("/")
            cmd = text.split()[0]
        else:
            text = text.lstrip("/")
        chat = telegram_bot_collection.find_one({"chat_id": t_chat["id"]})

        if not chat:
            chat = {
                "chat_id": t_chat["id"]
            }
            response = telegram_bot_collection.insert_one(chat)
            # we want chat obj to be the same as fetched from collection
            chat["_id"] = response.inserted_id
        
        else:
            if chat[text]:
                print(chat[text])
                self.send_message(chat[text], t_chat["id"])

        if cmd == "add":
            values = text[1].split("=")
            chat[values[0]] = values[1]
            telegram_bot_collection.save(chat)
            msg = f"Command: {values[0]} added to bot!"
            self.send_message(msg, t_chat["id"])
        elif text == "restart":
            blank_data = {"counter": 0}
            chat.update(blank_data)
            telegram_bot_collection.save(chat)
            msg = "The Tutorial bot was restarted"
            self.send_message(msg, t_chat["id"])
        else:
            msg = "Unknown command"
            self.send_message(msg, t_chat["id"])

        return JsonResponse({"ok": "POST request processed"})

    @staticmethod
    def send_message(message, chat_id):
        data = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown",
        }
        response = requests.post(
            f"{TELEGRAM_URL}{TUTORIAL_BOT_TOKEN}/sendMessage", data=data
        )
