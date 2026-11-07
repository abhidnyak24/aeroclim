# Validation record — 3 November 2026

## Completed software checks

- Python regression/integration tests: **16 cases passed**, comprising the full initial 14-case suite plus two added weather-success and issued-forecast scoring cases run individually. Covers invalid data, null sensor values, UTC receive-time fallback, topic identity, duplicates, out-of-order/restart handling, incomplete buckets, 15-minute aggregation, advisory hysteresis/gap reset, NWS reference examples, weather failure/cache behavior, training continuity and simulation exclusion.
- scikit-learn model fit → report → save → load → inference passed using deterministic fixtures. XGBoost CPU quantile fit/save/load/inference also passed in a separate integration check. These fixtures validate execution, **not real-world predictive accuracy**.
- Native C++ core tests passed with `g++ -std=c++11 -Wall -Wextra -Werror -pedantic`: valid environmental PM extraction, checksum rejection, resynchronization after corruption, sensor-error rejection, Holt confirmation and sustained-regime reset.
- USB collector integration passed through an OS pseudo-terminal: boot diagnostic, valid JSON, duplicate and out-of-range humidity. One valid raw record was stored.
- MQTT collector integration passed against a temporary local AMQTT broker: valid reception, deduplication, topic/payload mismatch and invalid sensor rejection. This tests the Paho transport path, not ESP radio operation or the supplied Docker broker image.
- Offline fleet demo ran for 200 accelerated ten-second steps for three nodes, producing raw data and completed forecast buckets.
- Streamlit AppTest passed for an empty live database and populated demo database, including six measurement metrics and forecast/diagnostic tables. This is a component execution check, not a physical browser rendering review.
- Python source compilation passed.
- Live Open-Meteo access timed out in the build environment. The successful response/interpolation/cache path is tested with a fixture; the outage path was observed to return no weather and preserve the baseline behavior. Live API connectivity remains to be verified on your PC.

## Full ESP32-C6 compile

Actual target: `esp32:esp32:esp32c6:CDCOnBoot=cdc`, Espressif Arduino core **3.3.0**. Libraries: ArduinoJson **7.4.3**, PubSubClient **2.8.0**, DHT sensor library **1.4.7**, Adafruit Unified Sensor **1.1.15**, Adafruit VEML7700 **2.1.6**, Adafruit BusIO **1.17.4**.

| Configuration | Compile | Flash bytes / 1,310,720 | Static RAM bytes / 327,680 |
|---|---|---:|---:|
| Shipped USB bring-up defaults | Passed | 1,017,257 | 43,996 |
| Wi-Fi + MQTT + PMS + MQ | Passed | 1,048,485 | 44,484 |
| Wi-Fi + TLS + PMS + MQ | Passed | 1,144,087 | 45,052 |

The two enabled profiles were compiled from temporary copies. The delivered `config.h` retains the safer initial disabled Wi-Fi/PMS/MQ settings. TLS compile success does not verify a CA certificate or broker handshake. Flash counts exclude runtime heap requirements; TLS has runtime RAM costs. No physical MCU was attached, flashed or measured.

To reproduce the build, use `scripts/compile_firmware.sh` with Arduino CLI installed, or the documented Arduino IDE settings. It installs the pinned board/libraries and compiles only; it does not upload.

## Python dependency versions used

See `pc/requirements-tested.txt` for exact direct dependency versions. The normal `requirements.txt` uses compatible version ranges for installation. Use a dedicated virtual environment. Neither list is a full transitive lockfile; retain `pip freeze` output from your deployment if you need exact future reproduction.

## Still requires your bench/field test

- Actual PCB net continuity, resistor values, sensor model and bridge isolation.
- Upload and USB operation on your Windows machine and exact board revision.
- Physical readings, failed-sensor behavior and lux saturation on real sensors.
- PMS5003S compatibility if your unit is not the standard 32-byte PMS5003.
- Wi-Fi association/reconnection, MQTT/TLS handshake and radio behavior.
- Power rails under heater/fan/transmit load and long-duration stability.
- Weather API reachability and correct deployment coordinates.
- Real forecasting accuracy, threshold suitability and field calibration.
- Any HVAC integration or energy savings: not implemented or demonstrated by this package.

No physical-hardware readiness or real-world performance claim follows from passing these software checks.
