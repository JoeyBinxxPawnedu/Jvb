import json
import operator
import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
import time

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
        user_answer = query.data
        correct_answer = context.chat_data['questions'][context.chat_data['question_index']]['correct_answer']
        if user_answer == correct_answer:
            context.chat_data['score'] += 1
            self.bot.edit_message_text(chat_id=query.message.chat_id, message_id=query.message.message_id, text='Correct!')
        else:
            self.bot.edit_message_text(chat_id=query.message.chat_id, message_id=query.message.message_id, text='Incorrect. The correct answer is {}.'.format(correct_answer))
        context.chat_data['question_index'] += 1
        if context.chat_data['question_index'] < len(context.chat_data['questions']):
            time.sleep(2)
            self.ask_question(update, context)
        else:
            self.end_quiz(update, context)

    def ask_question(self, update, context):
        question = context.chat_data['questions'][context.chat_data['question_index']]['question']
        answer_options = context.chat_data['questions'][context.chat_data['question_index']]['answer_options']
        answer_options_text = '\n'.join(['{}. {}'.format(chr(i+65), option) for i, option in enumerate(answer_options)])
        keyboard = [[InlineKeyboardButton(answer_option, callback_data=answer_option) for answer_option in answer_options]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        self.bot.send_message(chat_id=update.message.chat_id, text=question + '\n' + answer_options_text, reply_markup=reply_markup)

    def end_quiz(self, update, context):
        score = context.chat_data['score']
        num_questions = len(context.chat_data['questions'])
        self.bot.send_message(chat_id=update.message.chat_id, text='Quiz complete! You scored {}/{}.\nUse the /highscores command to see the top scores.'.format(score, num_questions))
        self.save_score(update.message.chat_id, score)

    def score(self, update, context):
        score = context.chat_data['score']
        num_questions = len(context.chat_data['questions'])
        self.bot.send_message(chat_id=update.message.chat_id, text='Your score is {}/{}'.format(score, num_questions))

    def highscores(self, update, context):
        high_scores = self.get_high_scores()
        if len(high_scores) == 0:
            self.bot.send_message(chat_id=update.message.chat_id, text='No high scores yet.')
        else:
            high_scores_text = 'High scores:\n\n'
            for i, high_score in enumerate(high_scores[:10]):
                high_scores_text += '{}. {} - {}\n'.format(i+1, high_score[0], high_score[1])
            self.bot.send_message(chat_id=update.message.chat_id, text=high_scores_text)

    def leaderboard(self, update, context):
        high_scores = self.get_high_scores()
        if len(high_scores) == 0:
            self.bot.send_message(chat_id=update.message.chat_id, text='No high scores yet.')
        else:
            high_scores_text = 'Leaderboard:\n\n'
            for i, high_score in enumerate(high_scores[:10]):
                user = self.bot.get_user(high_score[0])
                if user is not None:
                    high_scores_text += '{}. {} - {}\n'.format(i+1, user.first_name, high_score[1])
            self.bot.send_message(chat_id=update.message.chat_id, text=high_scores_text)

    def end(self, update, context):
        self.bot.send_message(chat_id=update.message.chat_id, text='Quiz ended.')
        context.chat_data.clear()

    def next_question(self, update, context):
        if 'question_index' in context.chat_data:
            context.chat_data['question_index'] += 1
            if context.chat_data['question_index'] < len(context.chat_data['questions']):
                self.ask_question(update, context)
            else:
                self.end_quiz(update, context)
        else:
            self.bot.send_message(chat_id=update.message.chat_id, text='No quiz in progress.')

    def get_high_scores(self):
        try:
            with open('high_scores.json', 'r') as f:
                high_scores = json.load(f)
        except:
            high_scores = {}
        return sorted(high_scores.items(), key=operator.itemgetter(1), reverse=True)

    def save_score(self, chat_id, score):
        try:
            with open('high_scores.json', 'r') as f:
                high_scores = json.load(f)
        except:
            high_scores = {}
        high_scores[str(chat_id)] = score
        with open('high_scores.json', 'w') as f:
            json.dump(high_scores, f)

    def shuffle_questions(self, questions):
        return sorted(questions, key=lambda x: x['question'])

    def run(self):
        self.updater.start_polling()
        self.updater.idle()

if __name__ == '__main__':
    # Replace YOUR_TOKEN_HERE with your actual bot token
    bot = QuizBot(token='6135605220:AAGID1bjlBbWbV0DckTLW5WX0C_tOtWj_K8')
    bot.run()
