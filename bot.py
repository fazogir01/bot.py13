from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from pytube import YouTube
import instaloader
import requests
from bs4 import BeautifulSoup
import os
import logging
import re

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(name)

# Команда /start
def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        'Привет! Я бот для скачивания контента с YouTube, Instagram и Pinterest.\n'
        'Отправь ссылку на видео (YouTube), пост (Instagram) или пин (Pinterest), и я попробую скачать контент!'
    )

# Обработка YouTube-видео
def download_youtube(update: Update, context: CallbackContext, url: str) -> None:
    chat_id = update.message.chat_id
    try:
        update.message.reply_text("Начинаю загрузку видео с YouTube...")
        yt = YouTube(url)
        stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()

        if not stream:
            update.message.reply_text("Не удалось найти подходящий формат видео!")
            return

        video_file = stream.download(output_path="downloads")
        file_size = os.path.getsize(video_file) / (1024 * 1024)  # Размер в МБ

        if file_size > 50:
            update.message.reply_text(
                f"Видео слишком большое ({file_size:.2f} МБ)! Telegram позволяет отправлять файлы до 1000 МБ."
            )
            os.remove(video_file)
            return

        with open(video_file, 'rb') as video:
            context.bot.send_video(chat_id=chat_id, video=video, supports_streaming=True)
        update.message.reply_text("Видео отправлено!")
        os.remove(video_file)

    except Exception as e:
        logger.error(f"YouTube ошибка: {e}")
        update.message.reply_text(f"Ошибка при скачивании с YouTube: {e}")

# Обработка Instagram-постов
def download_instagram(update: Update, context: CallbackContext, url: str) -> None:
    chat_id = update.message.chat_id
    try:
        update.message.reply_text("Начинаю загрузку поста с Instagram...")
        L = instaloader.Instaloader()

        # Раскомментируйте и укажите логин/пароль для полного доступа
        # L.login("YOUR_INSTAGRAM_USERNAME", "YOUR_INSTAGRAM_PASSWORD")

        # Извлекаем shortcode из URL
        shortcode_match = re.search(r'instagram\.com/(?:p|reel)/([A-Za-z0-9_-]+)', url)
        if not shortcode_match:
            update.message.reply_text("Неверная ссылка на Instagram!")
            return
        shortcode = shortcode_match.group(1)

        post = instaloader.Post.from_shortcode(L.context, shortcode)
        L.download_post(post, target="downloads")
        update.message.reply_text("Пост скачан! Отправляю файлы...")

        for file in os.listdir("downloads"):
            file_path = os.path.join("downloads", file)
            if file.endswith((".jpg", ".mp4")) and os.path.getsize(file_path) / (1024 * 1024) < 50:
                with open(file_path, 'rb') as f:
                    context.bot.send_document(chat_id=chat_id, document=f)
                os.remove(file_path)
            elif os.path.getsize(file_path) / (1024 * 1024) >= 50:
                update.message.reply_text(f"Файл {file} слишком большой для отправки (>50 МБ).")

    except Exception as e:
        logger.error(f"Instagram ошибка: {e}")
        update.message.reply_text(f"Ошибка при скачивании с Instagram: {e}")

# Обработка Pinterest-пинов
def download_pinterest(update: Update, context: CallbackContext, url: str) -> None:
    chat_id = update.message.chat_id
    try:
        update.message.reply_text("Начинаю загрузку пина с Pinterest...")
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')img_tag = soup.find("img", src=re.compile(r'https://i.pinimg.com/originals/'))
        if img_tag and img_tag.get("src"):
            img_url = img_tag['src']
            img_response = requests.get(img_url, headers=headers)
            img_path = os.path.join("downloads", "pinterest_image.jpg")

            with open(img_path, 'wb') as f:
                f.write(img_response.content)

            file_size = os.path.getsize(img_path) / (1024 * 1024)
            if file_size > 50:
                update.message.reply_text("Изображение слишком большое (>50 МБ)!")
                os.remove(img_path)
                return

            with open(img_path, 'rb') as f:
                context.bot.send_photo(chat_id=chat_id, photo=f)
            update.message.reply_text("Изображение отправлено!")
            os.remove(img_path)
        else:
            update.message.reply_text("Не удалось найти изображение в пине!")

    except Exception as e:
        logger.error(f"Pinterest ошибка: {e}")
        update.message.reply_text(f"Ошибка при скачивании с Pinterest: {e}")

# Обработка текстовых сообщений (ссылок)
def handle_link(update: Update, context: CallbackContext) -> None:
    url = update.message.text.strip()

    if "youtube.com" in url or "youtu.be" in url:
        download_youtube(update, context, url)
    elif "instagram.com" in url:
        download_instagram(update, context, url)
    elif "pinterest.com" in url:
        download_pinterest(update, context, url)
    else:
        update.message.reply_text(
            "Пожалуйста, отправь ссылку на YouTube, Instagram или Pinterest!"
        )

# Обработчик ошибок
def error(update: Update, context: CallbackContext) -> None:
    logger.warning(f'Update {update} caused error {context.error}')

def main() -> None:
    # Вставьте ваш токен от @BotFather
    TOKEN = "8029256016:AAEeLOJvNVYYLQyDLPt92j6MYlWV0ImrB5M"

    # Создаем директорию для скачивания
    if not os.path.exists("downloads"):
        os.makedirs("downloads")

    # Инициализируем Updater
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # Регистрируем обработчики
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_link))
    dp.add_error_handler(error)

    # Запускаем бота
    updater.start_polling()
    updater.idle()

if name == 'main':
    main()