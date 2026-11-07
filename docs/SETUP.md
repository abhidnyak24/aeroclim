# AeroClim v3 — hardware and PC setup

This guide is adapted from the original v3 package. Commands run from the repository root; firmware settings now use an ignored `config.local.h`. See [the repository README](../README.md) for the browser demo and folder layout.

Prepared for Abhidnya Kulkarni / Team Scavengers · 3 November 2026.

This replaces the supplied Python v2 stack with a coordinated v3 firmware, collector, dashboard and training pipeline. It is designed for your ESP32-C6-DevKitM-1-N4 carrier, based on the written pin map. Your PCB schematic, netlist, actual sensor labels and voltage measurements were not supplied, so electrical compatibility still needs the checks below. **Read `docs/HARDWARE.md` before powering the fully populated board.**

## Start here

1. Check the MQ divider and PMS UART wiring in `docs/HARDWARE.md`. Initially disconnect the MQ analog output and PMS UART from the ESP physically. A software disable cannot stop an unsafe voltage or two outputs fighting each other.
2. Install Python **3.11 or 3.12** and Arduino IDE 2.x. Open this extracted folder in a terminal.
3. Install the PC packages using the commands below.
4. Open `firmware/AeroClimNode/AeroClimNode.ino`, select **ESP32C6 Dev Module**, enable **USB CDC On Boot**, flash using the board's **native ESP32 USB connector**. Default settings run DHT22 + VEML7700 only, with USB JSON output every 10 seconds.
5. Start USB collection, then the dashboard. Confirm readings, then enable each remaining sensor after its physical wiring check.
6. For normal wireless operation, configure Wi-Fi + a local MQTT broker. Do not run two collectors against the same database.

## PC installation — Windows PowerShell

Run from the repository root. Activation is optional; these commands call the environment directly.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r pc\requirements.txt
```

Use `py -3.12` if that is the installed version. For Linux/macOS:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r pc/requirements.txt
```

### First test: USB, no broker or Wi-Fi needed

Close Arduino Serial Monitor before the collector opens the same COM port. Substitute the native USB port shown on your PC:

```powershell
.\.venv\Scripts\python.exe pc\cloudengine.py --serial COM5
```

In another terminal, from the same folder:

```powershell
.\.venv\Scripts\python.exe -m streamlit run pc\dashboard.py
```

