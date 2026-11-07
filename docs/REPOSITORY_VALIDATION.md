# Repository validation — 7 November 2026

Checks performed while preparing this repository:

| Check | Result |
| --- | --- |
| Python 3.12 regression and model fit/save/load/inference suite | 16 tests passed with `AEROCLIM_TEST_ML=1` |
| Python source compilation | Passed for `pc/` and `tests/` |
| Browser JavaScript calculations | 7 Node tests passed |
| Portable firmware core | MSVC C++14 build and executable passed on Windows |
| Browser UI smoke check | Dashboard loaded, retraining fitted 39 coefficients, regional/learned mode switching updated the planner |
| Browser console during smoke check | No error entries observed |

The Python suite initially exposed an open SQLite connection in forecast evaluation on Windows. `pc/evaluate.py` now closes the read-only connection explicitly; the full suite passed after the fix.

The browser smoke check used the manual baseline. Retraining preserved deterministic predictions. Switching the forecast mode changed the displayed planner input and initial cooling level (100% learned versus 50% regional in the default scenario). The source dashboard was preserved unchanged.

GitHub Actions is configured for Python 3.11 and 3.12 on Ubuntu, Python 3.12 on Windows, GCC C++11 portable-core tests, and Node 22 browser calculation tests. Consult the repository Actions tab for the current remote run status.

## Scope

These are software checks. The full ESP32 toolchain build was not repeated during repository preparation, and no board was flashed or electrically tested. The original package's separate build history remains in [VALIDATION.md](VALIDATION.md).

Live weather requests, optional XGBoost, USB/MQTT hardware transport, real-world forecasting accuracy, and physical HVAC control were not verified in this repository-preparation session. Browser tests use generated data and modeled cooling; they do not establish real energy savings. Hardware revision relationships are recorded in [hardware/README.md](../hardware/README.md).
