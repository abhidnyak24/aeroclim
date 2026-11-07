"""Direct 2/4/6h offset models; shared features; chronological purged holdout."""
import json
import math
import os
import pickle
import tempfile
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
import config
from thermal import cdi
VERSION = 3

def features(rows, h):
    if len(rows) < 5:
        return None
    rows = list(rows)[-5:]
    if any(b['ts']-a['ts'] != config.STEP for a,b in zip(rows,rows[1:])):
        return None
    r = rows[-1]
    if not r.get('macro') or any(x.get('temperature_c') is None or x.get('humidity') is None for x in rows):
        return None
    m = r['macro']
    temps = [x['temperature_c'] for x in rows]
    mean = sum(temps)/5
    hour = (r['ts'] % 86400)/3600  # UTC consistently in train and live
    return [temps[-1], r['humidity'], temps[-1]-temps[-2], temps[-1]-temps[0],
            mean, math.sqrt(sum((x-mean)**2 for x in temps)/5),
            r['humidity']-rows[0]['humidity'], math.sin(hour*math.pi/12), math.cos(hour*math.pi/12),
            temps[-1]-m['now'], m[str(h)]['temp']-m['now'], m[str(h)]['hum'],
            r.get('lux') or 0, int(r.get('lux') is None)]

def samples(history, h):
    grouped = defaultdict(list)
    for r in history:
        if r.get('valid') and r['source'] == 'hardware' and (r.get('macro') or {}).get('provider') == 'openmeteo':
            grouped[r['node_id']].append(r)
    out = []
    for node, rows in grouped.items():
        rows.sort(key=lambda r:r['ts'])
        by_time = {r['ts']:r for r in rows}
        for i,r in enumerate(rows):
            x = features(rows[max(0,i-4):i+1], h)
            target = by_time.get(r['ts']+h*3600)
            if x is not None and target is not None:
                out.append((r['ts'], r['ts']+h*3600, node, x,
                            target['temperature_c']-r['macro'][str(h)]['temp'], target['humidity'], r, target))
    return sorted(out, key=lambda x:x[0])

def train(history, path, backend='sklearn'):
    import numpy as np
    grouped = defaultdict(list)
    for r in history:
        if r.get('valid') and r['source']=='hardware' and (r.get('macro') or {}).get('provider')=='openmeteo':
            grouped[r['node_id']].append(r['ts'])
    eligible = {n for n,ts in grouped.items() if len(set(ts)) >= 7*96 and max(ts)-min(ts) >= 7*86400}
    history = [r for r in history if r['node_id'] in eligible]
    if not eligible:
        raise ValueError('Need at least 7 days AND 672 valid weather-backed buckets for a node; aim for 2–4 weeks.')
    times = sorted(set(r['ts'] for r in history))
    cutoff = times[int(len(times)*.8)]
    def model(q):
        if backend == 'xgboost':
            from xgboost import XGBRegressor
            return XGBRegressor(objective='reg:quantileerror', quantile_alpha=q,
                n_estimators=150, max_depth=3, learning_rate=.05, n_jobs=2, random_state=17)
        from sklearn.ensemble import HistGradientBoostingRegressor
        return HistGradientBoostingRegressor(loss='quantile', quantile=q,
            max_iter=120, max_depth=3, learning_rate=.06, random_state=17, early_stopping=False)
    bundle = {'version':VERSION, 'source':'hardware', 'backend':backend, 'nodes':sorted(eligible),
              'trained_at':datetime.now(timezone.utc).isoformat(), 'models':{}}
    report = {k:v for k,v in bundle.items() if k!='models'}
    report.update(holdout_start=cutoff, purge='training target time < holdout start', horizons={})
    for h in config.HORIZONS:
        ds = samples(history,h)
        tr = [s for s in ds if s[1] < cutoff]
        te = [s for s in ds if s[0] >= cutoff]
        if len(tr) < 200 or len(te) < 40:
            raise ValueError(f'+{h}h has too few continuous train/test windows ({len(tr)}/{len(te)})')
        def fit(data):
            X = np.array([s[3] for s in data])
            return [model(q).fit(X, [s[target] for s in data]) for q,target in ((.5,4),(.8,4),(.5,5))]
        ms = fit(tr)
        X = np.array([s[3] for s in te])
        regional = np.array([s[6]['macro'][str(h)]['temp'] for s in te])
        actual = np.array([s[7]['temperature_c'] for s in te])
        med = regional+ms[0].predict(X)
        upper = np.maximum(med,regional+ms[1].predict(X))
        rh = np.clip(ms[2].predict(X),0,100)
        persistence = np.array([s[6]['temperature_c'] for s in te])
        truth = np.array([cdi(s[7]['temperature_c'],s[7]['humidity']) >= config.TRIGGER for s in te])
        alerts = np.array([cdi(t,r) >= config.TRIGGER for t,r in zip(upper,rh)])
        tp,fp,fn = int(sum(alerts & truth)),int(sum(alerts & ~truth)),int(sum(~alerts & truth))
        mae = float(np.mean(abs(med-actual)))
        persist_mae = float(np.mean(abs(persistence-actual)))
        regional_mae = float(np.mean(abs(regional-actual)))
        report['horizons'][str(h)] = dict(n_train=len(tr), n_test=len(te), mae_c=mae,
            persistence_mae_c=persist_mae, regional_mae_c=regional_mae,
            upper80_empirical_coverage=float(np.mean(actual<=upper)),
            alert_precision=tp/(tp+fp) if tp+fp else None,
            alert_recall=tp/(tp+fn) if tp+fn else None,
            alert_f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None,
            beats_both_baselines=mae < min(persist_mae,regional_mae))
        bundle['models'][h] = fit(ds)
    bundle['report'] = report
    path = Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent,delete=False) as f:
        pickle.dump(bundle,f)
        tmp = f.name
    os.replace(tmp,path)
    path.with_suffix('.report.json').write_text(json.dumps(report,indent=2))
    return report

