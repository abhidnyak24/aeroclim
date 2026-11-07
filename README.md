# AeroClim

**Local heat forecasting, an interactive AI workbench, and an ESP32 sensing platform.**

AeroClim estimates how conditions at a particular location differ from regional weather, then uses the forecast to explore cooling decisions. Developed by **Abhidnya Kulkarni / Team Scavengers**.

This repository brings together the latest browser dashboard, the v3 hardware/PC software, and available carrier PCB files.

## Try the browser demo

Open [demo/index.html](demo/index.html) in a modern browser. There is no build step, API key, or JavaScript dependency to install. Download or clone the repository first; GitHub's file viewer displays source rather than running the page.

For a local web server, run from the repository root:

```sh
python -m http.server 8000 --bind 127.0.0.1
```

Then visit **http://localhost:8000/demo/**. Manual scenarios work offline; loading regional weather requires internet access to Open-Meteo.

1. Choose a location or manual weather conditions.
2. Inspect the asphalt court, shaded garden, library roof, or walkway profile.
3. Open the AI workbench and retrain the three models.
4. Compare learned local forecasts with regional weather and persistence baselines.
5. Change an input, inspect the learned calculation, and explore the six-hour cooling plan.
6. Export a run to save its inputs, model details, and calculated results.

## Two software paths

| | Browser demo | Hardware / PC system |
| --- | --- | --- |
| Entry point | `demo/index.html` | `pc/cloudengine.py` and `pc/dashboard.py` |
| Measurements | Generated local profiles with regional or manual weather | ESP32 USB/MQTT telemetry; separate offline simulator |
| Learning | Three ridge regressions, 12 features and 39 total coefficients | Quantile gradient boosting trained on collected hardware history |
| Forecast horizons | 2, 4 and 6 hours | 2, 4 and 6 hours |
| Decisions | Six-hour cooling schedule in a mathematical room model | Forecast-based precooling advisories |
| Interface | Self-contained HTML dashboard and AI workbench | Streamlit dashboard |

These are separate implementations. The browser dashboard does not currently receive PCB telemetry, and neither path controls a physical air conditioner.

## How the browser AI works

`Regional forecast + learned local correction → local temperature forecast → cooling plan`

The browser generates 16 days of deterministic example history. It trains on the first 12 days and evaluates on the remaining 4, excluding training examples whose future targets cross the split. Each horizon has its own ridge regression. The workbench shows MAE, fitted coefficients, and contributions calculated from those coefficients.

The cooling planner explores 24 quarter-hour decisions at 0%, 50%, or 100% cooling with an approximate beam search. It balances comfort, assumed electricity prices, and switching penalties. The adaptive heat-spike detector requires two consecutive unusually high readings.

Demo metrics describe generated examples and a simulated room. Real prediction quality and energy savings require field measurements. See [architecture and data flow](docs/ARCHITECTURE.md).

## Run the Python system

Use Python **3.11 or 3.12**. From the repository root on Windows:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r pc\requirements-tested.txt
.\.venv\Scripts\python.exe pc\cloudengine.py --simulate
```

In another terminal:

```powershell
.\.venv\Scripts\python.exe -m streamlit run pc\dashboard.py
```

Enable **Demo data** in the dashboard. Simulation uses a separate database. On macOS/Linux, create the environment with `python3 -m venv .venv` and use `.venv/bin/python`.

For USB collection, replace `--simulate` with `--serial COM5` using your board's actual port. Follow the [complete setup guide](docs/SETUP.md) for firmware, MQTT, deployment coordinates, real-data training, and evaluation.

## Firmware and PCB

The sketch targets the **ESP32-C6** and begins with native USB, DHT22 and VEML7700 enabled. PMS and MQ inputs require the physical checks described in [hardware bring-up](docs/HARDWARE.md).

Copy `firmware/AeroClimNode/config.example.h` to `config.local.h` in the same directory before entering Wi-Fi or MQTT credentials. The local file is ignored by Git and replaces the example profile. Without it, the sketch uses the shipped example defaults.

Available editable designs and manufacturing exports are in [hardware/](hardware/README.md). The October 7 manufacturing exports are newer than the recovered October 3 editable PCB. Their revision relationship is documented there.

## Repository layout

| Path | Contents |
| --- | --- |
| `demo/` | Latest standalone AI dashboard |
| `firmware/AeroClimNode/` | ESP32-C6 sketch, configuration and portable core |
| `pc/` | Collector, validation, storage, forecasting, simulator and dashboard |
| `hardware/` | EasyEDA snapshots, schematic image, BOM, placement and Gerbers |
| `docs/` | Setup, architecture, protocol, hardware and validation records |
| `tests/` | Python integration, portable C++ core and browser calculation tests |
| `broker/`, `compose.yaml` | Optional local Mosquitto broker |
| `.github/workflows/ci.yml` | Automated software checks |

## Development checks

```powershell
$env:AEROCLIM_TEST_ML="1"
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
node --test tests/test_demo.cjs
```

With GCC:

```sh
g++ -std=c++11 -Wall -Wextra -Werror -pedantic tests/test_firmware.cpp -o aeroclim-core-test
./aeroclim-core-test
```

CI runs Python 3.11/3.12, the portable firmware tests, and Node 22 calculation tests. This is separate from compiling the full ESP32 sketch; use `bash scripts/compile_firmware.sh` with Arduino CLI for that. See [repository validation](docs/REPOSITORY_VALIDATION.md) and the [original v3 validation record](docs/VALIDATION.md).

Local credentials, databases, trained model files, and build outputs are excluded from Git. The browser stores the selected region/weather in local storage, and exported runs contain that location. No runtime telemetry or credentials are included in this repository.

Original file provenance and packaging changes are recorded in [docs/PROVENANCE.md](docs/PROVENANCE.md). No open-source license has been applied to this combined repository.
