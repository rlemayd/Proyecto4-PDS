import json
import os
import requests
import numpy as np
from django.http import JsonResponse
from django.views import View
import datetime as date
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from email.mime.multipart import  MIMEMultipart
from email.mime.text import MIMEText
from smtplib import SMTP

from .models import telegram_bot_collection

TELEGRAM_URL = "https://api.telegram.org/bot"
TUTORIAL_BOT_TOKEN = "1233503709:AAE4fJsZTy2_AVtXOlOywOX_M18HbIonoEQ"


# https://api.telegram.org/bot<token>/setWebhook?url=<url>/webhooks/tutorial/
class TutorialBotView(View):
    def createPlot(self, data, searched, dayOrUser, xlabel, fig):
        dates = list(data.keys())
        msg = list(data.values())
        plt.clf()
        plt.figure()
        plt.bar(range(len(data)),msg,tick_label=dates)
        plt.title(f"Number of {searched} per {dayOrUser}")
        plt.xlabel(f"{xlabel}")
        plt.ylabel("Quantity")
        plt.savefig(f'{fig}.png')

    def createCloudPlot(self, data):
        wc = WordCloud(background_color="white",width=1000,height=1000,relative_scaling=0.5,normalize_plurals=False).generate_from_frequencies(data)
        plt.clf()
        plt.figure()
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
            if "@proyecto_4_rich_kath_bot" in text:
                text = text.replace("@proyecto_4_rich_kath_bot","")
            text = text.lstrip("/")
            cmd = text.split()
            if len(cmd) == 1:
                cmd = cmd[0]
            elif len(cmd) == 2 and cmd[0] == "add":
                cmd_time = cmd[1]
                cmd = cmd[0]
            elif cmd[0] == "add":
                cmd_time = " ".join(cmd[1:])
                cmd = cmd[0]
            elif len(cmd) == 2 and cmd[0] != "last_message" and cmd[0] != "add":
                if cmd[1].isnumeric():
                    cmd_time = int(cmd[1])
                else:
                    msg = "You didn't give the quantity of days to search for in the correct format, so we'll replace it by the default value (7 days)..."
                    self.send_message(msg, t_chat["id"])
                cmd = cmd[0]
            elif len(cmd) == 2 and cmd[0] == "last_message":
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
            if cmd_time == -1:
                msg = f"Incorrect format of command add \nThe correct format is /add \[commandName]=\[commandValue]"
            else:
                values = cmd_time.split("=")
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
                    msg = f"Incorrect format of command: {values[0]}! \nThe correct format is /add \[commandName]=\[commandValue]"
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

            if str(dateObtained) not in chat["all_words"]:
                for i in text.split():
                    if str(dateObtained) not in chat["all_words"]:
                        chat["all_words"][str(dateObtained)] = {i : 1}
                    else:
                        if i not in chat["all_words"][str(dateObtained)]:
                            chat["all_words"][str(dateObtained)][i] = 1
                        else:
                            chat["all_words"][str(dateObtained)].update({i: chat["all_words"][str(dateObtained)][i] + 1})
                telegram_bot_collection.save(chat)
            else:
                for i in text.split():
                    if i in chat["all_words"][str(dateObtained)]:
                        chat["all_words"][str(dateObtained)].update({i:chat["all_words"][str(dateObtained)][i] + 1})
                    else:
                        chat["all_words"][str(dateObtained)][str(i)] = 1
                telegram_bot_collection.save(chat)

            if str(dateObtained) not in chat["messages"]:
                chat["messages"][str(dateObtained)] = {text : 1}
                telegram_bot_collection.save(chat)
            else:
                if text in chat["messages"][str(dateObtained)]:
                    chat["messages"][str(dateObtained)].update({text:chat["messages"][str(dateObtained)][text] + 1})
                else:
                    chat["messages"][str(dateObtained)][text] = 1
                telegram_bot_collection.save(chat)

            chat.update({"last_message": text})
            telegram_bot_collection.save(chat)

        elif cmd == "most_messages":
            user_q2 = {}
            if cmd_time == -1:
                time_searched = 7
            else:
                time_searched = cmd_time
            for i in chat["group_members"]:
                for q in range(time_searched + 1):
                    searched_date = str(date.date.today()-date.timedelta(days=q))
                    if searched_date in chat["group_members"][i]:
                        if i in user_q2:
                            user_q2[i] += chat["group_members"][i][searched_date]["n_messages"]
                        else:
                            user_q2[i] = chat["group_members"][i][searched_date]["n_messages"]
                
            if len(user_q2) != 0:
                itemMaxValue = max(user_q2.items(), key=lambda x: x[1])
                listOfKeys = list()
                for key, value in user_q2.items():
                    if value == itemMaxValue[1]:
                        listOfKeys.append(key)
                if len(listOfKeys)==1:
                    x = self.get_user(t_chat["id"], listOfKeys[0])
                    msg = f"The user with most messages since {searched_date} is {x} with {itemMaxValue[1]}"
                    self.send_message(msg, t_chat["id"])
                else:
                    x = ""
                    for i in listOfKeys:
                        x += self.get_user(t_chat["id"], i) + ", "
                    msg = f"The users with most messages since {searched_date} are {x} with {itemMaxValue[1]}"
                    self.send_message(msg, t_chat["id"])
            else:
                msg = f"No user has spoken for {time_searched} days"
                self.send_message(msg, t_chat["id"])

        elif cmd == "most_characters":
            user_q3 = {}
            if cmd_time == -1:
                time_searched = 7
            else:
                time_searched = cmd_time
            for i in chat["group_members"]:
                for q in range(time_searched + 1):
                    searched_date = str(date.date.today()-date.timedelta(days=q))
                    if searched_date in chat["group_members"][i]:
                        if i in user_q3:
                            user_q3[i] += chat["group_members"][i][searched_date]["n_characters"]
                        else:
                            user_q3[i] = chat["group_members"][i][searched_date]["n_characters"]
                
            if len(user_q3) != 0:
                itemMaxValue = max(user_q3.items(), key=lambda x: x[1])
                listOfKeys = list()
                for key, value in user_q3.items():
                    if value == itemMaxValue[1]:
                        listOfKeys.append(key)
                if len(listOfKeys)==1:
                    x = self.get_user(t_chat["id"], listOfKeys[0])
                    msg = f"The user with most characters since {searched_date} is {x} with {itemMaxValue[1]}"
                    self.send_message(msg, t_chat["id"])
                else:
                    x = ""
                    for i in listOfKeys:
                        x += self.get_user(t_chat["id"], i) + ", "
                    msg = f"The users with most characters since {searched_date} are {x} with {itemMaxValue[1]}"
                    self.send_message(msg, t_chat["id"])
            else:
                msg = f"No user has spoken for {time_searched} days"
                self.send_message(msg, t_chat["id"])

        elif cmd == "absent_user":
            if cmd_time == -1:
                time_searched = 7
            else:
                time_searched = cmd_time
            users_innactive = []
            for i in chat["group_members"]:
                last_time_talked = date.datetime.strptime(chat["group_members"][i]["last_talked"], '%Y-%m-%d')
                searched_date = date.date.today()-date.timedelta(days=time_searched)
                searched_date = date.datetime.strptime(str(searched_date), '%Y-%m-%d')
                if last_time_talked < searched_date:
                    users_innactive.append(self.get_user(t_chat["id"], i))
            if len(users_innactive) > 1:
                x = ", ".join(users_innactive)
                msg = f"The users who haven't speaked since {searched_date.date()} are {x}"
            elif len(users_innactive) == 1:
                msg = f"Only one user haven't speaked since {searched_date.date()} which is {users_innactive[0]}"
            else:
                msg = f"There are none users who haven't speaked since {searched_date.date()}"
            self.send_message(msg, t_chat["id"])

        elif cmd== "messages_per_day":
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

        elif cmd== "characters_per_day":
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

        elif cmd== "messages_per_user":
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

        elif cmd== "characters_per_user":
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

        elif cmd== "word_cloud":
            if cmd_time == -1:
                time_searched = 7
            else:
                time_searched = cmd_time
            words = {}
            for i in chat["all_words"]:
                date_in_loop = date.datetime.strptime(i, '%Y-%m-%d')
                searched_date = date.date.today()-date.timedelta(days=time_searched)
                searched_date = date.datetime.strptime(str(searched_date), '%Y-%m-%d')
                if date_in_loop >= searched_date:
                    for t in chat["all_words"][i]:
                        if t in words:
                            words[t] += chat["all_words"][i][t]
                        else:
                            words[t] = chat["all_words"][i][t]
            self.createCloudPlot(words)
            self.send_photo(open('Clouds.png','rb'),t_chat["id"])

        elif cmd == "popular_message":
            if cmd_time == -1:
                time_searched = 7
            else:
                time_searched = cmd_time
            message = {}
            for i in chat["messages"]:
                date_in_loop = date.datetime.strptime(i, '%Y-%m-%d')
                searched_date = date.date.today()-date.timedelta(days=time_searched)
                searched_date = date.datetime.strptime(str(searched_date), '%Y-%m-%d')
                if date_in_loop >= searched_date:
                    for t in chat["messages"][i]:
                        if t in message:
                            message[t] += chat["messages"][i][t]
                        else:
                            message[t] = chat["messages"][i][t]

            mx_tuple = max(message.items(),key = lambda x:x[1]) 
            max_list =[i[0] for i in message.items() if i[1]==mx_tuple[1]]

            if len(max_list) > 1:
                x = ", ".join(max_list)
                msg = f"The most popular messages since {searched_date.date()} are {x}"
            elif len(max_list) == 1:
                msg = f"The most popular message since {searched_date.date()} is {max_list[0]}"
            else:
                msg = f"There are none most popular messages since {searched_date.date()}"
            self.send_message(msg, t_chat["id"])
        
        elif cmd == "last_message":
            if cmd_time == -1:
                msg = "Email not given"
            else:
                response = requests.get("https://isitarealemail.com/api/email/validate",params = {'email': cmd_time})
                status = response.json()['status']

                if status == "valid":
                    message = MIMEMultipart()
                    message["From"] = "proyecto.4.richard.katherine@gmail.com"
                    message["To"] = cmd_time
                    message["Subject"] = "Último mensaje recibido por bot"
                    body = "Hola! Mi nombre es proyecto-4-richard-katherine! \n\nTe escribo para comentarte que me pidieron que te envie un mail para enviarte el último mensaje que he recibido\nEs por esto que el último mensaje que he recibido fue \"" + chat["last_message"] + "\".\n\n\nEspero te sea de útilidad este mail.\n\nSaludos!!"
                    body = MIMEText(body)
                    message.attach(body)
                    smtp = SMTP("smtp.gmail.com")
                    smtp.starttls()
                    smtp.login("proyecto.4.richard.katherine@gmail.com","proyecto4")
                    smtp.sendmail("proyecto.4.richard.katherine@gmail.com", cmd_time, message.as_string())
                    smtp.quit()
                    msg = "Mail was successfully sent"

                elif status == "invalid":
                    msg = "Email doesn't exist"

                else:
                    msg = "Email doesn't exist"
            self.send_message(msg, t_chat["id"])

        elif cmd == "help":
            msg = """I can help you analyze and get statistics of your groups!.\nThe commands that contain \[] needs to be given to work\n<days> is an optional param, if it's not given it's replaced by 7 days.\nYou can control me by sending these commands:\n
/add \[commandName]=\[commandValue] - To answer a specific word or phrase when i receive a certain word.\n
/most\_messages <days> - Obtain the user with most messages from a specific date.\n
/most\_characters <days> - Obtain the user with most characters sent from a specific date.\n
/absent\_user <days> - Obtain the user who have not written messages in a period from a specific date.\n
/messages\_per\_day <days> - Obtain a graph with the number of messages per day from a specific date.\n
/characters\_per\_day <days> - Obtain a graph with the number of characters per day from a specific date.\n
/messages\_per\_user <days> - Obtain a graph with the number of messages per user from a specific date.\n
/characters\_per\_user <days> - Obtain a graph with the number of characters per user from a specific date.\n
/word\_cloud <days> - Obtain a word cloud with all messages from a specific date.\n
/popular\_message <days> - Obtain the most popular message from a specific date.\n
/last\_message \[Email] - Email the last message received."""
            
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