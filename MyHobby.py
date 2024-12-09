import telebot
from telebot import types
from collections import defaultdict
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import io
import matplotlib
matplotlib.use('Agg')


def get_hours_declension(hours):
    if hours % 10 == 1 and hours % 100 != 11:
        return f"{hours} час"
    elif hours % 10 in [2, 3, 4] and hours % 100 not in [12, 13, 14]:
        return f"{hours} часа"
    else:
        return f"{hours} часов"


class BotMyHobby:
    def __init__(self, token):
        self.bot = telebot.TeleBot(token)
        self.user_states = {}   # словарь для хранения стека состояний пользователей
        self.guitar_activity_tracker = GuitarActivityTracker(self.bot)
        self.setup_handlers()

    def setup_handlers(self):
        self.bot.message_handler(commands=['start'])(self.startBot)
        self.bot.message_handler(commands=['guitar_stats'])(self.guitar_activity_tracker.send_guitar_stats)
        self.bot.callback_query_handler(func=lambda call: True)(self.handle_callback)
        self.bot.message_handler(func=lambda message: True)(self.handle_message)

    def startBot(self, message):
        first_mess = (f'<b>{message.from_user.first_name}</b>, привет!\nЭто бот для хобби! Чтобы помочь тебе найти что-то, '
                      f'мне нужно знать, чем ты увлекаешься :)')
        markup = types.InlineKeyboardMarkup()
        button_guitar = types.InlineKeyboardButton(text='Гитара🎸', callback_data='guitar')
        markup.add(button_guitar)
        button_stats = types.InlineKeyboardButton(text='Статистика', callback_data='stats')
        markup.add(button_stats)
        self.bot.send_message(message.chat.id, first_mess, parse_mode='html', reply_markup=markup)

    def handle_callback(self, function_call):
        if function_call.message:
            chat_id = function_call.message.chat.id
            if chat_id not in self.user_states:
                self.user_states[chat_id] = []  # инициализация стека состояний для нового пользователя

            if function_call.data == 'guitar':
                guitar = Guitar(self.bot)
                guitar.handle_guitar(function_call.message)
                self.user_states[chat_id].append('guitar')  # добавление состояния в стек
            elif function_call.data == 'chords':
                guitar = Guitar(self.bot)
                guitar.send_chords(function_call.message)
                self.user_states[chat_id].append('chords')
            elif function_call.data == 'fights':
                guitar = Guitar(self.bot)
                guitar.send_fights(function_call.message)
                self.user_states[chat_id].append('fights')
            elif function_call.data == 'back':
                if self.user_states[chat_id]:
                    previous_state = self.user_states[chat_id].pop()  # извлечение предыдущего состояния из стека
                    if previous_state == 'guitar':
                        self.startBot(function_call.message)  # возврат к начальному состоянию
                    elif previous_state == 'chords':
                        guitar = Guitar(self.bot)
                        guitar.handle_guitar(function_call.message)  # возврат к состоянию "guitar"
                    elif previous_state == 'fights':
                        guitar = Guitar(self.bot)
                        guitar.handle_guitar(function_call.message)
                else:
                    self.startBot(function_call.message)  # возврат к начальному состоянию, если стек пуст
            elif function_call.data == 'stats':
                self.send_stats_menu(function_call.message)
            elif function_call.data == 'mark_today':
                self.bot.send_message(chat_id, "Сколько часов ты занимался сегодня? (укажите число)")
                self.user_states[chat_id].append('mark_today')
            elif function_call.data == 'show_stats':
                self.guitar_activity_tracker.send_guitar_stats(function_call.message)
            elif function_call.data == 'show_graph':
                self.guitar_activity_tracker.send_guitar_graph(function_call.message)

            try:
                self.bot.answer_callback_query(function_call.id)
            except telebot.apihelper.ApiTelegramException as e:
                if "query is too old" in str(e):
                    pass  # игнорировать ошибку, если запрос слишком старый
                else:
                    raise e  # поднять другие ошибки

    def handle_message(self, message):
        chat_id = message.chat.id
        if chat_id in self.user_states and self.user_states[chat_id] and self.user_states[chat_id][-1] == 'mark_today':
            try:
                hours = float(message.text)
                if 0 < hours <= 24:
                    self.guitar_activity_tracker.track_activity(chat_id, hours)
                    self.bot.send_message(chat_id, f"Запись принята: {get_hours_declension(hours)}")
                    self.user_states[chat_id].pop()  # удаление состояния 'mark_today' из стека
                else:
                    self.bot.send_message(chat_id, "Пожалуйста, введите число часов от 1 до 24")
            except ValueError:
                self.bot.send_message(chat_id, "Пожалуйста, введите корректное число часов")

    def send_stats_menu(self, message):
        markup = types.InlineKeyboardMarkup()
        button_mark_today = types.InlineKeyboardButton(text='Отметить занятие', callback_data='mark_today')
        markup.add(button_mark_today)
        button_show_stats = types.InlineKeyboardButton(text='Показать статистику', callback_data='show_stats')
        markup.add(button_show_stats)
        button_show_graph = types.InlineKeyboardButton(text='Показать график', callback_data='show_graph')
        markup.add(button_show_graph)
        button_back = types.InlineKeyboardButton("Назад", callback_data='back')
        markup.add(button_back)
        self.bot.send_message(message.chat.id, 'Выберите опцию:', reply_markup=markup)

    def start_polling(self):
        self.bot.infinity_polling()     # бот будет работать пока файл запущен


