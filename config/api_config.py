import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from highlow-tui project root (parent of config/)
_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=_ROOT / '.env')

API_KEY = os.getenv('API_KEY')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')

CALLBACK_URL = os.getenv('CALLBACK_URL', 'https://127.0.0.1')
TOKEN_PATH = os.getenv('TOKEN_PATH', str(_ROOT / 'token.json'))
