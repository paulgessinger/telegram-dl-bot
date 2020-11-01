from dataclasses import dataclass
import functools
import os

from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackContext, PicklePersistence
from telegram.ext.filters import Filters
import youtube_dl
import click
import validators

from telegram_dl_bot import config
from telegram_dl_bot.logging import logger


@dataclass()
class UserData:
  chat_id: int
  is_authenticated: bool = False

def ensure_user_data(fn):
  @functools.wraps(fn)
  def wrapped(update: Update, context: CallbackContext):
    if "data" not in context.user_data:
      context.user_data["data"] = UserData(chat_id=update.message.chat_id)
    return fn(update, context, context.user_data["data"])
  return wrapped

def get_user_data(context: CallbackContext) -> UserData:
  return context.user_data["data"]

def require_auth(fn):
  @functools.wraps(fn)
  def wrapped(update: Update, context: CallbackContext, user_data: UserData) -> None:
    if not user_data.is_authenticated:
      update.message.reply_text("You need to be authenticated to do this")
    else:
      return fn(update, context, user_data)
  return ensure_user_data(wrapped)

@ensure_user_data
def auth(update: Update, context: CallbackContext, user_data: UserData) -> None:
  logger.debug("Auth call received") 

  secret, = context.args
  if secret == config.AUTH_SECRET:
    first_name = update.message.chat.first_name
    update.message.reply_text(f"Ok {first_name}, you are now authenticated")
    user_data.is_authenticated = True
  else:
    update.message.reply_text("Nope")

@ensure_user_data
def deauth(update: Update, context: CallbackContext, user_data: UserData) -> None:
  logger.debug("De-Auth call received") 
  user_data.is_authenticated = False
  update.message.reply_text("Ok, bye!")

@ensure_user_data
def status(update: Update, context: CallbackContext, user_data: UserData) -> None:
  s = "authenticated" if user_data.is_authenticated else "not authenticated"
  update.message.reply_text(f"{update.message.chat.first_name}, you are {s}")

message_args = {
  "disable_web_page_preview": True
}

class DownloadTask:
  url: str

  __name__ = "DownloadTask"

  def __init__(self, url):
    self.url = url

  def __call__(self, context: CallbackContext) -> None:
    orig_context: CallbackContext = context.job.context
    user_data = get_user_data(orig_context)
    logger.info("Begin download of: %s for user %d", self.url, user_data.chat_id)
    context.bot.send_message(chat_id=user_data.chat_id, text=f"Download of '{self.url}' STARTED", **message_args)
    cwd = os.getcwd()
    try:
      os.chdir(config.DOWNLOAD_FOLDER)
      ydl = youtube_dl.YoutubeDL()
      with ydl:
        result = ydl.extract_info(self.url)
      context.bot.send_message(chat_id=user_data.chat_id, text=f"Download of '{self.url}' COMPLETED!", **message_args)
    except Exception as e:
      msg = """
  Download of '{url}' FAILED!
  <pre>{exc}</pre>
  """.format(url=self.url, exc=click.unstyle(str(e)))
      logger.debug(msg)
      context.bot.send_message(chat_id=user_data.chat_id, parse_mode="HTML", 
                              text=msg, **message_args)
    finally:
      os.chdir(cwd)

@require_auth
def download(update: Update, context: CallbackContext, user_data: UserData) -> None:
  url, = context.args
  logger.info("Requested download: %s", url)
  context.job_queue.run_once(DownloadTask(url), 0, context=context)

@require_auth
def download_message(update: Update, context: CallbackContext, user_data: UserData) -> None:
  text = update.message.text
  if validators.url(text):
    logger.info("Requested download: %s", text)
    context.job_queue.run_once(DownloadTask(text), 0, context=context)
  else:
    update.message.reply_text("Sorry, I don't know what to do with this")

def make_bot() -> Updater:

  persistence = PicklePersistence(filename=config.PICKLE_PERSISTENCE_LOCATION)

  updater = Updater(config.TELEGRAM_BOT_TOKEN, persistence=persistence, use_context=True)
  dp = updater.dispatcher

  dp.add_handler(CommandHandler("auth", auth))
  dp.add_handler(CommandHandler("deauth", deauth))
  dp.add_handler(CommandHandler("status", status))
  dp.add_handler(CommandHandler("download", download))
  dp.add_handler(MessageHandler(Filters.text & (~Filters.command), callback=download_message))

  return updater
