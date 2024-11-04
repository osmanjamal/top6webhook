import os
from pathlib import Path
import uuid

# تحديد المسارات
LOGS_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_LOCATION = os.path.join(LOGS_DIR, 'log.log')
LOG_LIMIT = 100

# إنشاء مجلد السجلات إذا لم يكن موجوداً
os.makedirs(os.path.dirname(LOG_LOCATION), exist_ok=True)

# التأكد من وجود ملف السجلات
try:
    open(LOG_LOCATION, 'r')
except FileNotFoundError:
    open(LOG_LOCATION, 'w').close()
if not os.path.exists(LOG_LOCATION):
    with open(LOG_LOCATION, 'w') as f:
        f.write("# Test log\n")


# DO NOT CHANGE
VERSION_NUMBER = '0.5'

# if key file exists, read key, else generate key and write to file
# WARNING: DO NOT CHANGE KEY ONCE GENERATED (this will break all existing events)
try:
    with open('.key', 'r') as key_file:
        UNIQUE_KEY = key_file.read().strip()
except FileNotFoundError:
    UNIQUE_KEY = str(uuid.uuid4())
    with open('.key', 'w') as key_file:
        key_file.write(UNIQUE_KEY)
        key_file.close()