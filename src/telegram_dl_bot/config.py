import os
import logging
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
LOG_LEVEL = getattr(logging, os.environ.get("LOG_LEVEL", "INFO"))
AUTH_SECRET = os.environ.get("AUTH_SECRET")
PICKLE_PERSISTENCE_LOCATION = os.environ.get("PICKLE_PERSISTENCE_LOCATION")
DOWNLOAD_FOLDER = Path(os.environ.get("DOWNLOAD_FOLDER")).resolve()