class Forecaster:
    def __init__(self, path=None):
        self.bundle = None
        self.buf = defaultdict(lambda:deque(maxlen=5))
        if path and Path(path).exists():
            with open(path,'rb') as f: # Only your own locally trained model. Pickle executes code.
                b = pickle.load(f)
            if b.get('version') != VERSION or b.get('source') != 'hardware':
                raise ValueError('Model version/source mismatch; retrain locally')
            self.bundle = b

    def predict(self, r):
        self.buf[r['node_id']].append(r)
        result = {}
        for h in config.HORIZONS:
            m = r.get('macro')
            x = features(self.buf[r['node_id']], h)
            if self.bundle and r['node_id'] in self.bundle['nodes'] and x and m['provider']=='openmeteo':
                ms = self.bundle['models'][h]
                temp = m[str(h)]['temp'] + float(ms[0].predict([x])[0])
                upper = max(temp, m[str(h)]['temp']+float(ms[1].predict([x])[0]))
                hum = max(0,min(100,float(ms[2].predict([x])[0])))
                method = 'trained_real_quantiles'
            elif m:
                temp = m[str(h)]['temp'] + max(-8,min(8,r['temperature_c']-m['now']))*math.exp(-h/6)
                hum = m[str(h)]['hum']
                upper,method = None,'regional_offset_baseline'
            else:
                temp,hum = r['temperature_c'],r['humidity']
                upper,method = None,'persistence_baseline'
            result[str(h)] = dict(temp=temp, temp_p80=upper, humidity=hum, cdi=cdi(temp,hum),
                cdi_risk_proxy=cdi(upper,hum) if upper is not None else None, method=method)
        return result

class Advisory:
    """Software suggestion only. State counts complete 15-minute buckets, not packets."""
    def __init__(self):
        self.on=False
        self.above=self.below=0
        self.since=None
        self.last=None
    def update(self, ts, preds):
        if self.last is not None and ts-self.last != config.STEP:
            self.__init__()
        self.last=ts
        # The 2h horizon drives recommendations; longer horizons are planning information.
        p=preds['2']
        value=p['cdi_risk_proxy'] if p['cdi_risk_proxy'] is not None else p['cdi']
        self.above=self.above+1 if value >= config.TRIGGER else 0
        self.below=self.below+1 if value < config.RELEASE else 0
        if not self.on and self.above >= 2:
            self.on,self.since=True,ts
        elif self.on and self.below >= 3 and ts-self.since >= 3600:
            self.on=False
        return 'CONSIDER_PRECOOLING' if self.on else 'MONITOR'
