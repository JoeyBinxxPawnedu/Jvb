import json
import operator
import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, filters, CallbackQueryHandler
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
            self.bot.edit_message_text(chat_id=query.message.chat_id, message_id=query.message.message_id, text='✅ Yes, {}{}!'.format(context.user_data['name'], ' ' + username if username else ''))
        else:
            self.bot.edit_message_text(chat_id=query.message.chat_id, message_id=query.message.message_id, text='❌ The correct answer is *{}*.'.format(correct_answer), parse_mode=telegram.ParseMode.MARKDOWN)
        context.chat_data['question_index'] += 1
        if context.chat_data['question_index'] < len(context.chat_data['questions']):
            time.sleep(20)
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
        self.bot.send_message(chat_id=update.effective_chat.id, text='Quiz complete! You scored {}/{}.'.format(score, num_questions))
        self.save_score(update.effective_user.id, score)
        del context.chat_data['score']
        del context.chat_data['question_index']
        del context.chat_data['questions']

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
            high_scores_text = '\n'.join(['🏅 {} ({}) - {} points'.format(score['name'], score['username'], score['score']) for score in high_scores])
            self.bot.send_message(chat_id=update.effective_chat.id, text='High scores:\n{}'.format(high_scores_text))

    def leaderboard(self, update, context):
        high_scores = self.get_high_scores()
        if len(high_scores) == 0:
            self.bot.send_message(chat_id=update.effective_chat.id, text='No high scores yet.')
        else:
            sorted_high_scores = sorted(high_scores, key=operator.itemgetter('score'), reverse=True)
            leaderboard_text = '\n'.join(['{}. {} (@{}) - {} points'.format(i+1, score['name'], score['username'], score['score']) for i, score in enumerate(sorted_high_scores)])
            self.bot.send_message(chat_id=update.effective_chat.id, text='Leaderboard:\n{}'.format(leaderboard_text))

    def get_high_scores(self):
        with open('scores.json', 'r') as f:
            high_scores = json.load(f)
        return high_scores

    def save_score(self, user_id, score):
        with open('scores.json', 'r+') as f:
            high_scores = json.load(f)
            for user in high_scores:
                if user['id'] == user_id:
                    user['score'] += score
                    break
            else:
                user_data = {'id': user_id, 'name': update.effective_user.first_name, 'username': update.effective_user.username, 'score': score}
                high_scores.append(user_data)
            f.seek(0)
            json.dump(high_scores, f)

    def shuffle_questions(self, questions):
        return sorted(questions, key=lambda x: x['question'])

    def end(self, update, context):
        self.bot.send_message(chat_id=update.effective_chat.id, text='Quiz ended. Thanks for playing!')

    def next_question(self, update, context):
        if 'question_index' in context.chat_data:
            context.chat_data['question_index'] += 1
            if context.chat_data['question_index'] < len(context.chat_data['questions']):
                self.ask_question(update, context)
            else:
                self.end_quiz(update, context)
        else:
            self.bot.send_message(chat_id=update.effective_chat.id, text='No quiz in progress.')

if __name__ == '__main__':
    with open('token.txt', 'r') as f:
        token = f.read().strip()
    bot = QuizBot(token)
    bot.updater.start_polling()
