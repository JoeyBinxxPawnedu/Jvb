import json
import operator
import random
import telegram
import os
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, JobQueue, JobContext

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
        user_answer = query.data
        correct_answer = context.chat_data['questions'][context.chat_data['question_index']]['correct_answer']
        user_name = update.effective_user.first_name

        if user_answer == correct_answer:
            context.chat_data['score'] += 10
            self.bot.edit_message_text(chat_id=query.message.chat_id, message_id=query.message.message_id,
                                       text='✅ Yes, correct!\n\n🏅 {} +10 points'.format(user_name))
        else:
            self.bot.edit_message_text(chat_id=query.message.chat_id, message_id=query.message.message_id,
                                       text='❌ Incorrect. The correct answer is {}.'.format(correct_answer))

        context.chat_data['question_index'] += 1
        if context.chat_data['question_index'] < len(context.chat_data['questions']):
            job_queue = self.updater.job_queue
            job_queue.run_once(self.ask_next_question, 10, context={'update': update, 'chat_data': context.chat_data})
        else:
            self.end_quiz(update, context)

    def ask_question(self, update, context):
        question = context.chat_data['questions'][context.chat_data['question_index']]['question']
        answer_options = context.chat_data['questions'][context.chat_data['question_index']]['answer_options']
        answer_options_text = '\n'.join(['{}. {}'.format(chr(i+65), option) for i, option in enumerate(answer_options)])
        keyboard = [[InlineKeyboardButton(answer_option, callback_data=answer_option) for answer_option in answer_options]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        self.bot.send_message(chat_id=update.effective_chat.id, text=question + '\n' + answer_options_text, reply_markup=reply_markup)

    def end_quiz(self, update, context):
        score = context.chat_data['score']
        num_questions = len(context.chat_data['questions'])
        self.bot.send_message(chat_id=update.effective_chat.id, text='Quiz complete! You scored {}/{}.\nUse the /highscores command to see the top scores.'.format(score, num_questions))
        self.save_score(update.effective_user.id, score)

    def ask_next_question(self, context: JobContext):
        update = context.job.context['update']
        chat_data = context.job.context['chat_data']
        self.ask_question(update, chat_data)

    def score(self, update, context):
        score = context.chat_data.get('score', 0)
        self.bot.send_message(chat_id=update.effective_chat.id, text='Your current score is {}.'.format(score))

    def highscores(self, update, context):
        highscores = self.get_highscores()
        sorted_highscores = sorted(highscores.items(), key=operator.itemgetter(1), reverse=True)
        highscores_text = '\n'.join(['{}: {}'.format(user_id, score) for user_id, score in sorted_highscores])
        self.bot.send_message(chat_id=update.effective_chat.id, text='Highscores:\n{}'.format(highscores_text))

    def leaderboard(self, update, context):
        highscores = self.get_highscores()
        sorted_highscores = sorted(highscores.items(), key=operator.itemgetter(1), reverse=True)
        top_scores = sorted_highscores[:10]
        leaderboard_text = '\n'.join(['{}. {}: {}'.format(i + 1, user_id, score) for i, (user_id, score) in enumerate(top_scores)])
        self.bot.send_message(chat_id=update.effective_chat.id, text='🏆 Leaderboard:\n{}'.format(leaderboard_text))

    def end(self, update, context):
        score = context.chat_data.get('score', 0)
        self.bot.send_message(chat_id=update.effective_chat.id, text='Quiz ended. Your final score is {}.'.format(score))
        self.save_score(update.effective_user.id, score)

    def next_question(self, update, context):
        context.chat_data['question_index'] += 1
        if context.chat_data['question_index'] < len(context.chat_data['questions']):
            self.ask_question(update, context)
        else:
            self.end_quiz(update, context)

    def shuffle_questions(self, questions):
        shuffled_questions = random.sample(questions, len(questions))
        for question in shuffled_questions:
            random.shuffle(question['answer_options'])
        return shuffled_questions

    def save_score(self, user_id, score):
        highscores = self.get_highscores()
        if user_id not in highscores or score > highscores[user_id]:
            highscores[user_id] = score
            with open('highscores.json', 'w') as f:
                json.dump(highscores, f)

    def get_highscores(self):
        if os.path.exists('highscores.json'):
            with open('highscores.json', 'r') as f:
                return json.load(f)
        return {}

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
