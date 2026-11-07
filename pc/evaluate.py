"""Score recorded forecasts against subsequently observed buckets; read-only."""
import argparse
import json
import sqlite3
from contextlib import closing
from pathlib import Path
import config

def evaluate(path):
    with closing(sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True)) as db:
        truth={}
        for (payload,) in db.execute('SELECT payload FROM buckets'):
            r=json.loads(payload)
            if r.get('valid') and r['source']=='hardware':
                truth[r['node_id'],r['ts']]=r
        scores={}
        for (payload,) in db.execute('SELECT payload FROM results ORDER BY ts'):
            r=json.loads(payload)
            if r['source']!='hardware':continue
            current=truth.get((r['node_id'],r['ts']))
            if current is None:continue
            for h,p in r['forecasts'].items():
                target=truth.get((r['node_id'],r['ts']+int(h)*3600))
                if target is None:continue
                key=f"{r['node_id']} / +{h}h / {p['method']}"
                s=scores.setdefault(key,dict(n=0,absolute_error=0,persistence_error=0,covered=0,quantile_n=0))
                s['n']+=1
                s['absolute_error']+=abs(p['temp']-target['temperature_c'])
                s['persistence_error']+=abs(current['temperature_c']-target['temperature_c'])
                if p['temp_p80'] is not None:
                    s['quantile_n']+=1
                    s['covered']+=target['temperature_c']<=p['temp_p80']
        return {k:dict(n=v['n'],mae_c=v['absolute_error']/v['n'],
                       persistence_mae_c=v['persistence_error']/v['n'],
                       p80_coverage=v['covered']/v['quantile_n'] if v['quantile_n'] else None)
                for k,v in scores.items()}
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--db',default=str(config.DB));a=ap.parse_args()
    result=evaluate(a.db)
    print(json.dumps(result,indent=2) if result else 'No matched hardware forecast/target pairs yet. Allow at least 2–6 hours after forecasts start.')
