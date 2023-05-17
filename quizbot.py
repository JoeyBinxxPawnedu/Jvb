import json
import operator
import random
import telegram
import os
import logging
import time
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class QuizBot:
    def __init__(self, token):
        self.bot = telegram.Bot(token=token)
        self.updater = Updater(token=token, use_context=True)
        self.dispatcher = self.updater.dispatcher

        # Load the questions from the questions.json file
        with open('questions.json', 'r') as f:
            self.questions = json.load(f)

        # Register the handlers
        self.register_handlers()

    def register_handlers(self):
        self.dispatcher.add_handler(CommandHandler('start', self.start))
        self.dispatcher.add_handler(CallbackQueryHandler(self.answer))
        self.dispatcher.add_handler(CommandHandler('score', self.score))
        self.dispatcher.add_handler(CommandHandler('highscores', self.highscores))
        self.dispatcher.add_handler(CommandHandler('leaderboard', self.leaderboard))
        self.dispatcher.add_handler(CommandHandler('end', self.end))
        self.dispatcher.add_handler(CommandHandler('next', self.next_question))

    def start(self, update, context):
        context.chat_data['score'] = 0
        context.chat_data['question_index'] = 0
        context.chat_data['questions'] = self.shuffle_questions(self.questions)
        self.ask_question(update, context)

    def answer(self, update, context):
        query = update.callback_query
        query.answer()

        correct_answer = context.chat_data['questions'][context.chat_data['question_index']]['correct_answer']
        if query.data == correct_answer:
            context.chat_data['score'] += 1
            query.edit_message_text(text="Correct! 🎉 Your score: {}".format(context.chat_data['score']))
        else:
            query.edit_message_text(text="Sorry, that's incorrect. 😞")

        context.chat_data['question_index'] += 1
        if context.chat_data['question_index'] < len(context.chat_data['questions']):
            self.next_question(update, context)
        else:
            self.end_quiz(update, context)

    def ask_question(self, update, context):
        question = context.chat_data['questions'][context.chat_data['question_index']]['question']
        answer_options = context.chat_data['questions'][context.chat_data['question_index']]['answer_options']
        answer_options_text = '\n'.join(['{}. {}'.format(chr(i+65), option) for i, option in enumerate(answer_options)])
        keyboard = [[InlineKeyboardButton(answer_option, callback_data=answer_option) for answer_option in answer_options]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = self.bot.send_message(chat_id=update.effective_chat.id, text=question + '\n' + answer_options_text, reply_markup=reply_markup)

        # Wait for 20 seconds
        time.sleep(20)

        # End the question
        self.end_question(update, context, message)

    def end_question(self, update, context, message):
        # Edit the message text to "time out"
        self.bot.edit_message_text(chat_id=message.chat_id, message_id=message.message_id, text='⏰ Time out!')

        # Move to the next question
        context.chat_data['question_index'] += 1
        if context.chat_data['question_index'] < len(context.chat_data['questions']):
            self.ask_question(update, context)
        else:
            self.end_quiz(update, context)

    def next_question(self, update, context):
        self.ask_question(update, context)

    def score(self, update, context):
        update.message.reply_text("Your current score is: {}".format(context.chat_data['score']))

    def highscores(self, update, context):
        # Implement highscore functionality here
        pass

    def leaderboard(self, update, context):
        # Implement leaderboard functionality here
        pass

    def end_quiz(self, update, context):
        update.effective_message.reply_text("Congratulations! You've completed the quiz. Your final score is {}.".format(context.chat_data['score']))

    def end(self, update, context):
        self.end_quiz(update, context)

    def shuffle_questions(self, questions):
        shuffled_questions = random.sample(questions, len(questions))
        for question in shuffled_questions:
            random.shuffle(question['answer_options'])
        return shuffled_questions

    def run(self):
        self.updater.start_polling()
        self.updater.idle()


if __name__ == '__main__':
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
   if token:
        quiz_bot = QuizBot(token)
        quiz_bot.run()
    else:
        print("Error: TELEGRAM_BOT_TOKEN environment variable not found. Please set it and run the script again.")
