from telegram.ext import CommandHandler, MessageHandler, Filters, CallbackQueryHandler, run_async
from telegram import ParseMode, MessageEntity, InlineKeyboardButton, InlineKeyboardMarkup
from texts import start_text, invalid_link_text, video_default_form, video_with_description_form,\
    download_started_notification, already_downloading, filesize_too_big
from keyboards import default_video_keyboard, back_button, loading_button
from pytube import YouTube
import os
from pytube.exceptions import RegexMatchError
import subprocess
from chattools import store_user
from dbmodels import Downloads, db, Users
from pyro import send_any_video, send_any_audio
import time
import random


def start_callback(update, context):

    store_user(update)

    context.bot.send_message(update.message.from_user.id,
                             start_text,
                             parse_mode=ParseMode.HTML)


start_handler = CommandHandler('start',
                               callback=start_callback)


def url_callback(update, context):
    url = update.message.text
    uid = update.message.chat_id

    store_user(update)

    if str(uid) in os.listdir():
        if len(os.listdir('{}/video/'.format(uid))) > 0 or\
                len(os.listdir('{}/audio/'.format(uid))) > 0 or\
                len(os.listdir('{}/output/'.format(uid))) > 0:

            context.bot.send_message(update.message.from_user.id,
                                     already_downloading,
                                     parse_mode=ParseMode.HTML)

            return

    try:
        yt_object = YouTube(url)

    except RegexMatchError:

        context.bot.send_message(update.message.from_user.id,
                                 invalid_link_text,
                                 parse_mode=ParseMode.HTML)

        return

    title = yt_object.title
    length = yt_object.length
    views = yt_object.views
    description = yt_object.description

    length_converted = str(int(length) // 60) + ':' + str(int(length) % 60)

    download_video_button = InlineKeyboardButton(default_video_keyboard[0],
                                                 callback_data=0)
    download_audio_button = InlineKeyboardButton(default_video_keyboard[1],
                                                 callback_data=1)
    show_description_button = InlineKeyboardButton(default_video_keyboard[2],
                                                   callback_data=2)

    keyboard = InlineKeyboardMarkup([
        [download_video_button],
        [download_audio_button],
        [show_description_button]
    ])

    context.bot.send_message(update.message.from_user.id,
                             video_default_form.format(title,
                                                       length_converted,
                                                       views),
                             parse_mode=ParseMode.HTML,
                             reply_markup=keyboard)

    context.chat_data['yt_object'] = yt_object
    context.chat_data['title'] = title
    context.chat_data['duration'] = length_converted
    context.chat_data['views'] = views
    context.chat_data['description'] = description


url_handler = MessageHandler(Filters.entity(MessageEntity.URL),
                             callback=url_callback)


def show_description_callback(update, context):

    title = context.chat_data['title']
    duration = context.chat_data['duration']
    views = context.chat_data['views']
    description = context.chat_data['description']

    button = InlineKeyboardButton(back_button,
                                  callback_data=-1)
    keyboard = InlineKeyboardMarkup([[button]])

    context.bot.edit_message_text(chat_id=update.callback_query.message.chat.id,
                                  message_id=update.callback_query.message.message_id,
                                  text=video_with_description_form.format(title,
                                                                          duration,
                                                                          views,
                                                                          description),
                                  parse_mode=ParseMode.HTML,
                                  reply_markup=keyboard)


show_description_handler = CallbackQueryHandler(pattern='2',
                                                callback=show_description_callback)


def back_to_default_callback(update, context):

    try:
        title = context.chat_data['title']
    except KeyError:
        context.bot.delete_message(chat_id=update.callback_query.message.chat_id,
                                   message_id=update.callback_query.message.message_id)
        return
    duration = context.chat_data['duration']
    views = context.chat_data['views']

    download_video_button = InlineKeyboardButton(default_video_keyboard[0],
                                                 callback_data=0)
    download_audio_button = InlineKeyboardButton(default_video_keyboard[1],
                                                 callback_data=1)
    show_description_button = InlineKeyboardButton(default_video_keyboard[2],
                                                   callback_data=2)

    keyboard = InlineKeyboardMarkup([[download_video_button],
                                     [download_audio_button],
                                     [show_description_button]])

    context.bot.edit_message_text(chat_id=update.callback_query.message.chat.id,
                                  message_id=update.callback_query.message.message_id,
                                  text=video_default_form.format(title,
                                                                 duration,
                                                                 views),
                                  parse_mode=ParseMode.HTML,
                                  reply_markup=keyboard)


back_to_default_handler = CallbackQueryHandler(pattern='-1',
                                               callback=back_to_default_callback)


def download_button_callback(update, context):

    yt_object = context.chat_data['yt_object']

    audio_streams = yt_object.streams.filter(only_audio=True)
    context.chat_data['audio_streams'] = audio_streams

    streams = yt_object.streams.filter(only_video=True)

    buttons = list()
    for stream in streams:
        mime_type = stream.mime_type.split('/')[1]

        resolution = stream.resolution
        if resolution is None:
            continue

        size = stream.filesize
        size_converted = round(size / 1000 / 1000, 2)

        fps = stream.fps
        n = streams.index(stream)

        button_text = resolution + '/' + str(fps) + 'FPS' + ' ' + mime_type.upper() + ' - ' + str(size_converted) + 'Mb'

        button = InlineKeyboardButton(text=button_text,
                                      callback_data='download:{}'.format(n))
        buttons.append([button])

    button = InlineKeyboardButton(back_button,
                                  callback_data=-1)
    buttons.append([button])

    keyboard = InlineKeyboardMarkup(buttons)

    context.chat_data['streams'] = streams

    context.bot.edit_message_reply_markup(chat_id=update.callback_query.message.chat.id,
                                          message_id=update.callback_query.message.message_id,
                                          reply_markup=keyboard)


download_button_handler = CallbackQueryHandler(pattern='0',
                                               callback=download_button_callback)


@run_async
def download_callback(update, context):
    n = int(update.callback_query.data.split(':')[1])
    uid = update.callback_query.message.chat_id

    video_stream = context.chat_data['streams'][n]
    audio_streams = context.chat_data['audio_streams']

    button = InlineKeyboardButton(loading_button, callback_data='NONE')
    kb = InlineKeyboardMarkup([[button]])

    context.bot.answer_callback_query(update.callback_query.id,
                                      download_started_notification,
                                      show_alert=True)
    context.bot.edit_message_reply_markup(update.callback_query.message.chat.id,
                                          update.callback_query.message.message_id,
                                          reply_markup=kb)

    if not os.path.exists('{}'.format(uid)):
        os.mkdir('{}'.format(uid))
    if not os.path.exists('{}/audio'.format(uid)):
        os.mkdir('{}/audio'.format(uid))
    if not os.path.exists('{}/video'.format(uid)):
        os.mkdir('{}/video'.format(uid))
    if not os.path.exists('{}/output'.format(uid)):
        os.mkdir('{}/output'.format(uid))

    highest_abr = -1

    if 'webm' in video_stream.mime_type:
        for stream in audio_streams:
            if 'webm' in stream.mime_type:
                if stream.abr is not None and int(stream.abr.split('k')[0]) > highest_abr:
                    highest_abr = int(stream.abr.split('k')[0])
                    n = audio_streams.index(stream)
    else:
        for stream in audio_streams:
            if 'mp4' in stream.mime_type:
                if stream.abr is not None and int(stream.abr.split('k')[0]) > highest_abr:
                    highest_abr = int(stream.abr.split('k')[0])
                    n = audio_streams.index(stream)

    audio_stream = audio_streams[n]

    filename_v = str(random.randint(0, 9999999999)) + '.' + video_stream.default_filename.split('.')[-1]
    filename_a = str(random.randint(0, 9999999999)) + '.' + audio_stream.default_filename.split('.')[-1]

    print('Downloading video...\n')
    video_stream.download(output_path='{}/video/'.format(uid),
                          filename=filename_v.split('.')[0])
    print('Video downloaded.\n')

    print('Downloading audio...\n')
    audio_stream.download(output_path='{}/audio/'.format(uid),
                          filename=filename_a.split('.')[0])
    print('Audio downloaded.\n')

    video_path = '{}/video/{}'.format(uid,
                                      filename_v)
    audio_path = '{}/audio/{}'.format(uid,
                                      filename_a)

    output_path = '{}/output/{}'.format(uid,
                                        filename_v)

    video_path = os.path.abspath(video_path)
    audio_path = os.path.abspath(audio_path)
    output_path = os.path.abspath(output_path)

    print('Merging files with ffmpeg...')
    cmd = 'ffmpeg -i \"{}\" -i \"{}\" -c copy  \"{}\"'.format(video_path, audio_path, output_path)
    try:
        subprocess.call(cmd, shell=True)
    except FileNotFoundError:
        time.sleep(10)
        subprocess.call(cmd, shell=True)
    print('Merge completed.')

    if os.path.getsize('{}/output/{}'.format(uid, filename_v)) <= 52428800:
        print('Filesize OK, sending via BotAPI...')
        fid = context.bot.send_video(chat_id=update.callback_query.message.chat_id,
                                     video=open('{}/output/{}'.format(uid,
                                                                      filename_v), 'rb'),
                                     width=1920,
                                     height=1080,
                                     supports_streaming=True,
                                     duration=context.chat_data['yt_object'].length).video.file_id

        print('File sent.')
    else:
        print('Filesize not OK, sending via Userbot...')
        message = send_any_video(path=output_path, tag=uid)
        if message is None:
            context.bot.send_message(text=filesize_too_big,
                                     parse_mode='HTML',
                                     chat_id=uid)

            back_to_default_callback(update, context)

            return
        fid = message.video.file_id

        context.bot.send_video(chat_id=update.callback_query.message.chat_id,
                               video=fid,
                               width=1920,
                               height=1080,
                               supports_streaming=True,
                               duration=context.chat_data['yt_object'].length)
        print('File sent.')

    button = InlineKeyboardButton(back_button,
                                  callback_data=-1)
    keyboard = InlineKeyboardMarkup([[button]])

    context.bot.edit_message_reply_markup(update.callback_query.message.chat.id,
                                          update.callback_query.message.message_id,
                                          reply_markup=keyboard)

    with db:
        Downloads.create(
            user=Users.get(Users.uid == uid),
            filename=filename_v,
            yt_url=context.chat_data['yt_object'].watch_url,
            file_id=fid,
            filesize=str(os.path.getsize('{}/output/{}'.format(uid, filename_v)))
        )

    os.remove(video_path)
    os.remove(audio_path)
    os.remove(output_path)


download_callback_handler = CallbackQueryHandler(pattern='download:(.*)',
                                                 callback=download_callback)


def download_audio_button_callback(update, context):

    yt_object = context.chat_data['yt_object']
    streams = yt_object.streams.filter(only_audio=True)

    buttons = list()
    for stream in streams:
        if stream.abr is None:
            continue
        abr = stream.abr
        mime_type = stream.mime_type.split('/')[1]
        size = stream.filesize
        size_converted = round(size / 1000 / 1000, 2)
        n = streams.index(stream)

        button_text = abr + ' ' + mime_type.upper() + ' - ' + str(size_converted) + 'Mb'

        button = InlineKeyboardButton(text=button_text,
                                      callback_data='download_audio:{}'.format(n))
        buttons.append([button])

    button = InlineKeyboardButton(back_button,
                                  callback_data=-1)
    buttons.append([button])

    keyboard = InlineKeyboardMarkup(buttons)

    context.chat_data['streams'] = streams

    context.bot.edit_message_reply_markup(chat_id=update.callback_query.message.chat.id,
                                          message_id=update.callback_query.message.message_id,
                                          reply_markup=keyboard)


download_audio_button_handler = CallbackQueryHandler(pattern='1',
                                                     callback=download_audio_button_callback)


@run_async
def download_audio_callback(update, context):
    n = int(update.callback_query.data.split(':')[1])
    uid = update.callback_query.message.from_user.id

    store_user(update)

    stream = context.chat_data['streams'][n]

    button = InlineKeyboardButton(loading_button, callback_data='NONE')
    kb = InlineKeyboardMarkup([[button]])

    context.bot.answer_callback_query(update.callback_query.id,
                                      download_started_notification,
                                      show_alert=True)
    context.bot.edit_message_reply_markup(update.callback_query.message.chat.id,
                                          update.callback_query.message.message_id,
                                          reply_markup=kb)

    if not os.path.exists('{}'.format(uid)):
        os.mkdir('{}'.format(uid))
    if not os.path.exists('{}/audio'.format(uid)):
        os.mkdir('{}/audio'.format(uid))

    filename = str(random.randint(0, 9999999999)) + '.' + stream.default_filename.split('.')[-1]

    stream.download(output_path='{}/audio/'.format(uid),
                    filename=filename.split('.')[0])

    audio_path = '{}/audio/{}'.format(uid,
                                      filename)

    audio_path = os.path.abspath(audio_path)

    if os.path.getsize('{}/audio/{}'.format(uid, filename)) <= 52428800:
        fid = context.bot.send_audio(chat_id=update.callback_query.message.chat_id,
                                     audio=open('{}/audio/{}'.format(uid,
                                                                     filename), 'rb'),
                                     title=context.chat_data['yt_object'].title,
                                     performer='YTButlerBot').audio.file_id
    else:
        message = send_any_audio(path=audio_path, tag=uid)
        fid = message.audio.file_id

        context.bot.send_audio(chat_id=update.callback_query.message.chat_id,
                               audio=fid,
                               title=context.chat_data['yt_object'].title,
                               performer='YTButlerBot')

    button = InlineKeyboardButton(back_button,
                                  callback_data=-1)
    keyboard = InlineKeyboardMarkup([[button]])

    context.bot.edit_message_reply_markup(update.callback_query.message.chat.id,
                                          update.callback_query.message.message_id,
                                          reply_markup=keyboard)

    with db:
        Downloads.create(
            user=Users.get(Users.uid == uid),
            filename=filename,
            yt_url=context.chat_data['yt_object'].watch_url,
            file_id=fid,
            filesize=str(os.path.getsize('{}/audio/{}'.format(uid, filename)))
        )

    os.remove(audio_path)


download_audio_callback_handler = CallbackQueryHandler(pattern='download_audio:(.*)',
                                                       callback=download_audio_callback)
