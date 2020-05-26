from pyrogram import Client
from decouple import config

api_id = config('API_ID')
api_hash = config('API_HASH')
userbot_id = config('USER_ID')
bot_name = config('BOT_USERNAME')

app = Client('yt_servant',
             api_id=api_id,
             api_hash=api_hash)


def progress(current, total):
    print("{:.1f}%".format(current * 100 / total))


def send_any_video(path, tag):
    app.workers = 4
    app.start()
    print('Userbot started...')

    print('Uploading video...')
    try:
        message = app.send_video(chat_id=bot_name,
                                 video=path,
                                 caption=tag,
                                 supports_streaming=True,
                                 progress=progress,
                                 width=1920,
                                 height=1080)
    except Exception as e:
        print(e)

        app.stop()
        
        return None
    print('Video uploaded.')
   
    app.stop()
    print('Userbot stopped.')
    return message


def send_any_audio(path, tag):
    app.start()

    message = app.send_audio(chat_id=bot_name,
                             audio=path,
                             caption=tag)

    app.stop()
    return message


