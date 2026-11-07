"""Read-only live view; deliberately no actuator controls."""
import json
import sqlite3
import time
from datetime import datetime,timezone
import pandas as pd
import streamlit as st
import config
from thermal import heat_index_c,cdi
st.set_page_config(page_title='AeroClim',page_icon='🌤️',layout='wide')
st.title('AeroClim · Street-level climate intelligence')
st.caption('Team Scavengers · Sensor measurements, forecast provenance, and advisory cooling decisions')
demo=st.sidebar.toggle('Demo data',value=False)
path=config.DATA/'demo.sqlite3' if demo else config.DB
st.sidebar.code(str(path))
if demo:
    st.warning('SIMULATION — generated data, not measurements or validated model performance.')
st.sidebar.caption('Live freshness limit: 90 s. Forecast cadence: 15 minutes. Times displayed in UTC.')

@st.fragment(run_every=5)
def live():
    if not path.exists():
        st.info('Start the collector first. See README.md for USB, MQTT or offline demo commands.')
        return
    db=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=5)
    try:
        nodes=[x[0] for x in db.execute('SELECT DISTINCT node FROM raw ORDER BY node')]
        if not nodes:
            st.info('Waiting for the first valid telemetry packet…')
            return
        node=st.selectbox('Node',nodes)
        rec=db.execute('SELECT payload FROM raw WHERE node=? ORDER BY ts DESC LIMIT 1',(node,)).fetchone()
        p=json.loads(rec[0])
        age=max(0,time.time()-p['received'])
        fresh=age<=config.STALE
        st.success(f'LIVE · last received {age:.0f}s ago') if fresh else st.error(f'STALE · no new telemetry for {age:.0f}s')
        cols=st.columns(4)
        for col,key,label,unit in zip(cols,('temperature_c','humidity','lux','pm25_ugm3'),
                                     ('Temperature','Humidity','Light','PM₂.₅'),('°C','%','lx','µg/m³')):
            v=p.get(key)
            col.metric(label,'Unavailable' if v is None else f'{v:.1f} {unit}')
        if p.get('temperature_c') is not None and p.get('humidity') is not None:
            a,b=st.columns(2)
            a.metric('Heat index (shade)',f"{heat_index_c(p['temperature_c'],p['humidity']):.1f} °C")
            b.metric('CDI · project proxy',f"{cdi(p['temperature_c'],p['humidity']):.1f} °C")
        st.caption('MQ-135 is an uncalibrated gas-response channel, not CO₂ ppm. Light and PM are contextual; they do not directly modify CDI.')
        st.write({'MQ ADC (mV)':p.get('mq_adc_mv'),'MQ warm':p.get('mq_warm'),
                  'edge anomaly':p.get('edge_anomaly'),'clock':p.get('time_quality'),
                  'Wi-Fi RSSI':p.get('rssi_dbm'),'sensor status':p.get('status',{})})
        rr=db.execute('SELECT payload FROM results WHERE node=? ORDER BY ts DESC LIMIT 1',(node,)).fetchone()
        if rr:
            r=json.loads(rr[0])
            forecast_fresh=fresh and (demo or time.time()-r['ts']<=1200)
            st.subheader(r['advisory'] if forecast_fresh else 'ADVISORY UNAVAILABLE · stale input')
            st.caption('Software recommendation only. No HVAC commands are sent. Two consecutive 15-minute high buckets enter the advisory.')
            if r['forecasts'] and forecast_fresh:
                frame=pd.DataFrame.from_dict(r['forecasts'],orient='index')
                frame.index=['+'+h+' hours' for h in frame.index]
                st.dataframe(frame.round(2))
                st.caption('temp_p80 is a one-sided empirical model quantile. CDI risk proxy combines temperature p80 with median humidity; it is not CDI p80 or a confidence interval.')
        else:
            st.info('Forecasts appear after a sufficiently complete 15-minute bucket closes. Allow up to 30 minutes on first start.')
        rows=[json.loads(x[0]) for x in db.execute('SELECT payload FROM raw WHERE node=? ORDER BY ts DESC LIMIT 8640',(node,))]
        frame=pd.DataFrame(rows).sort_values('timestamp')
        frame['UTC']=pd.to_datetime(frame['timestamp'],unit='s',utc=True)
        left,right=st.columns(2)
        left.caption('Temperature · °C')
        left.line_chart(frame.set_index('UTC')[['temperature_c']])
        right.caption('Relative humidity · %')
        right.line_chart(frame.set_index('UTC')[['humidity']])
        st.download_button('Download displayed readings (CSV)',frame.drop(columns=['status'],errors='ignore').to_csv(index=False),
                           file_name=f'{node}-telemetry.csv',mime='text/csv')
        with st.expander('Diagnostics and latest packet'):
            st.json(p)
            events=pd.read_sql_query('SELECT * FROM events ORDER BY ts DESC LIMIT 30',db)
            st.dataframe(events)
        report=config.MODEL.with_suffix('.report.json')
        if not demo and report.exists():
            with st.expander('Real-data model validation report'):
                st.json(json.loads(report.read_text()))
    finally:
        db.close()
live()
st.caption('Regional weather: Open-Meteo (when available). Heat index excludes solar radiation and wind. CDI thresholds are prototype settings, not measured HVAC energy demand.')