Open the URL Streamlit prints (usually http://localhost:8501). The collector prints a connection message; the dashboard shows raw data within approximately 10 seconds. Forecasts wait for a sufficiently complete 15-minute bucket to close, so the first usable forecast can take up to 30 minutes. Firmware with no NTP clock sends `timestamp: null`; the PC records reception UTC and labels that clock quality.

On Linux use `.venv/bin/python` and a port such as `/dev/ttyACM0`. With several nodes, MQTT is the supported multi-node collector; USB accepts one port per process.

### Offline demonstration

```powershell
.\.venv\Scripts\python.exe pc\cloudengine.py --simulate
.\.venv\Scripts\python.exe -m streamlit run pc\dashboard.py
```

Run those in separate terminals. Enable **Demo data** in the dashboard. This uses `data/demo.sqlite3`, labels all telemetry as simulation, and never loads a real model. It advances one simulated 10-second sample every 0.05 real seconds. To run a bounded demo: `--simulate --ticks 200 --speed 0`. Restarting starts a new simulated stream; older rows remain, and overlapping timestamps are stored but do not rewind the forecast engine.

### Wireless operation

The default PC broker is localhost; the ESP must use the **PC's LAN IPv4 address**.

1. Install Docker Desktop if you want the supplied broker, then run `docker compose up -d` in this folder. Alternatively install Mosquitto yourself and supply equivalent settings. Docker is unnecessary for USB or offline mode.
2. Keep both devices on the same trusted network. Find the PC's Wi-Fi IPv4 with `ipconfig`. Allow inbound TCP 1883 for the private network in the firewall. Networks with client isolation may block this.
3. Copy `firmware/AeroClimNode/config.example.h` to `config.local.h` in the same directory, then edit the local file: `ENABLE_WIFI 1`, SSID/password, `MQTT_HOST` = PC IPv4. The C6 uses 2.4 GHz Wi-Fi. Set a unique `NODE_ID` on every board. Flash again.
4. Stop the USB collector and run `.\.venv\Scripts\python.exe pc\cloudengine.py`.
5. Topic root is `aeroclim/lab` on both sides. Override the PC with `$env:AEROCLIM_TOPIC_ROOT="aeroclim/your-project"` and match the firmware.

The supplied broker permits anonymous lab LAN access. Do not expose it to the internet. For a remote broker, enable TLS on both sides, supply the correct root CA and credentials, and configure broker ACLs. A unique topic root is a namespace, not authentication. Firmware never disables TLS verification. NTP must work before TLS can connect.

### Firmware libraries and board settings

Boards Manager: **esp32 by Espressif Systems** (3.x; see `docs/VALIDATION.md` for the version actually tested). Libraries:

- ArduinoJson 7.x
- PubSubClient 2.8
- DHT sensor library by Adafruit, plus Adafruit Unified Sensor
- Adafruit VEML7700, plus Adafruit BusIO

Choose **ESP32C6 Dev Module**, 4 MB flash, USB CDC On Boot **Enabled**, CPU/default partition settings unchanged. The sketch intentionally refuses compilation without USB CDC. Use the native USB connector (GPIO12/13), not the UART bridge connector. If first flashing fails: hold BOOT, tap RESET, release BOOT, then select the reappeared USB port and upload. Do not burn eFuses as a troubleshooting step.

`config.local.h` contains your settings and credentials and is ignored by Git. The tracked `config.h` selects this local profile when present, or the credential-free example otherwise. There is no shipped firmware binary: compile your own configuration.

## Real forecasting and training

Immediately usable modes:

- **Regional offset baseline:** Open-Meteo's regional temperature forecast plus a decaying local offset, with regional forecast humidity. A hand-designed baseline, not trained AI.
- **Persistence baseline:** if regional weather is unavailable, holds current local temperature/humidity. Clearly labelled, with no invented uncertainty bound.
- **Trained real quantiles:** after you train on collected hardware data, direct +2/+4/+6-hour local-offset models predict temperature median and 80th percentile plus median humidity. Only nodes present in the training set use the model. Others stay on baselines.

The collector requests regional forecasts automatically, caches for 30 minutes, and rejects the cache after one hour. Outage does not stop raw collection. Set `$env:AEROCLIM_MACRO="off"` for completely offline USB collection; such buckets cannot train the regional-offset model. Default coordinates are 18.6298, 73.7997; change `AEROCLIM_LAT` and `AEROCLIM_LON` to your actual deployment. Regional values are forecasts/model output, not a nearby physical weather-station measurement.

Collect at least 7 full days **and** 672 valid weather-backed buckets per eligible node; 2–4 weeks across varied conditions is preferable. Stop the collector, then:

```powershell
.\.venv\Scripts\python.exe pc\cloudengine.py --retrain-db
```

This writes `data/real_model.pkl` and `data/real_model.report.json`. Restart the collector to load it. Default scikit-learn uses quantile gradient boosting; optional XGBoost:

```powershell
.\.venv\Scripts\python.exe -m pip install -r pc\requirements-xgboost.txt
.\.venv\Scripts\python.exe pc\cloudengine.py --retrain-db --backend xgboost
```

Only load model files you trained yourself: pickle is executable, not a safe exchange format. Preserve the training environment because models depend on library versions. Inspect the report: time-ordered last-20% evaluation, horizon-specific purge, temperature MAE versus persistence/regional baselines, empirical temperature-p80 coverage and CDI alert precision/recall/F1. No guarantee that the trained model improves either baseline; the report explicitly flags the comparison. Do not describe synthetic test data or the old simulated metrics as real validation.

To score forecasts that were actually issued against later hardware observations, run `python pc/evaluate.py` with the same environment/database. It reports per-node/horizon/method MAE, persistence MAE and observed p80 coverage. No future target yet means no scored pair.

The thermal index is the NWS heat-index approximation. **CDI is separately defined as max(air temperature, heat index)** and is a project-specific °C proxy, not energy demand. Heat index describes shaded conditions and does not capture radiant heat. The p80-temperature/median-humidity CDI value is a risk proxy, **not** a calibrated p80 CDI. Defaults are prototype thresholds: enter at ≥42 °C on two consecutive 15-minute buckets; release below 40 °C on three consecutive buckets after at least 60 minutes. Only the 2-hour forecast drives the software suggestion. There is no relay/HVAC actuator in your supplied hardware map, so this package sends no physical cooling commands.

## What is inside

| Path | Purpose |
|---|---|
| `firmware/AeroClimNode/` | C6 sketch, editable configuration, PMS parser, Holt filter |
| `pc/cloudengine.py` | USB / MQTT collector and training CLI |
| `pc/dashboard.py` | Live measurements, freshness, faults, forecasts, CSV export |
| `pc/protocol.py`, `store.py`, `engine.py` | Validation, deduplication, SQLite, aggregation |
| `pc/forecasting.py`, `macro.py`, `thermal.py` | Real model training, weather snapshots, thermal calculations |
| `pc/simulator.py` | Offline demo in a separate database |
| `docs/HARDWARE.md` | Required electrical checks, pin mapping, bring-up sequence |
| `docs/PROTOCOL.md` | Wire contract and data behavior |
| `docs/CHANGES.md` | Review of the old design and changes |
| `docs/VALIDATION.md` | Test results and limits of verification |
| `tests/` | Python integration tests and native C++ firmware-core tests |
| `compose.yaml`, `broker/` | Optional local Mosquitto broker |

For the exact direct Python package versions used here, install `pc/requirements-tested.txt` instead of the ranged requirements file. Arduino CLI users can use `scripts/compile_firmware.sh` to reproduce the pinned firmware build.

## Tests and backups

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
$env:AEROCLIM_TEST_ML="1"
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The ML integration test uses deterministic fixtures solely to check the training/inference path; it is not a performance benchmark. If a C++ compiler is available:

```bash
g++ -std=c++11 -Wall -Wextra -Werror -pedantic tests/test_firmware.cpp -o /tmp/aeroclim-core-test
/tmp/aeroclim-core-test
```

Raw data is retained indefinitely. At a 10-second cadence there are 8,640 rows/day/node; watch disk usage. Stop the collector and dashboard before copying the `data` folder, or use SQLite's online backup API. Do not copy only a live WAL database's main file. No automatic reset/deletion is performed. For a fresh run use `AEROCLIM_DB` with a new absolute path in both terminals.

## Limits to know

The firmware publishes best-effort MQTT QoS0 and does not buffer telemetry across outages or resets. USB logs remain available while Wi-Fi fails, but are only saved if a collector is attached. Sequence numbers expose gaps. A collector restart discards its partial current bucket and begins fresh; raw rows remain. Advisory state restarts at MONITOR. Edge detector state resets on MCU restart, with six complete 15-minute windows needed before anomaly detection. The dashboard suppresses stale advisories. Physical environmental accuracy, power stability, airflow, enclosure, sensor placement and forecasting accuracy need real bench/field measurements.
