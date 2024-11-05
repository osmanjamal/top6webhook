import os
from pathlib import Path
import uuid

# Get base directory
BASE_DIR = Path(__file__).resolve().parent

# Define log locations
LOG_LOCATION = os.path.join(BASE_DIR, 'components', 'logs', 'log.log')
LOG_LIMIT = 100

# Create logs directory if not exists
os.makedirs(os.path.dirname(LOG_LOCATION), exist_ok=True)

# Ensure log file exists
try:
    open(LOG_LOCATION, 'r')
except FileNotFoundError:
    open(LOG_LOCATION, 'w').close()

if not os.path.exists(LOG_LOCATION):
    with open(LOG_LOCATION, 'w') as f:
        f.write("# Test log\n")

# DO NOT CHANGE
VERSION_NUMBER = '0.5'

# Handle key file
KEY_PATH = os.path.join(BASE_DIR, '.key')

try:
    with open(KEY_PATH, 'r') as key_file:
        UNIQUE_KEY = key_file.read().strip()
except FileNotFoundError:
    UNIQUE_KEY = str(uuid.uuid4())
    with open(KEY_PATH, 'w') as key_file:
        key_file.write(UNIQUE_KEY)
        