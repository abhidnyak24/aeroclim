"""Strict v3 transport contract. Missing sensors are null, never fabricated zeros."""
import json
import math
import re
import time
ID = re.compile(r'^[A-Za-z0-9_-]{1,40}$')
RANGES = {'temperature_c': (-40, 80), 'humidity': (0, 100), 'lux': (0, 250000),
          'pm1_ugm3': (0, 2000), 'pm25_ugm3': (0, 2000), 'pm10_ugm3': (0, 3000),
          'mq_adc_mv': (0, 3600), 'mq_ao_mv': (0, 6000), 'rssi_dbm': (-130, 0)}

def decode(raw, topic_node=None, received=None, allow_sim=False):
    if len(raw) > 8192:
        raise ValueError('payload exceeds 8192 bytes')
    def reject(s):
        raise ValueError('nonfinite JSON constant')
    p = json.loads(raw, parse_constant=reject)
    if not isinstance(p, dict) or p.get('schema') != 3:
        raise ValueError('expected schema 3 object')
    for key in ('node_id', 'boot_id'):
        if not isinstance(p.get(key), str) or not ID.fullmatch(p[key]):
            raise ValueError('invalid ' + key)
    if topic_node is not None and topic_node != p['node_id']:
        raise ValueError('topic/payload node mismatch')
    if type(p.get('seq')) is not int or not 0 <= p['seq'] <= 0xFFFFFFFF:
        raise ValueError('invalid sequence')
    if p.get('source') not in ('hardware', 'simulation'):
        raise ValueError('invalid source')
    if p['source'] == 'simulation' and not allow_sim:
        raise ValueError('simulation refused by live collector')
    for key, (lo, hi) in RANGES.items():
        x = p.get(key)
        if x is not None and (type(x) not in (float, int) or not math.isfinite(x) or not lo <= x <= hi):
            raise ValueError('invalid ' + key)
    if type(p.get('edge_anomaly')) not in (bool, int) or p['edge_anomaly'] not in (0, 1):
        raise ValueError('invalid edge flag')
    received = time.time() if received is None else received
    ts = p.get('timestamp')
    if ts is None:
        ts = received
        p['time_quality'] = 'receive_time'
    elif type(ts) not in (float, int) or not math.isfinite(ts) or ts < 1700000000:
        raise ValueError('invalid UTC epoch timestamp')
    else:
        if p['source'] == 'hardware' and abs(ts - received) > 120:
            raise ValueError('clock skew / delayed packet over 120 seconds')
        p['time_quality'] = 'ntp' if p['source'] == 'hardware' else 'simulation'
    p.update(timestamp=float(ts), received=received)
    return p
