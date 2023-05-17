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
            context.chat_data['score'] += 10
            username = update.effective_user.username
            self.bot.edit_message_text(chat_id=query.message.chat_id, message_id=query.message.message_id, text='Correct, @{}!'.format(username))
        else:
            self.bot.edit_message_text(chat_id=query.message.chat_id, message_id=query.message.message_id, text='Incorrect. The correct answer is {}.'.format(correct_answer))
        context.chat_data['question_index'] += 1
        if context.chat_data['question_index'] < len(context.chat_data['questions']):
            time.sleep(10)
            self.ask_question(update, context)
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

    def score(self, update, context):
        if 'score' in context.chat_data:
            score = context.chat_data['score']
            num_questions = len(context.chat_data['questions'])
            self.bot.send_message(chat_id=update.effective_chat.id, text='Your score is {}/{}'.format(score, num_questions))
        else:
            self.bot.send_message(chat_id=update.effective_chat.id, text='No quiz in progress.')

    def highscores(self, update, context):
        high_scores = self.get_high_scores()
        if len(high_scores) == 0:
            self.bot.send_message(chat_id=update.effective_chat.id, text='No high scores yet.')
        else:
            high_scores_text = 'High scores:\n\n'
            for i, high_score in enumerate(high_scores[:10]):
                high_scores_text += '{}. {}: {}\n'.format(i+1, high_score['username'], high_score['score'])
            self.bot.send_message(chat_id=update.effective_chat.id, text=high_scores_text)

    def leaderboard(self, update, context):
        high_scores = self.get_high_scores()
        leaderboard = {}
        for high_score in high_scores:
            username = high_score['username']
            score = high_score['score']
            if username in leaderboard:
                leaderboard[username] += score
            else:
                leaderboard[username] = score
        sorted_leaderboard = sorted(leaderboard.items(), key=operator.itemgetter(1), reverse=True)
        leaderboard_text = 'Leaderboard:\n\n'
        for i, (username, score) in enumerate(sorted_leaderboard[:10]):
            leaderboard_text += '{}. {}: {}\n'.format(i+1, username, score)
        self.bot.send_message(chat_id=update.effective_chat.id, text=leaderboard_text)

    def end(self, update, context):
        if 'score' in context.chat_data:
            del context.chat_data['score']
        if 'question_index' in context.chat_data:
            del context.chat_data['question_index']
        if 'questions' in context.chat_data:
            del context.chat_data['questions']
        self.bot.send_message(chat_id=update.effective_chat.id, text='Quiz ended.')

    def next_question(self, update, context):
        if context.chat_data['question_index'] < len(context.chat_data['questions']):
            time.sleep(10)
            self.ask_question(update, context)
        else:
            self.end_quiz(update, context)

    def get_high_scores(self):
        try:
            with open('high_scores.json', 'r') as f:
                high_scores = json.load(f)
        except FileNotFoundError:
            high_scores = []
        return high_scores

    def save_score(self, chat_id, score):
        username = self.bot.get_chat(chat_id).username
        high_scores = self.get_high_scores()
        high_scores.append({'username': username, 'score': score})
        high_scores = sorted(high_scores, key=lambda x: x['score'], reverse=True)
        with open('high_scores.json', 'w') as f:
            json.dump(high_scores, f)

    def shuffle_questions(self, questions):
        return sorted(questions, key=lambda x: x['question'])

    def run(self):
        self.updater.start_polling()
        self.updater.idle()

if __name__ == '__main__':
    # Replace YOUR_TOKEN with your Telegram Bot API token
    bot = QuizBot(YOUR_TOKEN)
    bot.run()