class GuitarActivityTracker:
    def __init__(self, bot):
        self.bot = bot
        self.guitar_activities = defaultdict(dict)  # словарь для хранения занятий гитарой

    def track_activity(self, chat_id, hours):
        today = datetime.now().date()
        if today in self.guitar_activities[chat_id]:
            self.guitar_activities[chat_id][today] += hours
        else:
            self.guitar_activities[chat_id][today] = hours

    def send_guitar_stats(self, message):
        chat_id = message.chat.id
        if chat_id in self.guitar_activities:
            stats_mess = 'Ваша статистика занятий гитарой:\n'
            for date, hours in sorted(self.guitar_activities[chat_id].items()):
                stats_mess += f'{date}: {get_hours_declension(hours)}\n'
        else:
            stats_mess = 'Вы еще не отслеживали свои занятия гитарой'
        self.bot.send_message(chat_id, stats_mess)

    def send_guitar_graph(self, message):
        chat_id = message.chat.id
        if chat_id in self.guitar_activities:
            dates, hours = zip(*sorted(self.guitar_activities[chat_id].items()))
            plt.figure(figsize=(10, 5))
            plt.plot(dates, hours, marker='o')
            plt.xlabel('Дата')
            plt.ylabel('Часы')
            plt.title('Статистика занятий гитарой')
            plt.xticks(rotation=45)
            plt.tight_layout()

            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            self.bot.send_photo(chat_id, buf)
            plt.close()
        else:
            self.bot.send_message(chat_id, 'Вы еще не отслеживали свои занятия гитарой')


class Guitar:
    def __init__(self, bot):
        self.bot = bot

    def handle_guitar(self, message):
        second_mess = 'Отлично! Хочешь найти какой-нибудь аккорд, бой или песню?'
        markup = types.InlineKeyboardMarkup()
        button_chords = types.InlineKeyboardButton("Аккорды", callback_data='chords')
        markup.add(button_chords)
        button_fight = types.InlineKeyboardButton("Бои", callback_data='fights')
        markup.add(button_fight)
        button_songs = types.InlineKeyboardButton("Песни", url='https://454.amdm.ru/')
        markup.add(button_songs)
        button_back = types.InlineKeyboardButton("Назад", callback_data='back')
        markup.add(button_back)
        self.bot.send_message(message.chat.id, second_mess, reply_markup=markup)

    def send_chords(self, message):
        chords_mess = ('На фотографии представлены основные аккорды. С их помощью можно сыграть любую песню, '
                        'а если нужно изменить тональность – используй каподастр '
                        '\nЕсли тебе нужны другие аккорды, нажми на кнопку "Другие аккорды"👇\n'+
                        '\nЕсли хочешь узнать больше теории про аккорды, нажми на кнопку "Теория"'+
                        '\nЕсли ты впервые держишь в руках гитару, и ещё не знаешь, как ставить аккорды, '
                        'нажми на кнопку "Видео"')
        markup = types.InlineKeyboardMarkup()
        button_chords_link = types.InlineKeyboardButton('Другие аккорды', url='https://www.5lad.ru/applikatury/')
        markup.add(button_chords_link)
        button_chords_theory = types.InlineKeyboardButton('Теория', url='https://musiconshop.ru/vidy-i-tipy-akkordov')
        markup.add(button_chords_theory)
        button_chords_video = types.InlineKeyboardButton('Видео', url='https://www.youtube.com/watch?v=VahPPwUc8QI')
        markup.add(button_chords_video)
        button_back = types.InlineKeyboardButton("Назад", callback_data='back')
        markup.add(button_back)
        with open("C:/Users/Nika/PycharmProjects/tgbotHobby/pic/chords.jpg", 'rb') as chords_photo:
            self.bot.send_photo(message.chat.id, chords_photo, caption=chords_mess, reply_markup=markup)

    def send_fights(self, message):
        fights_mess = ('На картинке представлены самые популярные бои.'
                        '\nЕсли тебе нужны другие бои, нажми на кнопку "Другие бои"👇'+
                        '\nЕсли ты впервые держишь в руках гитару, и ещё не знаешь, как играть бои, '
                        'нажми на кнопку "Видео"')
        markup = types.InlineKeyboardMarkup()
        button_fights_link = types.InlineKeyboardButton('Другие бои', url='https://pereborom.ru/boj-na-gitare-12-vidov/')
        markup.add(button_fights_link)
        button_fights_video = types.InlineKeyboardButton('Видео', url='https://www.youtube.com/watch?v=5QbeJyFHEfk')
        markup.add(button_fights_video)
        button_back = types.InlineKeyboardButton("Назад", callback_data='back')
        markup.add(button_back)
        with open("C:/Users/Nika/PycharmProjects/tgbotHobby/pic/fights.jpg", 'rb') as fights_photo:
            self.bot.send_photo(message.chat.id, fights_photo, caption=fights_mess, reply_markup=markup)


if __name__ == "__main__":
    bot_token = '7928918563:AAG6rUHhgCWKAufgVhSjP2R-SaC1UIhfKWU'
    hobby_bot = BotMyHobby(bot_token)
    hobby_bot.start_polling()