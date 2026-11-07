import logging
from collections import defaultdict
import config
from forecasting import Forecaster, Advisory
from macro import Macro
from thermal import cdi

class Engine:
    def __init__(self, store, model=None, macro=None):
        self.store=store
        self.forecast=Forecaster(model)
        self.macro=macro or Macro()
        self.buffers={}
        self.advisories=defaultdict(Advisory)
        self.latest={}

    def process(self,p):
        node=p['node_id']
        last=self.latest.get(node)
        if last is None:
            last=self.store.latest_ts(node)
        if not self.store.insert(p):
            return False
        if last is not None and p['timestamp'] <= last:
            self.store.event(p['received'],'out_of_order',node)
            return False # raw remains available for diagnostics; never rewinds forecasts
        self.latest[node]=p['timestamp']
        slot=int(p['timestamp']//config.STEP)*config.STEP
        if node in self.buffers and self.buffers[node][0] != slot:
            old_slot,values=self.buffers.pop(node)
            self.finish(node,old_slot,values)
        self.buffers.setdefault(node,(slot,[]))[1].append(p)
        return True

    def finish(self,node,slot,values):
        valid=[p for p in values if p.get('temperature_c') is not None and p.get('humidity') is not None]
        # Coverage across ten minutes, ≥30 valid readings; gaps may not exceed 90s.
        times=sorted(p['timestamp'] for p in valid)
        ok=(len(valid)>=30 and times[-1]-times[0]>=600 and
            max([b-a for a,b in zip(times,times[1:])] or [0])<=90)
        row=dict(node_id=node, ts=slot+config.STEP, source=values[-1]['source'],
                 count=len(values), valid_count=len(valid), valid=ok)
        for key in ('temperature_c','humidity','lux','pm25_ugm3','mq_adc_mv'):
            vs=[p[key] for p in valid if p.get(key) is not None]
            row[key]=sum(vs)/len(vs) if vs else None
        row['edge_anomaly']=int(any(p['edge_anomaly'] for p in values))
        row['macro']=self.macro.get(row['ts']) if ok else None
        if ok:
            pred=self.forecast.predict(row)
            result=dict(node_id=node,ts=row['ts'],source=row['source'],forecasts=pred,
                        cdi_now=cdi(row['temperature_c'],row['humidity']),
                        advisory=self.advisories[node].update(row['ts'],pred))
        else:
            self.forecast.buf.pop(node,None)
            self.advisories.pop(node,None)
            result=dict(node_id=node,ts=row['ts'],source=row['source'],forecasts={},advisory='INSUFFICIENT_DATA')
        self.store.bucket(row,result)
        logging.info('%s bucket %s: %s (%s valid samples)',node,row['ts'],result['advisory'],len(valid))
