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
        self.dispatcher.add_handler(CommandHandler('/', self.help))

    def load_questions(self):
        with open('questions.json', 'r') as f:
            questions = json.load(f)
        return questions

    def load_leaderboard(self):
        try:
            with open(self.score_file, 'r') as f:
                leaderboard = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            leaderboard = []
        return leaderboard

    def save_score(self, name, username, score):
        # Create a new score entry
        entry = {
            'name': name,
            'username': username,
            'score': score,
            'answers': 0
        }

        # Check if the user's score is already in the leaderboard
        for i, user_score in enumerate(self.leaderboard):
            if user_score['name'] == name and user_score['username'] == username:
                if score > user_score['score']:
                    self.leaderboard[i]['score'] = score
                break
        else:
            # Add the user's score to the leaderboard
            self.leaderboard.append(entry)

        # Sort the leaderboard by score in descending order
        self.leaderboard.sort(key=lambda x: x['score'], reverse=True)

        # Truncate the leaderboard to the desired size
        self.leaderboard = self.leaderboard[:self.leaderboard_size]

        # Save the leaderboard to a file
        with open(self.score_file, 'w') as f:
            json.dump(self.leaderboard, f, indent=4)

    def get_high_scores(self):
        try:
            with open(self.score_file, 'r') as f:
                high_scores = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            high_scores = []
        return high_scores

    def start(self, update, context):
        context.user_data['name'] = update.message.from_user.first_name
        context.user_data['username'] = update.message.from_user.username
        context.chat_data['score'] = 0
        context.chat_data['questions'] = random.sample(self.questions, 5)
        context.chat_data['question_index'] = 0

        self.bot.send_message(chat_id=update.message.chat_id, text='Welcome to the quiz, {}!'.format(context.user_data['name']))
        self.ask_question(update, context)

        return 'quiz'

    def ask_question(self, update, context):
        question = context.chat_data['questions'][context.chat_data['question_index']]
        options = question['answer_options']
        random.shuffle(options)

        reply_markup = telegram.InlineKeyboardMarkup([
            [telegram.InlineKeyboardButton(text=option, callback_data=option)] for option in options
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
        else:
            self.end_quiz(update, context)

    def end_quiz(self, update, context):
        score = context.chat_data['score']
        name = context.user_data.get('name')
        username = context.user_data.get('username')
        self.save_score(name, username, score)

        high_scores = self.get_high_scores()
        if high_scores:
            text = '🎉 Global ranking\n'
            for i, user_score in enumerate(high_scores):
                medal = ''
                if i == 0:
                    medal = '🥇'
                elif i == 1:
                    medal = '🥈'
                elif i == 2:
                    medal = '🥉'

                text += '{} {}. {}   {} points (answers: {})\n'.format(medal, i+1, user_score['name'], user_score['score'], user_score['answers'])

            self.bot.send_message(chat_id=update.callback_query.message.chat_id, text=text, parse_mode=telegram.ParseMode.MARKDOWN)
        else:
            self.bot.send_message(chat_id=update.callback_query.message.chat_id, text='No high scores yet!')

        return ConversationHandler.END

    def cancel(self, update, context):
        self.bot.send_message(chat_id=update.message.chat_id, text='Quiz cancelled.')
        return ConversationHandler.END

    def show_score(self, update, context):
        high_scores = self.get_high_scores()
        if high_scores:
            text = '🎉 Global ranking\n'
            for i, user_score in enumerate(high_scores):
                medal = ''
                if i == 0:
                    medal = '🥇'
                elif i == 1:
                    medal = '🥈'
                elif i == 2:
                    medal = '🥉'

                text += '{} {}. {}   {} points (answers: {})\n'.format(medal, i+1, user_score['name'], user_score['score'], user_score['answers'])

            self.bot.send_message(chat_id=update.message.chat_id, text=text, parse_mode=telegram.ParseMode.MARKDOWN)
        else:
            self.bot.send_message(chat_id=update.message.chat_id, text='No high scores yet!')

    def help(self, update, context):
        text = 'Use /start to start the quiz, and /score to view the high scores.'
        self.bot.send_message(chat_id=update.message.chat_id, text=text)

if __name__ == '__main__':
    # Replace YOUR_TOKEN_HERE with your actual bot token
    bot = QuizBot('6135605220:AAGID1bjlBbWbV0DckTLW5WX0C_tOtWj_K8')
    bot.updater.start_polling()
    bot.updater.idle()
