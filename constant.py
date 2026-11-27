import os
import datetime as dt
import time
from dotenv import load_dotenv

load_dotenv()

CHANNEL_ACCESS_TOKEN = os.getenv('CHANNEL_ACCESS_TOKEN')
CHANNEL_SECRET = os.getenv('CHANNEL_SECRET')
URL = "https://www.sportsentry.ne.jp/event/t/107858"
TARGET = "A）100mile"   # 100mileソロ
REPORT_HOUR = 21        # 定時レポートの時刻（この時刻以降の最初の取得で送信）
HEADERS = {"User-Agent": "Mozilla/5.0 (personal slot notifier)"}
JST = dt.timezone(dt.timedelta(hours=9))
