# Architecture

AeroClim contains two independent software implementations that share the project idea, plus a collection of hardware design files.

## Browser demo

`Regional/manual weather → generated local profiles → ridge forecasts → cooling planner → dashboard/export`

The standalone page contains its styling, JavaScript, chart rendering and seeded training data generator. No build tool or external JavaScript library is required. Open-Meteo supplies regional weather when requested; manual conditions support offline use. The four campus locations are illustrative profiles.

Three standardized ridge models learn local temperature corrections for +2, +4 and +6 hours. Twelve features plus an intercept per model produce 39 coefficients. The 16-day generated dataset is divided chronologically into 12 training days and 4 test days; targets crossing the boundary are purged. The workbench compares MAE with regional weather and persistence, shows model arithmetic, and allows an isolated input experiment.

Forecast points are interpolated for a six-hour room simulation. A beam search retains up to 40 candidate temperature-bin paths and chooses among off/half/full cooling for 24 quarter-hour intervals. This approximate optimizer trades comfort penalties, tariff cost and switching penalties. It does not guarantee a globally optimal plan or field energy savings.

An adaptive statistical detector tracks level and trend and confirms spikes after two unusual readings. The detector and optimizer are distinct from the trained regression models.

The page stores its selected region/weather in localStorage. Run exports include location and model/scenario details. The input experiment changes the workbench preview, while the forecast-mode switch changes the dashboard/planner scenario.

## Firmware and Python

`Sensors → ESP32-C6 JSON → USB or MQTT → validation → SQLite → 15-minute buckets → forecast/advisory → Streamlit`

- `firmware/AeroClimNode/`: sensor reads, device identity, JSON telemetry, PMS frame parsing and an edge anomaly filter. Native USB is the initial transport; Wi-Fi/MQTT is optional.
- `pc/protocol.py`: payload validation and identity checks.
- `pc/store.py` and `pc/engine.py`: raw storage, deduplication, aggregation and forecast results.
- `pc/macro.py`: cached regional forecast snapshots.
- `pc/forecasting.py`: regional-offset/persistence baselines, trained quantile forecasts and advisory hysteresis.
- `pc/cloudengine.py`: USB/MQTT collection, simulation and training entry point.
- `pc/evaluate.py`: read-only scoring of issued forecasts against later hardware buckets.
- `pc/dashboard.py`: Streamlit measurements, forecasts, freshness and export UI.

Hardware model training requires eligible collected history, with at least seven days and 672 valid weather-backed buckets per node. It uses chronological, purged evaluation and reports baseline comparisons. The default backend is scikit-learn quantile gradient boosting; XGBoost is optional. Simulation data is excluded from real training and uses its own database.

Advisories are software suggestions based on the two-hour forecast. There is no physical HVAC actuator or bridge from this collector to the browser demo.

## Hardware revision boundary

Read [hardware/README.md](../hardware/README.md) for recovered files and mismatched dates. Read [HARDWARE.md](HARDWARE.md) before bring-up. File inclusion and software tests do not establish electrical compatibility or a verified production revision.
