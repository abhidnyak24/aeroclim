"""Offline demo explicitly isolated from hardware DB and real model training."""
import json
import math
import random
import time
import config
from protocol import decode
from store import Store
from engine import Engine
class DemoMacro:
    def get(self,ts):
        def temp(t):
            return 30+6*math.sin((t%86400)/86400*2*math.pi)
        return {'provider':'simulation','fetched_at':ts,'now':temp(ts),
                **{str(h):{'temp':temp(ts+h*3600),'hum':60} for h in config.HORIZONS}}

def run(ticks=0,speed=.05):
    if speed < 0 or ticks < 0:
        raise ValueError('ticks and speed must be nonnegative')
    store=Store(config.DATA/'demo.sqlite3')
    engine=Engine(store,macro=DemoMacro())
    rng=random.Random(17)
    boot='demo'+str(time.time_ns())
    ts=int(time.time()//900)*900
    i=0
    print('SIMULATION ONLY — data/demo.sqlite3; dashboard: enable Demo data')
    try:
        while not ticks or i<ticks:
            for n,bias in (('demo1',.8),('demo2',-.4),('demo3',1.5)):
                p=dict(schema=3,node_id=n,boot_id=boot,seq=i,timestamp=ts,source='simulation',
                       temperature_c=engine.macro.get(ts)['now']+bias+rng.uniform(-.2,.2),
                       humidity=60+rng.uniform(-1,1),lux=max(0,10000*math.sin(ts/86400*2*math.pi)),
                       pm25_ugm3=18+rng.uniform(-2,2),mq_adc_mv=900,edge_anomaly=0)
                engine.process(decode(json.dumps(p),allow_sim=True))
            ts+=10
            i+=1
            time.sleep(speed)
    except KeyboardInterrupt:
        pass
    finally:
        store.close()
