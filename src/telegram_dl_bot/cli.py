import logging

import click

from telegram_dl_bot import config
from telegram_dl_bot.bot import make_bot


@click.command()
def main():
  logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=config.LOG_LEVEL
  )

  config.DOWNLOAD_FOLDER.mkdir(exist_ok=True, parents=True)

  bot = make_bot()

  bot.start_polling()
  bot.idle()