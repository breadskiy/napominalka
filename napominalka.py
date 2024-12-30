import logging
import asyncio
import time
import re
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ConversationHandler
from datetime import datetime

# Включаем логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен моего бота
TOKEN = '7187385834:AAF5ZZLTG2xUBNdkm4HRMCvvPl6VWwBwUrY'

# Состояния
WAITING_FOR_REMINDER = 1

class ReminderBot:
    def __init__(self, token):
        self.reminders = {}  # Словарь для хранения напоминаний для каждого пользователя
        self.application = ApplicationBuilder().token(token).build()

        # Обработчик команды /start
        self.application.add_handler(CommandHandler('start', self.start))

        # Обработчик команды /add
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('add', self.add_reminder)],
            states={ 
                WAITING_FOR_REMINDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.receive_reminder)]
            },
            fallbacks=[]
        )
        self.application.add_handler(conv_handler)

        # Обработчик команды /show
        self.application.add_handler(CommandHandler('show', self.show_reminders))

    async def start(self, update: Update, context):
        await update.message.reply_text('Привет! Я бот-напоминалка. Используй /add для добавления напоминания.')

    async def add_reminder(self, update: Update, context):
        await update.message.reply_text('Введите напоминание в формате: <сообщение> <дд.мм.гггг чч:мм>.')
        return WAITING_FOR_REMINDER  # Переходим в состояние ожидания

    async def receive_reminder(self, update: Update, context):
        message_text = update.message.text.strip()

        # Используем регулярное выражение для разделения сообщения и времени
        match = re.search(r"(.+)\s(\d{2}\.\d{2}\.\d{4}\s\d{2}:\d{2})$", message_text)

        if not match:
            await update.message.reply_text('Неверный формат. Используйте: <сообщение> <дд.мм.гггг чч:мм>.')
            return WAITING_FOR_REMINDER

        # Извлекаем сообщение и дату/время
        message = match.group(1).strip()
        time_str = match.group(2).strip()
        chat_id = update.message.chat_id

        try:
            # Конвертируем дату и время в timestamp
            remind_time = datetime.strptime(time_str, '%d.%m.%Y %H:%M').timestamp()

            # Сохраняем напоминание
            self.reminders.setdefault(chat_id, []).append((message, remind_time))

            # Планируем напоминание
            delay = remind_time - time.time()
            if delay > 0:
                asyncio.create_task(self.schedule_reminder(chat_id, message, delay))
                await update.message.reply_text(f'Напоминание "{message}" добавлено на {time_str}.')
            else:
                await update.message.reply_text('Указанное время уже прошло. Пожалуйста, выберите более позднее время.')
        except ValueError:
            await update.message.reply_text('Ошибка при обработке даты. Проверьте формат: <дд.мм.гггг чч:мм>.')
            return WAITING_FOR_REMINDER

        return ConversationHandler.END

    async def show_reminders(self, update: Update, context):
        chat_id = update.message.chat_id
        current_time = time.time()
        
        if chat_id not in self.reminders or not self.reminders[chat_id]:
            await update.message.reply_text('Нет напоминаний.')
            return

        reminders_text = '\n'.join(
            f'{message} в {self.format_time(remind_time)}'
            for message, remind_time in self.reminders[chat_id] if remind_time > current_time
        )
        
        if reminders_text:
            await update.message.reply_text(f'Список напоминаний:\n{reminders_text}')
        else:
            await update.message.reply_text('Нет актуальных напоминаний.')

    async def schedule_reminder(self, chat_id, message, delay):
        await asyncio.sleep(delay)
        current_time = time.time()

        # Удаляем напоминание из словаря
        self.reminders[chat_id] = [rem for rem in self.reminders[chat_id] if rem[1] > current_time]

        # Отправляем напоминание
        await self.application.bot.send_message(chat_id=chat_id, text=f'Напоминание: {message}')

    def format_time(self, timestamp):
        # Форматируем время в формат "дд.мм.гггг чч:мм"
        return datetime.fromtimestamp(timestamp).strftime('%d.%m.%Y %H:%M')

    def start_bot(self):
        self.application.run_polling()

if __name__ == '__main__':
    bot = ReminderBot(TOKEN)
    bot.start_bot()