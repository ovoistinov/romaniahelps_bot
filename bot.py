#!/usr/bin/env python
# pylint: disable=C0116,W0613
# This program is dedicated to the public domain under the CC0 license.

import logging
import os
import smtplib

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext,
)

PORT = int(os.environ.get("PORT", 8443))

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if BOT_TOKEN is None:
    raise EnvironmentError("Please, set BOT_TOKEN environment variable with the bot token from @BotFather")
BOT_URL = "https://romanianshelp.herokuapp.com/"

EMAIL_USER = "romanianshelp@gmail.com"
EMAIL_PASSWD = os.environ.get("EMAIL_PASSWD")
if EMAIL_PASSWD is None:
    raise EnvironmentError("Please, set EMAIL_PASSWD environment variable with the emal password")

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

HELP_NEEDED, LOCATION, CONTACTS = range(3)


def send_email(user_data):
    gmail_user = EMAIL_USER
    gmail_password = EMAIL_PASSWD

    sent_from = gmail_user
    to = [gmail_user]
    subject = '[Bot] Help needed!'
    body = f"Hey Volunteers,\n\nI collected the following data: {user_data}"

    email_text = """\
    From: %s
    To: %s
    Subject: %s

    %s
    """ % (sent_from, ", ".join(to), subject, body)

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.ehlo()
        server.login(gmail_user, gmail_password)
        server.sendmail(sent_from, to, email_text)
        server.close()

        logger.info('Email sent successfully!')
    except:
        logger.error('Something went wrong with email...')


def start(update: Update, context: CallbackContext) -> int:
    """Starts the conversation and asks the user about help message."""

    update.message.reply_text(
        'Hi! Romanians Help Bot will help you to connect with volunteers in Romania. '
        'Send /cancel to stop interaction.\n\n'
        'What kind of help do you need (e.g. accomodation, food, or something else)?',
    )

    return HELP_NEEDED


def help_needed(update: Update, context: CallbackContext) -> int:
    """Stores the selected gender and asks for a photo."""
    user = update.message.from_user
    text = update.message.text

    context.user_data[user.id] = {}
    context.user_data[user.id]['user_name'] = user.first_name
    context.user_data[user.id]['help_needed'] = text

    logger.info("User %s needs help with: %s", user.first_name, text)
    update.message.reply_text(
        'I see! Please send me your location, '
        'so volunteers can find you, or send /skip if you don\'t want to.',
    )

    return LOCATION


def location(update: Update, context: CallbackContext) -> int:
    """Stores the location and asks for some the user's contacts."""
    user = update.message.from_user
    user_location = update.message.location

    user_data = context.user_data
    user_data[user.id]['location'] = (user_location.latitude, user_location.longitude)

    logger.info(
        "Location of %s: %f / %f", user.first_name, user_location.latitude, user_location.longitude
    )
    update.message.reply_text(
        'Thank you! At last, tell me how our volunteers can contact you.'
    )

    return CONTACTS


def skip_location(update: Update, context: CallbackContext) -> int:
    """Skips the location and asks for the user contacts."""
    user = update.message.from_user
    user_data = context.user_data
    user_data[user.id]['location'] = (None, None)

    logger.info("User %s did not send a location.", user.first_name)
    update.message.reply_text(
        'That\'s fine, we respect your privacy! At last, tell me how our volunteers can contact you.'
    )

    return CONTACTS


def contacts(update: Update, context: CallbackContext) -> int:
    """Stores the info about the user and ends the conversation."""
    user = update.message.from_user
    user_data = context.user_data
    text = update.message.text
    context.user_data[user.id]['contacts'] = text

    logger.info("Contacts of %s: %s", user.first_name, text)
    update.message.reply_text('Thank you! Romanian volunteers will reach out to you shortly.')

    send_email(user_data)
    logger.info("Gathered data: %s", user_data)

    return ConversationHandler.END


def cancel(update: Update, context: CallbackContext) -> int:
    """Cancels and ends the conversation."""
    user = update.message.from_user
    user_data = context.user_data

    logger.info("User %s canceled the conversation.", user.first_name)
    update.message.reply_text(
        'Interaction canceled! Stay safe.', reply_markup=ReplyKeyboardRemove()
    )

    user_data.clear()
    return ConversationHandler.END


def main() -> None:
    """Run the bot."""

    updater = Updater(BOT_TOKEN)

    dispatcher = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler(['start', 'starthelp'], start)],
        states={
            HELP_NEEDED: [MessageHandler(Filters.text & ~Filters.command, help_needed)],
            LOCATION: [
                MessageHandler(Filters.location, location),
                CommandHandler('skip', skip_location),
            ],
            CONTACTS: [MessageHandler(Filters.text & ~Filters.command, contacts)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    dispatcher.add_handler(conv_handler)

    updater.start_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=f"{BOT_URL}{BOT_TOKEN}",
    )

    updater.idle()


if __name__ == '__main__':
    main()
