import json
import os
import requests
import numpy as np
from django.http import JsonResponse
from django.views import View
import datetime as date
import matplotlib.pyplot as plt
from wordcloud import WordCloud

from .models import telegram_bot_collection

TELEGRAM_URL = "https://api.telegram.org/bot"
TUTORIAL_BOT_TOKEN = "1233503709:AAE4fJsZTy2_AVtXOlOywOX_M18HbIonoEQ"


# https://api.telegram.org/bot<token>/setWebhook?url=<url>/webhooks/tutorial/
class TutorialBotView(View):
    def createPlot(self, data, searched, dayOrUser, xlabel, fig):
        dates = list(data.keys())
        msg= list(data.values())
        plt.clf()
        plt.bar(range(len(data)),msg,tick_label=dates)
        plt.title(f"Number of {searched} per {dayOrUser}")
        plt.xlabel(f"{xlabel}")
        plt.ylabel("Quantity")
        plt.savefig(f'{fig}.png')

    def createCloudPlot(self, data):
        wc = WordCloud(background_color="white",width=1000,height=1000,relative_scaling=0.5,normalize_plurals=False).generate_from_frequencies(data)
        plt.clf()
        plt.imshow(wc)
        plt.axis("off")
        plt.tight_layout(pad = 0)
        plt.savefig('Clouds.png')

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
                cmd_time = int(cmd[1])
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
                            "n_messages": 1,
                            "n_characters": len(text)
                        }
                    chat["group_members"][str(t_message["from"]["id"])][str(dateObtained)] = user_stats
                    chat["group_members"][str(t_message["from"]["id"])].update({"last_talked": str(dateObtained)})
                    telegram_bot_collection.save(chat)

                        
                else:
                    user_stats = {
                            "n_messages": chat["group_members"][str(t_message["from"]["id"])][str(dateObtained)]["n_messages"] + 1,
                            "n_characters": chat["group_members"][str(t_message["from"]["id"])][str(dateObtained)]["n_characters"] + len(text)
                        }
                    chat["group_members"][str(t_message["from"]["id"])][str(dateObtained)].update(user_stats)
                    chat["group_members"][str(t_message["from"]["id"])].update({"last_talked": str(dateObtained)})
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
            user_q2 = {}
            if cmd_time == -1:
                time_searched = 7
            else:
                time_searched = cmd_time
            for i in chat["group_members"]:
                for q in range(time_searched):
                    searched_date = str(date.date.today()-date.timedelta(days=q))
                    if searched_date in chat["group_members"][i]:
                        if i in user_q2:
                            user_q2[i] += chat["group_members"][i][searched_date]["n_messages"]
                        else:
                            user_q2[i] = chat["group_members"][i][searched_date]["n_messages"]
            itemMaxValue = max(user_q2.items(), key=lambda x: x[1])
            listOfKeys = list()
            for key, value in user_q2.items():
                if value == itemMaxValue[1]:
                    listOfKeys.append(key)
            if len(listOfKeys)==1:
                x = self.get_user(t_chat["id"], listOfKeys[0])
                msg = f"The user with most messages is {x} with {itemMaxValue[1]}"
                self.send_message(msg, t_chat["id"])
            else:
                x = ""
                for i in listOfKeys:
                    x += self.get_user(t_chat["id"], i) + ", "
                msg = f"The users with most messages are {x} with {itemMaxValue[1]}"
                self.send_message(msg, t_chat["id"])

        elif cmd == "q3":
            user_q3 = {}
            if cmd_time == -1:
                time_searched = 7
            else:
                time_searched = cmd_time
            for i in chat["group_members"]:
                for q in range(time_searched):
                    searched_date = str(date.date.today()-date.timedelta(days=q))
                    if searched_date in chat["group_members"][i]:
                        if i in user_q3:
                            user_q3[i] += chat["group_members"][i][searched_date]["n_characters"]
                        else:
                            user_q3[i] = chat["group_members"][i][searched_date]["n_characters"]
            itemMaxValue = max(user_q3.items(), key=lambda x: x[1])
            listOfKeys = list()
            for key, value in user_q3.items():
                if value == itemMaxValue[1]:
                    listOfKeys.append(key)
            if len(listOfKeys)==1:
                x = self.get_user(t_chat["id"], listOfKeys[0])
                msg = f"The user with most characters is {x} with {itemMaxValue[1]}"
                self.send_message(msg, t_chat["id"])
            else:
                x = ""
                for i in listOfKeys:
                    x += self.get_user(t_chat["id"], i) + ", "
                msg = f"The users with most characters are {x} with {itemMaxValue[1]}"
                self.send_message(msg, t_chat["id"])

        elif cmd == "q4":
            if cmd_time == -1:
                time_searched = 7
            else:
                time_searched = cmd_time
            users_innactive = []
            for i in chat["group_members"]:
                last_time_talked = date.datetime.strptime(chat["group_members"][i]["last_talked"], '%Y-%m-%d')
                searched_date = date.date.today()-date.timedelta(days=time_searched)
                searched_date = date.datetime.strptime(str(searched_date), '%Y-%m-%d')
                if last_time_talked <= searched_date:
                    users_innactive.append(i)
            if len(users_innactive) > 1:
                x = ", ".join(users_innactive)
                msg = f"The users who haven't speaked since {searched_date.date()} are {x}"
            elif len(users_innactive) == 1:
                msg = f"Only one user haven't speaked since {searched_date.date()} which is {users_innactive[0]}"
            else:
                msg = f"There are none users who haven't speaked since {searched_date.date()}"
            self.send_message(msg, t_chat["id"])

        elif cmd== "q5":
            if cmd_time == -1:
                time_searched = 7
            else:
                time_searched = cmd_time
            messages_per_day = {}
            for i in chat["group_members"]:
                for t in chat["group_members"][i]:
                    if t != "last_talked":
                        date_in_loop = date.datetime.strptime(t, '%Y-%m-%d')
                        searched_date = date.date.today()-date.timedelta(days=time_searched)
                        searched_date = date.datetime.strptime(str(searched_date), '%Y-%m-%d')
                        if date_in_loop >= searched_date:
                            if t in messages_per_day:
                                messages_per_day[t] += chat["group_members"][i][t]["n_messages"]
                            else:
                                messages_per_day[t] = chat["group_members"][i][t]["n_messages"]
        
            self.createPlot(messages_per_day, "messages", "day", "Dates", "MessagesPerDay")
            self.send_photo(open('MessagesPerDay.png','rb'),t_chat["id"])

        elif cmd== "q6":
            if cmd_time == -1:
                time_searched = 7
            else:
                time_searched = cmd_time
            chars_per_day = {}
            for i in chat["group_members"]:
                for t in chat["group_members"][i]:
                    if t != "last_talked":
                        date_in_loop = date.datetime.strptime(t, '%Y-%m-%d')
                        searched_date = date.date.today()-date.timedelta(days=time_searched)
                        searched_date = date.datetime.strptime(str(searched_date), '%Y-%m-%d')
                        if date_in_loop >= searched_date:
                            if t in chars_per_day:
                                chars_per_day[t] += chat["group_members"][i][t]["n_characters"]
                            else:
                                chars_per_day[t] = chat["group_members"][i][t]["n_characters"]
            
            self.createPlot(chars_per_day, "characters", "day", "Dates", "CharactersPerDay")
            self.send_photo(open('CharactersPerDay.png','rb'),t_chat["id"])

        elif cmd== "q7":
            if cmd_time == -1:
                time_searched = 7
            else:
                time_searched = cmd_time
            messages_per_user = {}
            for i in chat["group_members"]:
                for t in chat["group_members"][i]:
                    if t != "last_talked":
                        date_in_loop = date.datetime.strptime(t, '%Y-%m-%d')
                        searched_date = date.date.today()-date.timedelta(days=time_searched)
                        searched_date = date.datetime.strptime(str(searched_date), '%Y-%m-%d')
                        if date_in_loop >= searched_date:
                            user = self.get_user(t_chat["id"], i)
                            if user in messages_per_user:
                                messages_per_user[user] += chat["group_members"][i][t]["n_messages"]
                            else:
                                messages_per_user[user] = chat["group_members"][i][t]["n_messages"]
        
            self.createPlot(messages_per_user, "messages", "user", "Users", "MessagesPerUser")
            self.send_photo(open('MessagesPerUser.png','rb'),t_chat["id"])

        elif cmd== "q8":
            if cmd_time == -1:
                time_searched = 7
            else:
                time_searched = cmd_time
            chars_per_user = {}
            for i in chat["group_members"]:
                for t in chat["group_members"][i]:
                    if t != "last_talked":
                        date_in_loop = date.datetime.strptime(t, '%Y-%m-%d')
                        searched_date = date.date.today()-date.timedelta(days=time_searched)
                        searched_date = date.datetime.strptime(str(searched_date), '%Y-%m-%d')
                        if date_in_loop >= searched_date:
                            user = self.get_user(t_chat["id"], i)
                            if user in chars_per_user:
                                chars_per_user[user] += chat["group_members"][i][t]["n_characters"]
                            else:
                                chars_per_user[user] = chat["group_members"][i][t]["n_characters"]
        
            self.createPlot(chars_per_user, "characters", "user", "Users", "CharsPerUser")
            self.send_photo(open('CharsPerUser.png','rb'),t_chat["id"])

        elif cmd== "q9":
            if cmd_time == -1:
                time_searched = 7
            else:
                time_searched = cmd_time
            words = {}
            for i in chat["all_words"]:
                words[i] = chat["all_words"][i]
            self.createCloudPlot(words)
            self.send_photo(open('Clouds.png','rb'),t_chat["id"])

        elif cmd == "q10":
            max_qty = -1
            message = []
            for i in chat["messages"]:
                if chat["messages"][i] > max_qty:
                    max_qty = chat["messages"][i]
                    message = [i]
                elif chat["messages"][i] == max_qty:
                    message.append(i)
            if len(message) == 1:
                msg = f"The most popular message is \"{message[0]}\""
            elif len(message) > 1:
                msg = f"The most popular messages are \"{" ,".join(message)}\""
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

    @staticmethod
    def send_photo(photo, chat_id):
        data = {
            "chat_id": chat_id
        }
        body = {
            "photo": photo
        }
        response = requests.post(
            f"{TELEGRAM_URL}{TUTORIAL_BOT_TOKEN}/sendPhoto", data=data, files=body
        )

    @staticmethod
    def get_user(chat_id, user_id):
        data = {
            "chat_id": chat_id,
            "user_id": user_id
        }
        response = requests.get(
            f"{TELEGRAM_URL}{TUTORIAL_BOT_TOKEN}/getChatMember", data=data
        )
        response = response.json()
        user = response["result"]["user"]["first_name"] + " " + response["result"]["user"]["last_name"]
        return user