from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, ConversationHandler
import os
import sqlite3
from datetime import datetime, timedelta
import pytz
import matplotlib.pyplot as plt
from io import BytesIO
import random

# Подключение к базе данных
conn = sqlite3.connect('tasks.db', check_same_thread=False)
cursor = conn.cursor()

# Создание таблиц для задач и пользователей
cursor.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        task TEXT NOT NULL,
        task_time TEXT NOT NULL,
        completed INTEGER DEFAULT 0
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        timezone_offset INTEGER NOT NULL
    )
''')
conn.commit()

# Состояния для диалога
NAME, TIME = range(2)

# Клавиатура с кнопками
keyboard = ReplyKeyboardMarkup([
    ["📝 Добавить задачу", "📋 Посмотреть задачи"],
    ["📊 Статистика"]
], resize_keyboard=True)

# Цветовая палитра
PRIMARY_COLOR = "#1abc9c"  # Основной цвет (бирюзовый)
SECONDARY_COLOR = "#ecf0f1"  # Вторичный цвет (светло-серый)
ACCENT_COLOR = "#e67e22"  # Акцентный цвет (оранжевый)

# Форматирование текста с использованием HTML и цветов
def format_message(text):
    return f'<b>{text}</b>'

# Список фраз для Анны
greetings = [
    "👋 <b>Привет!</b> Меня зовут Анна, и я стану твоим личным ассистентом 😊",
    "🌟 <b>Приветик!</b> Я рада тебя видеть! Как я могу помочь тебе сегодня?",
    "💫 <b>О, привет!</b> Давай вместе сделаем этот день продуктивным!"
]

task_reminders = [
    "⏰ Через 10 минут нужно {task}. Не забудь, я слежу за тобой 😉",
    "⏰ Эй, через 10 минут начинается задача: {task}. Готов? 🌟",
    "⏰ Напоминаю: через 10 минут нужно {task}. Я верю в тебя! 💪"
]

task_start_messages = [
    "🔥 Эй, ты обещал начать задачу \"{task}\" прямо сейчас! Жду результат 🤨",
    "🔥 Пора действовать! Задача \"{task}\" ждёт тебя! 🚀",
    "🔥 Время пришло! Начинай задачу \"{task}\". Я здесь, чтобы поддержать тебя ❤️"
]

motivational_messages = [
    "🎉 Молодец! Ты справился с задачей! Я горжусь тобой 💪",
    "🌟 Отличная работа! Продолжай в том же духе! 🎯",
    "💪 Ты настоящий чемпион! Давай следующую задачу? 😊"
]

supportive_messages = [
    "💕 Я знаю, что ты устал, но давай попробуем хотя бы одну задачку? Ты сможешь!",
    "❤️ Не переживай, если что-то не получается. Главное — не сдаваться! Я рядом.",
    "🌈 Давай сделаем это вместе! Я верю в тебя! 💪"
]

jokes_and_fun = [
    "🐾 Если забудешь о задаче, я пришлю тебе милого котика вместо напоминания!",
    "☕ Ты уже выполнил 5 задач! Кажется, пора устроить себе перерыв на кофе.",
    "🎮 Хорошая работа! Может, теперь заслужил немного игр? 😉"
]

# Функция для выбора случайной фразы
def get_random_message(messages):
    return random.choice(messages)

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    cursor.execute("SELECT name FROM users WHERE user_id = ?", (user_id,))
    user_data = cursor.fetchone()

    if user_data:
        await update.message.reply_text(
            f"👋 <b>Привет, {user_data[0]}!</b>\n\n"
            "Я рада снова тебя видеть.\n\n"
            "Используй кнопки ниже для управления задачами.",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        return ConversationHandler.END
    else:
        greeting = get_random_message(greetings)
        await update.message.reply_text(
            f"{greeting}\n\n"
            "Как я могу к тебе обращаться? Введи своё имя:",
            parse_mode="HTML"
        )
        return NAME

# Сохранение имени пользователя
async def save_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    name = update.message.text.strip()

    # Сохраняем имя пользователя
    cursor.execute("INSERT INTO users (user_id, name, timezone_offset) VALUES (?, ?, ?)", (user_id, name, 0))
    conn.commit()

    await update.message.reply_text(
        f"<b>🌟 Приятно познакомиться, {name}!</b>\n\n"
        "Сколько у тебя сейчас времени? Введи в формате <code>HH:MM</code> (например, <code>15:30</code>).",
        parse_mode="HTML"
    )
    return TIME

# Сохранение времени пользователя
async def save_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    try:
        user_time = datetime.strptime(update.message.text.strip(), "%H:%M")
        now_utc = datetime.now(pytz.utc)  # Используем timezone-aware объект
        user_time_utc = datetime.now(pytz.utc).replace(hour=user_time.hour, minute=user_time.minute)
        offset = int((user_time_utc - now_utc).total_seconds() // 3600)

        # Обновляем смещение времени
        cursor.execute("UPDATE users SET timezone_offset = ? WHERE user_id = ?", (offset, user_id))
        conn.commit()

        await update.message.reply_text(
            "<b>🚀 Отлично!</b>\n\n"
            "Теперь мы готовы работать вместе.\n\n"
            "Используй кнопки ниже для управления задачами.",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text(
            "❌ Неверный формат времени.\n\n"
            "Попробуй ещё раз. Например: <code>15:30</code>",
            parse_mode="HTML"
        )
        return TIME

# Обработка текстовых сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    user_id = update.effective_user.id

    if text == "📝 Добавить задачу":
        await update.message.reply_text(
            "<b>📝 Добавить задачу:</b>\n\n"
            "Введи задачу и время в формате:\n"
            "<code>[Задача, Время]</code>\n\n"
            "Пример: <code>[Сделать зарядку, 08:30]</code>",
            parse_mode="HTML"
        )
        context.user_data['action'] = 'add_task'
    elif text == "📋 Посмотреть задачи":
        cursor.execute("SELECT id, task, task_time FROM tasks WHERE user_id = ? AND completed = 0", (user_id,))
        tasks = cursor.fetchall()
        if tasks:
            task_list = "\n".join([f"• {id}. {task} <i>({task_time})</i>" for id, task, task_time in tasks])
            keyboard_buttons = [
                [InlineKeyboardButton(f"✅ {id}", callback_data=f"done_{id}"),
                 InlineKeyboardButton(f"🔄 {id}", callback_data=f"reschedule_{id}")] for id, _, _ in tasks
            ]
            reply_markup = InlineKeyboardMarkup(keyboard_buttons)
            await update.message.reply_text(
                f"<b>🌟 Твои задачи:</b>\n"
                f"-------------------\n"
                f"{task_list}\n"
                f"-------------------",
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        else:
            await update.message.reply_text("<b>⚠️ У тебя пока нет задач.</b>", parse_mode="HTML")
    elif text == "📊 Статистика":
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ? AND completed = 1", (user_id,))
        completed_tasks = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ? AND completed = 0", (user_id,))
        pending_tasks = cursor.fetchone()[0]
        total_tasks = completed_tasks + pending_tasks

        progress_bar = generate_progress_bar(completed_tasks, total_tasks)

        image_buffer = generate_progress_image(completed_tasks, pending_tasks)
        await update.message.reply_photo(photo=image_buffer, caption=(
            f"<b>{format_message('📊 Статистика:')}</b>\n"
            f"✅ Выполнено задач: {completed_tasks}\n"
            f"⏳ Ожидают выполнения: {pending_tasks}\n"
            f"🔥 Прогресс: {progress_bar}"
        ), parse_mode="HTML")
    else:
        action = context.user_data.get('action')
        if action == 'add_task':
            try:
                task, task_time = map(str.strip, update.message.text.strip("[]").split(","))
                task_time = task_time.strip()
                # Сохраняем задачу
                cursor.execute("INSERT INTO tasks (user_id, task, task_time) VALUES (?, ?, ?)", (user_id, task, task_time))
                conn.commit()
                await update.message.reply_text(
                    f'<b>{format_message("✔️ Задача добавлена:")}</b> "{task}" на время <i>{task_time}</i>',
                    parse_mode="HTML"
                )
                # Устанавливаем напоминания
                set_reminders(context, user_id, task, task_time)
            except ValueError:
                await update.message.reply_text(
                    "<b>❌ Неверный формат.</b>\n\n"
                    "Введи задачу и время в формате:\n"
                    "<code>[Задача, Время]</code>\n\n"
                    "Пример: <code>[Сделать зарядку, 08:30]</code>",
                    parse_mode="HTML"
                )
            context.user_data['action'] = None

# Генерация ASCII-графика прогресса
def generate_progress_bar(completed_tasks, total_tasks):
    progress = int((completed_tasks / total_tasks) * 10) if total_tasks > 0 else 0
    return f"{'🟩' * progress}{'⬜' * (10 - progress)}"

# Генерация изображения графика прогресса
def generate_progress_image(completed_tasks, pending_tasks):
    labels = ['Выполнено', 'Ожидают']
    sizes = [completed_tasks, pending_tasks]
    colors = ['#1abc9c', '#e67e22']  # Бирюзовый и оранжевый

    plt.figure(figsize=(6, 3))
    plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
    plt.axis('equal')

    buffer = BytesIO()
    plt.savefig(buffer, format='png', facecolor="#ecf0f1")  # Светло-серый фон
    buffer.seek(0)
    plt.close()

    return buffer

# Установка напоминаний
def set_reminders(context: ContextTypes.DEFAULT_TYPE, user_id: int, task: str, task_time: str):
    cursor.execute("SELECT timezone_offset FROM users WHERE user_id = ?", (user_id,))
    offset = cursor.fetchone()[0]

    now = datetime.now(pytz.utc) + timedelta(hours=offset)
    task_datetime = datetime.strptime(task_time, "%H:%M").replace(year=now.year, month=now.month, day=now.day)
    task_datetime = task_datetime.replace(tzinfo=pytz.utc) + timedelta(hours=offset)

    if task_datetime < now:
        task_datetime += timedelta(days=1)  # Если время уже прошло, переносим на завтра

    # Напоминание за 10 минут
    reminder_time_10min = task_datetime - timedelta(minutes=10)
    if task:
        reminder_message = get_random_message(task_reminders).format(task=task.lower())
    else:
        reminder_message = "⏰ Напоминание о задаче!"
    context.job_queue.run_once(
        send_reminder,
        reminder_time_10min - now,
        chat_id=user_id,
        data=f"<b>{reminder_message}</b>"
    )

    # Напоминание в момент начала
    if task:
        start_message = get_random_message(task_start_messages).format(task=task.lower())
    else:
        start_message = "⏰ Пора начинать задачу!"
    context.job_queue.run_once(
        send_reminder,
        task_datetime - now,
        chat_id=user_id,
        data=f"<b>{start_message}</b>"
    )

# Отправка напоминания
async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    await context.bot.send_message(job.chat_id, text=job.data, parse_mode="HTML")

# Отметка задачи как выполненной
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = update.effective_user.id

    if data.startswith("done_"):
        task_id = int(data.split("_")[1])
        cursor.execute("UPDATE tasks SET completed = 1 WHERE id = ?", (task_id,))
        conn.commit()
        motivational_message = get_random_message(motivational_messages)
        await query.edit_message_text(f"<b>{motivational_message}</b>", parse_mode="HTML")

        # Показываем оставшиеся задачи
        cursor.execute("SELECT id, task, task_time FROM tasks WHERE user_id = ? AND completed = 0", (user_id,))
        tasks = cursor.fetchall()
        if tasks:
            task_list = "\n".join([f"• {id}. {task} <i>({task_time})</i>" for id, task, task_time in tasks])
            await update.effective_message.reply_text(
                f"<b>🌟 Оставшиеся задачи:</b>\n"
                f"-------------------\n"
                f"{task_list}\n"
                f"-------------------",
                parse_mode="HTML"
            )
        else:
            joke_or_fun = get_random_message(jokes_and_fun)
            await update.effective_message.reply_text(f"<b>🎉 Все задачи выполнены!</b> {joke_or_fun}", parse_mode="HTML")
    elif data.startswith("reschedule_"):
        task_id = int(data.split("_")[1])
        cursor.execute("SELECT task, task_time FROM tasks WHERE id = ?", (task_id,))
        task, task_time = cursor.fetchone()
        new_task_time = datetime.strptime(task_time, "%H:%M") + timedelta(days=1)
        new_task_time = new_task_time.strftime("%H:%M")
        cursor.execute("UPDATE tasks SET task_time = ? WHERE id = ?", (new_task_time, task_id))
        conn.commit()
        await query.edit_message_text(f"<b>🔄 Задача \"{task}\"</b> перенесена на завтра в <i>{new_task_time}</i>", parse_mode="HTML")

# Основная функция
def main() -> None:
    # Вставь свой API-токен здесь
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise SystemExit("Не задан BOT_TOKEN — положите токен в переменную окружения (.env)")
    # Создание приложения
    application = Application.builder().token(TOKEN).build()

    # Диалог для приветствия
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_name)],
            TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_time)]
        },
        fallbacks=[]
    )

    # Регистрация обработчиков
    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(handle_callback))

    # Запуск бота
    application.run_polling()

if __name__ == "__main__":
    main()