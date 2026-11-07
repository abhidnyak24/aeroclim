"""Capture forecasts at issue time. Failure yields None; no synthetic fallback in live mode."""
import json
import logging
import math
import time
import urllib.parse
import urllib.request
import config

class Macro:
    def __init__(self):
        self.data = None
        self.fetched = 0
        self.attempted = 0

    def get(self, ts):
        if config.MACRO == 'off':
            return None
        now = time.time()
        if now-self.fetched > 1800 and now-self.attempted > 60:
            self.attempted = now
            try:
                q = urllib.parse.urlencode(dict(latitude=config.LAT, longitude=config.LON,
                    hourly='temperature_2m,relative_humidity_2m', timeformat='unixtime',
                    timezone='UTC', forecast_days=2))
                with urllib.request.urlopen('https://api.open-meteo.com/v1/forecast?'+q, timeout=6) as f:
                    data = json.load(f)['hourly']
                for key in ('time', 'temperature_2m', 'relative_humidity_2m'):
                    if not data[key] or any(type(v) not in (int, float) or not math.isfinite(v) for v in data[key]):
                        raise ValueError('missing weather values')
                if len({len(data[k]) for k in ('time','temperature_2m','relative_humidity_2m')}) != 1:
                    raise ValueError('weather length mismatch')
                if any(b <= a for a,b in zip(data['time'],data['time'][1:])):
                    raise ValueError('weather time not increasing')
                self.data, self.fetched = data, now
            except Exception as e:
                logging.warning('Regional weather unavailable: %s', e)
        if self.data is None or now-self.fetched > 3600:
            return None
        d = self.data
        def interp(key, t):
            import bisect
            j = bisect.bisect_right(d['time'], t)
            if j == 0 or j >= len(d['time']):
                raise ValueError('outside forecast coverage')
            a,b = d['time'][j-1:j+1]
            return d[key][j-1] + (d[key][j]-d[key][j-1])*(t-a)/(b-a)
        try:
            return {'provider':'openmeteo', 'fetched_at':self.fetched,
                    'now':interp('temperature_2m',ts),
                    **{str(h):{'temp':interp('temperature_2m', ts+h*3600),
                              'hum':interp('relative_humidity_2m',ts+h*3600)} for h in config.HORIZONS}}
        except ValueError:
            return None
