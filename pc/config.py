"""Environment overrides; paths are stable regardless of working directory."""
import os
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
DATA = BASE / 'data'
DATA.mkdir(exist_ok=True)
DB = Path(os.getenv('AEROCLIM_DB', str(DATA / 'live.sqlite3'))).expanduser().resolve()
MODEL = Path(os.getenv('AEROCLIM_MODEL', str(DATA / 'real_model.pkl'))).expanduser().resolve()
BROKER = os.getenv('AEROCLIM_BROKER', '127.0.0.1')
PORT = int(os.getenv('AEROCLIM_PORT', '1883'))
ROOT = os.getenv('AEROCLIM_TOPIC_ROOT', 'aeroclim/lab')
USER = os.getenv('AEROCLIM_MQTT_USER', '')
PASSWORD = os.getenv('AEROCLIM_MQTT_PASS', '')
TLS = os.getenv('AEROCLIM_MQTT_TLS', '0') == '1'
CA = os.getenv('AEROCLIM_MQTT_CA') or None
LAT = float(os.getenv('AEROCLIM_LAT', '18.6298'))
LON = float(os.getenv('AEROCLIM_LON', '73.7997'))
MACRO = os.getenv('AEROCLIM_MACRO', 'openmeteo')
TRIGGER = float(os.getenv('AEROCLIM_CDI_TRIGGER', '42'))
RELEASE = float(os.getenv('AEROCLIM_CDI_RELEASE', '40'))
if RELEASE >= TRIGGER:
    raise ValueError('CDI release must be below trigger')
if not ROOT or any(c in ROOT for c in '+#') or ROOT.endswith('/'):
    raise ValueError('Invalid MQTT topic root')
STEP = 900
HORIZONS = (2, 4, 6)
STALE = 90
