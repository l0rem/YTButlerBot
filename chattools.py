from telegram import Update
from dbmodels import Users, db


def store_user(update: Update):
    uid = update.effective_message.from_user.id

    with db:
        user_entry = Users.select().where(Users.uid == uid)

        if user_entry.exists():
            return

        username = update.effective_message.from_user.username
        if username is None:
            username = update.effective_message.from_user.first_name

        Users.create(uid=uid,
                     username=username)
