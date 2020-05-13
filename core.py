from decouple import config
from telegram.ext import Updater
from handlers import start_handler, url_handler, show_description_handler, back_to_default_handler,\
    download_button_handler, download_callback_handler, download_audio_button_handler, download_audio_callback_handler
import logging
import shutil
import os


bot_token = config('BOT_TOKEN')

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

upd = Updater(bot_token, use_context=True)

dp = upd.dispatcher


if __name__ == '__main__':
    for file in os.listdir():
        if '.' not in file and file.isdigit():
            shutil.rmtree(file)

    dp.add_handler(start_handler)
    dp.add_handler(url_handler)
    dp.add_handler(show_description_handler)
    dp.add_handler(back_to_default_handler)
    dp.add_handler(download_button_handler)
    dp.add_handler(download_callback_handler)
    dp.add_handler(download_audio_button_handler)
    dp.add_handler(download_audio_callback_handler)

    upd.start_polling()
