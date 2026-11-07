import json
import math
import os
import pathlib
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'pc'))
import config
from protocol import decode
from thermal import heat_index_c
from store import Store
from engine import Engine
from forecasting import Advisory,features,samples,train,Forecaster
from macro import Macro

T=1800000000

def packet(**changes):
    p=dict(schema=3,node_id='node4',boot_id='abc',seq=1,source='hardware',timestamp=T,
           temperature_c=30,humidity=60,lux=200,edge_anomaly=0)
    p.update(changes)
    return p

def parsed(**changes):
    return decode(json.dumps(packet(**changes)),received=T)

class NoMacro:
    def get(self,ts):return None

class ProtocolTests(unittest.TestCase):
    def test_valid_and_null(self):
        self.assertIsNone(parsed(temperature_c=None)['temperature_c'])
        self.assertEqual(parsed()['node_id'],'node4')
    def test_receive_time(self):
        p=parsed(timestamp=None)
        self.assertEqual(p['timestamp'],T)
        self.assertEqual(p['time_quality'],'receive_time')
    def test_bad_packets(self):
        for change in [dict(temperature_c=True),dict(humidity=101),dict(lux=float('nan')),
                       dict(seq=-1),dict(node_id='../x'),dict(source='simulation'),dict(timestamp=T+121),
                       dict(edge_anomaly=2),dict(pm25_ugm3=-1),dict(boot_id=[]),dict(schema=2)]:
            with self.subTest(change=change),self.assertRaises(ValueError):parsed(**change)
    def test_topic_identity(self):
        with self.assertRaises(ValueError): decode(json.dumps(packet()),'wrong',T)
    def test_shape_size(self):
        for raw in ['[]','null','x'*9000,'{"x":NaN}']:
            with self.assertRaises(ValueError): decode(raw,received=T)

class CoreTests(unittest.TestCase):
    def test_heat_index_reference(self):
        self.assertAlmostEqual(heat_index_c((100-32)/1.8,55)*1.8+32,124,delta=1)
        self.assertLess(heat_index_c((100-32)/1.8,15),(100-32)/1.8)
    def test_hysteresis_and_gap(self):
        a=Advisory()
        hot={'2':dict(cdi=43,cdi_risk_proxy=None)}
        cool={'2':dict(cdi=38,cdi_risk_proxy=None)}
        self.assertEqual(a.update(T,hot),'MONITOR')
        self.assertEqual(a.update(T+900,hot),'CONSIDER_PRECOOLING')
        for i in range(2,5):self.assertEqual(a.update(T+i*900,cool),'CONSIDER_PRECOOLING')
        self.assertEqual(a.update(T+4500,cool),'MONITOR')
        a.update(T+5400,hot)
        self.assertEqual(a.update(T+7200,hot),'MONITOR')
    def test_weather_success_and_cache(self):
        import io
        payload={'hourly':{'time':[T+i*3600 for i in range(10)],
                          'temperature_2m':[30+i for i in range(10)],
                          'relative_humidity_2m':[60]*10}}
        with patch('urllib.request.urlopen',return_value=io.StringIO(json.dumps(payload))) as req, patch('time.time',return_value=T):
            weather=Macro()
            m=weather.get(T+1800)
            self.assertEqual(m['now'],30.5)
            self.assertEqual(m['2']['temp'],32.5)
            self.assertEqual(m['6']['hum'],60)
            weather.get(T+1800)
            self.assertEqual(req.call_count,1)
    def test_weather_failure_no_fabrication(self):
        with patch('urllib.request.urlopen',side_effect=OSError('offline')):
            self.assertIsNone(Macro().get(T))
    def test_purge_targets_and_gap(self):
        rows=history(1)
        ds=samples(rows,2)
        cut=T+30000
        tr=[s for s in ds if s[1]<cut]
        self.assertTrue(all(s[0]+7200<cut for s in tr))
        self.assertIsNone(features([rows[i] for i in [0,1,3,4,5]],2))
    def test_training_refuses_simulation(self):
        with self.assertRaises(ValueError):train([dict(r,source='simulation') for r in history(8)],'unused.pkl')

class IngestTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.s=Store(pathlib.Path(self.tmp.name)/'test.db')
        self.e=Engine(self.s,macro=NoMacro())
    def tearDown(self):
        self.s.close();self.tmp.cleanup()
    def test_dedup_and_restart(self):
        self.assertTrue(self.e.process(parsed()))
        self.assertFalse(self.e.process(parsed()))
        e=Engine(self.s,macro=NoMacro())
        self.assertFalse(e.process(parsed(seq=2,timestamp=T-10)))
        self.assertEqual(self.s.db.execute('SELECT count(*) FROM raw').fetchone()[0],2)
    def test_bucket_and_gap(self):
        base=(T//900)*900
        for i in range(91):
            p=decode(json.dumps(packet(seq=i,timestamp=base+i*10)),received=base+i*10)
            self.e.process(p)
        rows=self.s.history()
        self.assertEqual(len(rows),1)
        self.assertTrue(rows[0]['valid'])
        r=json.loads(self.s.db.execute('SELECT payload FROM results').fetchone()[0])
        self.assertEqual(r['forecasts']['2']['method'],'persistence_baseline')
    def test_score_recorded_forecast(self):
        from evaluate import evaluate
        r=dict(node_id='node4',ts=T,source='hardware',valid=True,temperature_c=30,humidity=60)
        pred=dict(node_id='node4',ts=T,source='hardware',forecasts={'2':dict(temp=32,temp_p80=34,method='test')})
        self.s.bucket(r,pred)
        later=dict(r,ts=T+7200,temperature_c=33)
        self.s.bucket(later,dict(pred,ts=T+7200,forecasts={}))
        out=evaluate(pathlib.Path(self.tmp.name)/'test.db')['node4 / +2h / test']
        self.assertEqual(out['n'],1)
        self.assertEqual(out['mae_c'],1)
        self.assertEqual(out['persistence_mae_c'],3)
        self.assertEqual(out['p80_coverage'],1)
    def test_missing_sensor_and_sparse_not_forecast(self):
        base=(T//900)*900
        for i in range(2):
            self.e.process(decode(json.dumps(packet(seq=i,timestamp=base+i*900,temperature_c=None)),received=base+i*900))
        self.assertFalse(self.s.history()[0]['valid'])
        r=json.loads(self.s.db.execute('SELECT payload FROM results').fetchone()[0])
        self.assertEqual(r['advisory'],'INSUFFICIENT_DATA')

def history(days):
    rows=[]
    for i in range(days*96):
        ts=T+i*900
        temp=29+4*math.sin(i*2*math.pi/96)
        m={'provider':'openmeteo','now':temp-1,'fetched_at':ts,
           **{str(h):{'temp':29+4*math.sin((i+h*4)*2*math.pi/96),'hum':60} for h in config.HORIZONS}}
        rows.append(dict(node_id='node4',ts=ts,source='hardware',valid=True,temperature_c=temp,
                         humidity=60,lux=200,edge_anomaly=0,macro=m))
    return rows

@unittest.skipUnless(os.getenv('AEROCLIM_TEST_ML')=='1','enable optional model integration test')
class ModelTest(unittest.TestCase):
    def test_fit_save_load_infer(self):
        with tempfile.TemporaryDirectory() as td:
            path=pathlib.Path(td)/'model.pkl'
            rows=history(9)
            report=train(rows,path)
            self.assertEqual(set(report['horizons']),{'2','4','6'})
            fc=Forecaster(path)
            for r in rows[-5:]:pred=fc.predict(r)
            self.assertEqual(pred['2']['method'],'trained_real_quantiles')
            self.assertGreaterEqual(pred['2']['temp_p80'],pred['2']['temp'])

if __name__=='__main__':unittest.main()
