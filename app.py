from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import telebot
from telebot import types
from datetime import datetime
import os

TOKEN = os.environ.get("API_TOKEN")
URL = 'https://api.telegram.org/bot' + TOKEN + '/'


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL',
                                                       'postgres+psycopg2://postgres:postgres@localhost:5432/homework')

db = SQLAlchemy(app)

bot = telebot.TeleBot(TOKEN)

SUBJECTS = ['Вышка', 'Англ', 'ООП', 'Дискретка', 'Физика', 'ОГТИ', 'АиП']

# HOME KEYBOARD
HOME_MARKUP = types.ReplyKeyboardMarkup(resize_keyboard=True)
item1 = types.KeyboardButton("Текущее дз")
item2 = types.KeyboardButton("Прошлое дз")
item3 = types.KeyboardButton("Ссылочки")

HOME_MARKUP.add(item1, item2)
HOME_MARKUP.add(item3)

# CURRENT SUBJECTS KEYBOARD
CURRENT_SUBJECTS_MARKUP = types.ReplyKeyboardMarkup(resize_keyboard=True)
for subj in SUBJECTS:
    CURRENT_SUBJECTS_MARKUP.add(types.KeyboardButton(subj))

# LAST SUBJECTS KEYBOARD
LAST_SUBJECTS_MARKUP = types.ReplyKeyboardMarkup(resize_keyboard=True)
for subj in SUBJECTS:
    LAST_SUBJECTS_MARKUP.add(types.KeyboardButton(subj + "'"))

# LECTURES' LINKS KEYBOARD
LINKS_MARKUP = types.ReplyKeyboardMarkup(resize_keyboard=True)
for subj in SUBJECTS:
    if subj != 'АиП' and subj != 'ОГТИ':
        LINKS_MARKUP.add(types.KeyboardButton(subj + ' практика'))
    if subj != 'Англ' and subj != 'Физика':
        LINKS_MARKUP.add(types.KeyboardButton(subj + ' лекция'))


class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(40), nullable=False)
    text = db.Column(db.String(200), nullable=False)
    post_link = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False)


class Link(db.Model):
    __tablename__ = 'links'
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String, nullable=False)
    link = db.Column(db.String, nullable=False)
db.create_all()


def get_date(date: int):
    time = datetime.utcfromtimestamp(date)
    formatted_time = time.strftime("%Y-%m-%d")
    return formatted_time


def send_homework(chat_id, subject):
    index = -1
    # if subject has ' sign, we take pre last element
    if subject[-1] == "'":
        subject = subject[:-1]
        index = -2
    subject = subject.lower()
    all_homework = db.session.query(Task).filter_by(subject=subject).all()
    if all_homework:
        try:
            homework = all_homework[index]
            message = f"{homework.subject.upper()}\n\n{homework.text}\nДоп-инфа: {homework.post_link}\n{homework.date}"
        except IndexError:
            message = "Sorry, I don't have this homework yet. If you think that's an error, write to @voha_shvarc"
    else:
        message = "Sorry, I don't have this homework yet. If you think that's an error, write to @voha_shvarc"
    bot.send_message(chat_id, message, reply_markup=HOME_MARKUP)


def send_link(chat_id, message):
    subject = message.split()[0].lower() + '_' + message.split()[1].lower()
    print(subject)
    link = db.session.query(Link).filter_by(subject=subject).first()
    if link:
        answer = f"{link.subject.upper()}\n\n{link.link}"
    else:
        answer = "Sorry, I don't have a link for this class. If you think that's an error, write to @voha_shvarc"
    bot.send_message(chat_id, answer, reply_markup=HOME_MARKUP)


def add_new_lecture_link(chat_id, message):
    subject, link = message.split()[1:]
    if not db.session.query(Link).filter_by(subject=subject).first():
        new_link = Link(
            subject=subject,
            link=link
        )
        db.session.add(new_link)
        db.session.commit()
        answer = "Lecture's link was successfully added!"
    else:
        answer = "I already have a link for this class. Did you expect to edit instead?(/edit)"
    bot.send_message(chat_id, answer)


def edit_lecture_link(chat_id, message):
    subject, link = message.split()[1:]
    current_entry = db.session.query(Link).filter_by(subject=subject).first()
    if current_entry:
        current_entry.link = link
        db.session.commit()
        answer = "Link was successfully updated!"
    else:
        answer = "I haven't got a link for this lecture. Did you expect to add instead?(/add)"
    bot.send_message(chat_id, answer)


@app.route('/', methods=['GET', 'POST'])
def get_post():
    if request.method == 'POST':
        response = request.get_json()
        print(response)
        # new homework
        try:
            if response['channel_post']['sender_chat']['username'] == "ksDzHelp":  # new homework in channel
                message = response['channel_post']['text']
                task, subject = message.split('#')
                new_homework = Task(
                    subject=subject,
                    text=task,
                    post_link=f"https://t.me/ksDzHelp/{response['channel_post']['message_id']}",
                    date=get_date(response['channel_post']['date'])
                )
                db.session.add(new_homework)
                db.session.commit()

        except KeyError:
            chat_id = response['message']['chat']['id']
            try:
                message = response['message']['text']
            except KeyError:
                message = "photo"
                bot.send_message(chat_id, "You sent me a photo")
            if message == '/start':
                welcome_sticker = open('static/boguch_stick.webp', 'rb')
                bot.send_sticker(chat_id, welcome_sticker)
                bot.send_message(chat_id, f"Где твои монатки, {response['message']['from']['first_name']}?\n"
                                          f"Дается 5 секунд на размышления.", reply_markup=HOME_MARKUP)

            elif message == 'Текущее дз' or message == 'Прошлое дз':
                if message == 'Текущее дз':
                    bot.send_message(chat_id, "Выберите нужный предмет, sir.", reply_markup=CURRENT_SUBJECTS_MARKUP)
                else:
                    bot.send_message(chat_id, "Выберите нужный предмет, sir.", reply_markup=LAST_SUBJECTS_MARKUP)

            elif message == 'Ссылочки':
                bot.send_message(chat_id, "Нахуй оно вам надо, sir? Идите лучше подрочите.", reply_markup=LINKS_MARKUP)

            # if we have ' sign after message, request for last subjects
            elif message in SUBJECTS or message[:-1] in SUBJECTS:
                send_homework(chat_id, message)

            elif 'лекция' in message or 'практика' in message:
                send_link(chat_id, message)

            elif '/add' in message:
                if response['message']['from']['id'] == 647711432 or response['message']['from']['id'] == 683204904:  # admin's id
                    add_new_lecture_link(chat_id, message)
                else:
                    bot.send_message(chat_id, "Sorry, but you don't have a permission for this. "
                                              "If you think, that's an error, write to @voha_shvarc")

            elif '/edit' in message:
                if response['message']['from']['id'] == 647711432 or response['message']['from']['id'] == 683204904:
                    edit_lecture_link(chat_id, message)
                else:
                    bot.send_message(chat_id, "Sorry, but you don't have a permission for this. "
                                              "If you think, that's an error, write to @voha_shvarc")

            else:
                bot.send_message(chat_id,
                                 "Sorry, I don't understand you. If you think, that's an error, write to @voha_shvarc",
                                 reply_markup=HOME_MARKUP)

        return jsonify(response)
    return 'Bot welcomes you!'


if __name__ == '__main__':
    app.run()
