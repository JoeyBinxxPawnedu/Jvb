# -*- coding: utf-8 -*-

import json
import random
import telegram
import time

from telegram.ext import CommandHandler, CallbackQueryHandler, ConversationHandler
from telegram.ext import Updater


class QuizBot:
    def __init__(self, token):
        self.token = token
        self.bot = telegram.Bot(token)
        self.updater = Updater(token, use_context=True)
        self.dispatcher = self.updater.dispatcher
        self.questions = self.load_questions()
        self.score_file = 'scores.json'
        self.leaderboard_size = 10
        self.leaderboard = self.load_leaderboard()

        # Define conversation handlers
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.start)],
            states={
                'quiz': [CallbackQueryHandler(self.answer)],
            },
            fallbacks=[CommandHandler('cancel', self.cancel)]
        )

        # Add handlers to the dispatcher
        self.dispatcher.add_handler(conv_handler)
        self.dispatcher.add_handler(CommandHandler('score', self.show_score))
        self.dispatcher.add_handler(CommandHandler('help', self.help))

    def load_questions(self):
        with open('questions.json', 'r') as f:
            questions = json.load(f)
        return questions

    def load_leaderboard(self):
        try:
            with open(self.score_file, 'r') as f:
                leaderboard = json.load(f)
        except FileNotFoundError:
            leaderboard = {}
        return leaderboard

    def save_leaderboard(self):
        with open(self.score_file, 'w') as f:
            json.dump(self.leaderboard, f)

    def start(self, update, context):
        context.user_data.clear()
        context.chat_data.clear()

        # Ask for the user's name
        self.bot.send_message(chat_id=update.message.chat_id, text='👋 Hi there! What is your name?')
        return 'name'

    def ask_question(self, update, context):
        question = context.chat_data['questions'][context.chat_data['question_index']]
        options = question['options']
        random.shuffle(options)
        reply_markup = telegram.InlineKeyboardMarkup([
            [telegram.InlineKeyboardButton(option, callback_data=option)] for option in options
        ])
        self.bot.send_message(chat_id=update.callback_query.message.chat_id, text=question['question'], reply_markup=reply_markup)

    def answer(self, update, context):
        query = update.callback_query
        user_answer = query.data
        correct_answer = context.chat_data['questions'][context.chat_data['question_index']]['correct_answer']

        # Check if the 'name' key is present in the context.user_data dictionary
        if 'name' not in context.user_data:
            self.start(update, context)

        # Retrieve the user's name and username from the context.user_data dictionary
        name = context.user_data.get('name')
        username = context.user_data.get('username')

        if user_answer == correct_answer:
            context.chat_data['score'] += 10
            self.bot.edit_message_text(chat_id=query.message.chat_id, message_id=query.message.message_id, text='✅  Yes, {}{}!'.format(name, ' @' + username if username else ''))
        else:
            self.bot.edit_message_text(chat_id=query.message.chat_id, message_id=query.message.message_id, text='❌ The correct answer is *{}*.'.format(correct_answer), parse_mode=telegram.ParseMode.MARKDOWN)

        context.chat_data['question_index'] += 1
        if context.chat_data['question_index'] < len(context.chat_data['questions']):
            time.sleep(2)
            self.ask_question(update, context)
        elif update.callback_query is not None:
            self.end_quiz(update, context)
            return ConversationHandler.END
        else:
            return ConversationHandler.END


    def end_quiz(self, update, context):
        score = context.chat_data['score']
        name = context.user_data.get('name')
        username = context.user_data.get('username')

        # Add the user's score to the leaderboard
        if name is not None:
            if username is not None:
                user_identifier = f"{name} (@{username})"
            else:
                user_identifier = name
            if user_identifier not in self.leaderboard:
                self.leaderboard[user_identifier] = score
            else:
                self.leaderboard[user_identifier] = max(self.leaderboard[user_identifier], score)
            self.save_leaderboard()

        # Show the user's score
        self.bot.send_message(chat_id=update.callback_query.message.chat_id, text=f'🎉 Congratulations {name}! You scored {score} points.')

    def show_score(self, update, context):
        # Show the top scores on the leaderboard
        if bool(self.leaderboard):
            sorted_leaderboard = sorted(self.leaderboard.items(), key=lambda x: x[1], reverse=True)
            leaderboard_text = '🏆 *Leaderboard* 🏆\n\n'
            for i, (user, score) in enumerate(sorted_leaderboard[:self.leaderboard_size]):
                leaderboard_text += f'{i+1}. {user}: {score}\n'
            self.bot.send_message(chat_id=update.message.chat_id, text=leaderboard_text, parse_mode=telegram.ParseMode.MARKDOWN)
        else:
            self.bot.send_message(chat_id=update.message.chat_id, text='🏆 *Leaderboard* 🏆\n\nNo scores yet.', parse_mode=telegram.ParseMode.MARKDOWN)

    def help(self, update, context):
        help_text = 'Welcome to the Quiz Bot! Here are the available commands:\n\n'
        help_text += '/start - Start the quiz\n'
        help_text += '/score - Show the top scores on the leaderboard\n'
        help_text += '/help - Show this help message\n'
        self.bot.send_message(chat_id=update.message.chat_id, text=help_text, parse_mode=telegram.ParseMode.MARKDOWN)

    def cancel(self, update, context):
        self.bot.send_message(chat_id=update.message.chat_id, text='Quiz cancelled.')
        return ConversationHandler.END

    def run(self):
        self.updater.start_polling()
        self.updater.idle()


if __name__ == '__main__':
    bot_token = 'YOUR_BOT_TOKEN_HERE'
    quiz_bot = QuizBot('6135605220:AAGID1bjlBbWbV0DckTLW5WX0C_tOtWj_K8')
    quiz_bot.run()
