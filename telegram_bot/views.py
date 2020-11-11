import json
import os
import requests
import numpy as np
from django.http import JsonResponse
from django.views import View
import datetime as date

from .models import telegram_bot_collection

TELEGRAM_URL = "https://api.telegram.org/bot"
TUTORIAL_BOT_TOKEN = "1233503709:AAE4fJsZTy2_AVtXOlOywOX_M18HbIonoEQ"


# https://api.telegram.org/bot<token>/setWebhook?url=<url>/webhooks/tutorial/
class TutorialBotView(View):
    def post(self, request, *args, **kwargs):
        t_data = json.loads(request.body)
        print(t_data)
        t_message = {}
        # If it's a normal message
        if "message" in t_data:
            t_message = t_data["message"]
        # If it's a editted message
        else:
            t_message = t_data["edited_message"]
        t_chat = t_message["chat"]
        cmd = ""

        try:
            text = t_message["text"].strip().lower()
        except Exception as e:
            return JsonResponse({"ok": "POST request processed"})

        # If the message it's a command
        cmd_time = -1
        if text[0] == "/":
            text = text.lstrip("/")
            cmd = text.split()
            if len(cmd) == 1:
                cmd = cmd[0]
            elif len(cmd) == 2:
                cmd_time = cmd[1]
                cmd = cmd[0]

        #Normal message
        else:
            text = text.lstrip("/")

        # Obtain data from DB
        chat = telegram_bot_collection.find_one({"chat_id": t_chat["id"]})

        # If DB doesn't contain the chat id
        if not chat:
            chat = {
                "chat_id": t_chat["id"],
                "added_commands":{},
                "group_members":{},
                "words": {},
                "chars": {},
                "all_words": {},
                "messages": {},
                "last_message": ""
            }
            response = telegram_bot_collection.insert_one(chat)
            # we want chat obj to be the same as fetched from collection
            chat["_id"] = response.inserted_id
        
        else:
            words = []
            for i in text.split():                
                if cmd == "" and i in chat["added_commands"] and i not in words:
                    words.append(i)
                    self.send_message(chat["added_commands"][i], t_chat["id"])

        if cmd == "add":
            text = text.split()
            values = text[1].split("=")
            if values[0] in chat["added_commands"] and len(values) == 2:
                new_resp = {values[0]: values[1]}
                chat["added_commands"].update(new_resp)
                msg = f"The function {values[0]} was changed to {values[1]}"
                telegram_bot_collection.save(chat)
            elif values[0] not in chat["added_commands"] and len(values) == 2:
                chat["added_commands"][values[0]] = values[1]
                msg = f"Command: {values[0]} added to bot!"
                telegram_bot_collection.save(chat)
            else:  
                msg = f"Incorrect format of command: {values[0]}! \nThe correct format is /add commandName=commandValue"
            self.send_message(msg, t_chat["id"])

        elif cmd == "":
            dateObtained = date.date.today()
            if str(t_message["from"]["id"]) not in chat["group_members"]:
                user_stats = {
                    str(dateObtained): {
                        "n_messages": 1,
                        "n_characters": len(text)
                    },
                    "last_talked": str(dateObtained)
                }
                chat["group_members"][str(t_message["from"]["id"])] = user_stats
                telegram_bot_collection.save(chat)
            elif str(t_message["from"]["id"]) in chat["group_members"]:
                
                if str(dateObtained) not in chat["group_members"][str(t_message["from"]["id"])]:
                    user_stats = {
                        str(dateObtained): {
                            "n_messages": 1,
                            "n_characters": len(text)
                        },
                        "last_talked": str(dateObtained)
                    }
                    chat["group_members"][str(t_message["from"]["id"])] = user_stats
                    telegram_bot_collection.save(chat)
                else:
                    user_stats = {
                        str(dateObtained): {
                            "n_messages": chat["group_members"][str(t_message["from"]["id"])][str(dateObtained)]["n_messages"] + 1,
                            "n_characters": chat["group_members"][str(t_message["from"]["id"])][str(dateObtained)]["n_characters"] + len(text)
                        },
                        "last_talked": str(dateObtained)
                    }
                    chat["group_members"][str(t_message["from"]["id"])].update(user_stats)
                    telegram_bot_collection.save(chat)
            if str(dateObtained) not in chat["words"]:
                chat["words"][str(dateObtained)] = 1
                telegram_bot_collection.save(chat)
            else:
                chat["words"].update({str(dateObtained):chat["words"][str(dateObtained)] + 1})
                telegram_bot_collection.save(chat)
            if str(dateObtained) not in chat["chars"]:
                chat["chars"][str(dateObtained)] = len(text)
                telegram_bot_collection.save(chat)
            else:
                chat["chars"].update({str(dateObtained):chat["chars"][str(dateObtained)] + len(text)})
                telegram_bot_collection.save(chat)
            for i in text.split():
                if i not in chat["all_words"]:
                    chat["all_words"][i] = 1
                else:
                    chat["all_words"].update({i: chat["all_words"][i] + 1})
                telegram_bot_collection.save(chat)
            if text not in chat["messages"]:
                chat["messages"][text] = 1
                telegram_bot_collection.save(chat)
            else:
                chat["messages"].update({text: chat["messages"][text] + 1})
                telegram_bot_collection.save(chat)
            chat.update({"last_message": text})
            telegram_bot_collection.save(chat)

        elif cmd == "q2":
            most_messages = -1
            user_q2 = []
            if cmd_time == -1:
                time_searched = 7
            else:
                time_searched = cmd_time
            for i in chat["group_members"]:
                for q in range(time_searched):
                    searched_date = str(date.date.today()-date.timedelta(days=q))
                    if searched_date in chat["group_members"][i]:
                        if chat["group_members"][i][searched_date]["n_messages"] > most_messages:
                            user_q2 = [i]
                            most_messages = chat["group_members"][i][searched_date]["n_messages"]
                        elif hat["group_members"][i][searched_date]["n_messages"] == most_messages:
                            user_q2.append(i)
            if len(user_q2)==1:
                msg = f"The user with most messages is {user_q2[0]} with {most_messages}"
                self.send_message(msg, t_chat["id"])
            else:
                x = " ".join(user_q2)
                msg = f"The users with most messages are {x} with {most_messages}"
                self.send_message(msg, t_chat["id"])

        elif cmd == "q3":
            most_characters = -1
            user_q3 = []
            if cmd_time == -1:
                time_searched = 7
            else:
                time_searched = cmd_time
            for i in chat["group_members"]:
                for q in range(time_searched):
                    searched_date = str(date.date.today()-date.timedelta(days=q))
                    if searched_date in chat["group_members"][i]:
                        if chat["group_members"][i][searched_date]["n_characters"] > most_characters:
                            user_q3 = [i]
                            most_characters = chat["group_members"][i][searched_date]["n_characters"]
                        elif hat["group_members"][i][searched_date]["n_characters"] == most_characters:
                            user_q3.append(i)
            if len(user_q3)==1:
                msg = f"The user with most characters is {user_q3[0]} with {most_characters}"
                self.send_message(msg, t_chat["id"])
            else:
                x = " ".join(user_q3)
                msg = f"The users with most characters are {x} with {most_characters}"
                self.send_message(msg, t_chat["id"])

        elif cmd == "q4":
            if cmd_time == -1:
                time_searched = 7
            else:
                time_searched = cmd_time
            users_innactive = []
            for i in chat["group_members"]:
                last_time_talked = datetime.strptime(chat["group_members"][i]["last_talked"], '%m/%d/%y %H:%M:%S')
                searched_date = str(date.date.today()-date.timedelta(days=time_searched))
                if last_time_talked <= searched_date:
                    users_innactive.append(i)
            if len(users_innactive) > 1:
                x = " ".join(users_innactive)
                msg = f"The users who haven't speaked since {date.timedelta(days=time_searched)} are {x}"
            elif len(users_innactive) == 1:
                msg = f"Only one user haven't speaked since {date.timedelta(days=time_searched)} which is {users_innactive[0]}"
            else:
                msg = f"There are none users who haven't speaked since {date.timedelta(days=time_searched)}"
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
