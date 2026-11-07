# AeroClim v3 data contract

## Transport

MQTT topic: `aeroclim/lab/<node_id>/telemetry` by default. The firmware also writes the same JSON as one line on native USB serial. Diagnostic lines start with `#`. Every 10 seconds a fresh packet is produced; MQTT telemetry is non-retained QoS0. MQTT status is retained on `<root>/<node>/status`, with an offline last will. The dashboard uses received telemetry age rather than trusting retained status. The collector ignores retained telemetry.

```json
{
  "schema": 3,
  "source": "hardware",
  "node_id": "node4",
  "boot_id": "a1b2c3d4e5f60708",
  "seq": 42,
  "timestamp": 1793700000,
  "temperature_c": 30.2,
  "humidity": 48.0,
  "lux": 750.0,
  "pm1_ugm3": 10,
  "pm25_ugm3": 18,
  "pm10_ugm3": 22,
  "mq_adc_mv": 950,
  "mq_ao_mv": 2850,
  "mq_warm": true,
  "edge_anomaly": 0,
  "rssi_dbm": -58,
  "status": {"dht":"ok","light":"ok","pms":"ok","mq":"uncalibrated_voltage"}
}
```

The example timestamp is illustrative; a live packet must match PC time within 120 seconds. Timestamp is UTC Unix seconds, **not** a naive local string. An unsynchronized MCU sends null and the collector uses received time. Source must be hardware in live collection; simulation is accepted only by the separate simulator. Neither source nor node ID is cryptographic authentication—use a trusted broker and credentials/ACLs when needed.

Node/boot IDs: 1–40 ASCII letters, digits, underscore or hyphen. Sequence: unsigned 32-bit integer per boot. The firmware creates a random boot ID on startup. Each `(node_id, boot_id, seq)` is unique in SQLite. Duplicate messages have no forecasting effect. Delayed/non-increasing timestamps can be retained for diagnostics but never rewind inference. Node identity must match the MQTT topic.

All sensor numbers are finite and range-checked. Missing/failed sensors use JSON null. There is no `co2_ppm` conversion. Optional health fields include uptime, free heap, PMS good/bad frame counts, MQTT failures and completed edge windows. A status label explains why a channel is null.

## Storage and aggregation

- `raw`: exact validated payload plus receive time and normalized time quality. Deduplicated primary key.
- `buckets`: 15-minute UTC wall-clock aggregates timestamped at the **end** of the interval. A bucket closes on the next observed interval; no forecast is produced from a still-open bucket.
- `results`: forecasts and advisory for that bucket.
- `events`: rejections and out-of-order diagnostics.

A bucket needs at least 30 valid temperature/RH observations spanning at least 600 seconds, with no inter-observation gap above 90 seconds. Failed intervals are recorded as invalid and reset the model feature warmup. Means use only packets with valid temperature and RH; optional channels additionally exclude null. Missing optional light is represented with an explicit missing feature. There is no interpolation across absent buckets.

The model needs five consecutive valid 15-minute buckets for lag features. Regional snapshots are captured when the bucket closes, not fetched retroactively during training. Forecast targets match exact future bucket times, not row offsets. The time split purges any training example whose target reaches the holdout period, preventing overlap leakage. Gaps reduce usable data; row count alone does not establish readiness.

All timestamps are UTC. Dashboard labels UTC explicitly. The firmware Holt filter uses separate 15-minute **uptime-based** means; its windows need not align with the PC's UTC buckets. It resets after insufficient coverage and requires six complete windows of warmup. This is a positive temperature-residual detector, not a general gas/PM anomaly classifier.

## Fault and restart behavior

No DHT reading: store packet and health status; omit temperature-dependent computations. No PMS frame: null after 10 seconds, never stale PM. No weather: baseline persistence, no synthetic weather, no uncertainty claim. No network: sensors and USB continue; MQTT reconnects with bounded retry intervals. Individual connection attempts can briefly block (PubSubClient is synchronous); the PMS receive buffer reduces but does not eliminate possible serial loss.

No collector: firmware samples are not buffered. No new telemetry: dashboard marks stale after 90 seconds and hides the advisory. Collector restart: warmup restarts, partial bucket is discarded, and historical completed buckets/raw telemetry remain. Model files are loaded only at collector startup. Use one writer per database and do not mix old v2 databases with v3.
