"""Transport callbacks enqueue only; all weather, inference and SQLite run in the main thread."""
import argparse
import json
import logging
import queue
import time
import config
from protocol import decode
from engine import Engine
from store import Store

def run_mqtt(engine):
    import paho.mqtt.client as mqtt
    q=queue.Queue(maxsize=1000)
    client=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,client_id='aeroclim-pc-'+str(time.time_ns()))
    if config.USER:
        client.username_pw_set(config.USER,config.PASSWORD)
    if config.TLS:
        client.tls_set(ca_certs=config.CA)
    client.reconnect_delay_set(1,60)
    def connected(c,userdata,flags,reason,properties):
        if reason.is_failure:
            logging.error('Broker rejected connection: %s',reason)
        else:
            c.subscribe(config.ROOT+'/+/telemetry',qos=1)
            logging.info('MQTT connected, subscribed %s/+/telemetry',config.ROOT)
    def message(c,userdata,msg):
        if msg.retain: # Telemetry must describe a new live observation
            return
        try:
            if len(msg.payload)>8192:
                raise ValueError('oversize message')
            suffix=msg.topic[len(config.ROOT)+1:]
            parts=suffix.split('/')
            if len(parts)!=2 or parts[1]!='telemetry':
                raise ValueError('invalid topic')
            q.put_nowait((msg.payload,parts[0],time.time()))
        except (ValueError,queue.Full) as e:
            logging.warning('MQTT dropped: %s',e)
    client.on_connect=connected
    client.on_message=message
    client.connect_async(config.BROKER,config.PORT,60)
    client.loop_start()
    logging.info('Connecting to %s:%s',config.BROKER,config.PORT)
    try:
        while True:
            try:
                raw,node,received=q.get(timeout=1)
            except queue.Empty:
                continue
            try:
                engine.process(decode(raw,node,received))
            except (ValueError,TypeError,UnicodeError) as e:
                logging.warning('Rejected telemetry: %s',e)
                engine.store.event(received,'reject',str(e))
    finally:
        client.disconnect()
        client.loop_stop()

def run_serial(engine,port):
    import serial
    while True:
        try:
            with serial.Serial(port,115200,timeout=2) as ser:
                logging.info('USB serial connected: %s',port)
                while True:
                    raw=ser.read_until(b'\n',8193)
                    if not raw:
                        continue
                    if not raw.endswith(b'\n'):
                        ser.reset_input_buffer()
                        continue
                    if not raw.startswith(b'{'):
                        logging.info('ESP: %s',raw.decode(errors='replace').strip())
                        continue
                    try:
                        engine.process(decode(raw))
                    except (ValueError,TypeError,UnicodeError) as e:
                        logging.warning('Rejected serial telemetry: %s',e)
        except serial.SerialException as e:
            logging.warning('USB unavailable (%s); retry in 3s',e)
            time.sleep(3)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--serial',help='Native USB COM port, e.g. COM5 or /dev/ttyACM0')
    ap.add_argument('--db',default=str(config.DB))
    ap.add_argument('--simulate',action='store_true')
    ap.add_argument('--ticks',type=int,default=0,help='Demo only; 0 = indefinitely')
    ap.add_argument('--speed',type=float,default=.05,help='Demo seconds per simulated 10s')
    ap.add_argument('--retrain-db',action='store_true')
    ap.add_argument('--backend',choices=['sklearn','xgboost'],default='sklearn')
    a=ap.parse_args()
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    if a.simulate and a.retrain_db:
        ap.error('simulation cannot be used for real training')
    if a.simulate:
        from simulator import run
        run(a.ticks,a.speed)
        return
    store=Store(a.db)
    try:
        if a.retrain_db:
            from forecasting import train
            print(json.dumps(train(store.history(),config.MODEL,a.backend),indent=2))
            return
        engine=Engine(store,config.MODEL)
        run_serial(engine,a.serial) if a.serial else run_mqtt(engine)
    except KeyboardInterrupt:
        logging.info('Stopped. Partial current bucket is not used for forecasting.')
    finally:
        store.close()
if __name__=='__main__':
    main()
