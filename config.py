# config.py
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
GOOGLE_PROJECT_ID = os.getenv('GOOGLE_CLOUD_PROJECT')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
CACHE_DIR = ".cache"
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB