# Review and changes from the supplied v2 source

The original Holt approach and regional-offset forecasting concept were useful. The urgent work was the transition from a ghost node to physical sensors, trustworthy timing and a testable end-to-end system.

| Finding in supplied material | v3 response |
|---|---|
| Firmware task still described replacing simulated readings; no actual Arduino sketch in the combined source | New real DHT22/VEML7700/PMS5003/MQ voltage sketch |
| MQ claimed as CO₂ ppm without provided calibration | Explicit uncalibrated voltage channel; no ppm claim |
| 10k/20k divider has little/no high-end voltage margin | Physical divider check and proposed 20k/10k rework; initially disabled channel |
| PMS connected to UART0 pins shared with USB bridge | Explicit conflict check and configurable isolated RX-only jumper path |
| Notes omit GPIO4/5 from strapping pins | Corrected hardware checklist |
| Original median-labelled model used squared-error objective | Actual 0.5 and 0.8 quantile temperature objectives |
| Training split allowed targets to extend into the holdout period | Purge by target time for each horizon |
| Forecast lags depended on packet cadence | Fixed 15-minute buckets and continuity requirements |
| Macro failure could silently substitute synthetic/climatology values | Explicit missing weather and labelled baseline; no synthetic live fallback |
| Simulation-generated model could bootstrap live operation | Live starts with explicit baselines; real models train only on hardware buckets |
| Naive local timestamp strings | UTC Unix seconds plus receive-time fallback quality |
| MQTT callback performed weather/inference/storage inline | Bounded queue, main-thread processing, reconnect callbacks |
| Duplicate/out-of-order data reset state | Persistent deduplication and no forecast rewind |
| UI could keep an old cooling state visible | Telemetry/forecast freshness checks and stale advisory suppression |
| Heat-index floor mixed into the physical heat-index function | Raw heat-index calculation and separately named CDI floor |
| “Upper bound” could imply a confidence interval | Explicit empirical temperature p80 and CDI risk-proxy language |
| Unspecified physical actuator | Advisory only; no relay/HVAC command code invented |

## Deliberate scope choices

This is a Wi-Fi-to-MQTT star network, not an implemented Thread/Zigbee mesh. It uses the C6's Wi-Fi capability; the existence of an 802.15.4 radio does not make a mesh. No energy-savings percentage, real-world model accuracy or physical sensor calibration is claimed.

The default Python model is scikit-learn to make installation simpler. XGBoost quantile regression remains available as an explicit optional backend. The original simulated model pickle is neither required nor reused. No attempt is made to import the old v2 SQLite table automatically: retain the original files separately and use the new database path.

The package does not add OTA updates, flash wear from high-frequency writes, a relay driver, or an uncontrolled internet-facing broker. Those require their own hardware and operational design. Sensor thresholds should be tuned only after collecting stable real readings; changing the algorithm cannot compensate for direct-sun DHT bias or a sensor heated by its neighbor.

## References for software methods

- NWS heat-index computation: https://www.wpc.ncep.noaa.gov/html/heatindex_equation.shtml
- NWS heat-index interpretation: https://www.weather.gov/ama/heatindex
- Open-Meteo forecast API: https://open-meteo.com/en/docs
- scikit-learn quantile loss: https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingRegressor.html
- XGBoost quantile regression: https://xgboost.readthedocs.io/en/stable/python/examples/quantile_regression.html
- Paho MQTT client: https://github.com/eclipse-paho/paho.mqtt.python

Open-Meteo provides regional weather data. Check its current service terms and attribution requirements for your deployment; the dashboard visibly credits it.
