from dataclasses import dataclass
import functools
import os

from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext, PicklePersistence
import youtube_dl

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

@require_auth
def download(update: Update, context: CallbackContext, user_data: UserData) -> None:
  url, = context.args
  logger.info("Requested download: %s", url)
  context.job_queue.run_once(perform_download, 0, context=context)

def perform_download(context: CallbackContext):
  url, = context.job.context.args
  orig_context: CallbackContext = context.job.context
  user_data = get_user_data(orig_context)
  logger.info("Begin download of: %s for user %d", url, user_data.chat_id)
  context.bot.send_message(chat_id=user_data.chat_id, text=f"Download of '{url}' STARTED")
  cwd = os.getcwd()
  try:
    os.chdir(config.DOWNLOAD_FOLDER)
    ydl = youtube_dl.YoutubeDL()
    with ydl:
      result = ydl.extract_info(url)
    context.bot.send_message(chat_id=user_data.chat_id, text=f"Download of '{url}' COMPLETED!")
  except:
    context.bot.send_message(chat_id=user_data.chat_id, text=f"Download of '{url}' FAILED!")
  finally:
    os.chdir(cwd)


def make_bot() -> Updater:

  persistence = PicklePersistence(filename=config.PICKLE_PERSISTENCE_LOCATION)

  updater = Updater(config.TELEGRAM_BOT_TOKEN, persistence=persistence, use_context=True)
  dp = updater.dispatcher

  dp.add_handler(CommandHandler("auth", auth))
  dp.add_handler(CommandHandler("deauth", deauth))
  dp.add_handler(CommandHandler("status", status))
  dp.add_handler(CommandHandler("download", download))

  return updater
