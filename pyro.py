from pyrogram import Client
from decouple import config


userbot_api_id = config('API_ID')
userbot_api_hash = config('API_HASH')
userbot_chat_id = config('USER_ID')
bot_name = config('BOT_USERNAME')

app = Client('yt_servant',
             api_id=userbot_api_id,
             api_hash=userbot_api_hash)


def send_any_video(path, tag):
    app.start()
   
    message = app.send_video(chat_id=bot_name,
                             video=path,
                             caption=tag,
                             width=1920,
                             height=1080)
   
    app.stop()
    return message


def send_any_audio(path, tag):
    app.start()

    message = app.send_audio(chat_id=bot_name,
                             audio=path,
                             caption=tag)

    app.stop()
    return message


