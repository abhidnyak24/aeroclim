# File provenance

Repository assembled on 7 November 2026 from the project's existing local downloads.

| Source | Repository destination |
| --- | --- |
| `AeroClim_v3_Complete_Package.zip`, dated 3 November 2026 | Firmware, PC software, original tests, broker, scripts and v3 documentation |
| `aeroclim-ai.html`, dated 7 November 2026 | `demo/index.html`, copied unchanged |
| Existing EasyEDA and manufacturing exports | `hardware/`; original filenames retained |

Older browser dashboards, updater utilities and the combined source dump are superseded by the included files and are not needed to run the repository. Source downloads were left unchanged.

## Repository preparation changes

- Added a project README, architecture guide, hardware inventory and this provenance record.
- Adapted the original README into `docs/SETUP.md`.
- Renamed the original firmware configuration to `config.example.h`, unchanged; added a tracked `config.h` selector for an optional, ignored `config.local.h`.
- Added Git ignore rules for local credentials, observations, model binaries and generated files.
- Added browser calculation tests and GitHub Actions checks.
- Fixed `pc/evaluate.py` to close its read-only SQLite connection explicitly. The original context manager managed transactions without closing the connection, leaving database handles open on Windows.

The original package checksum manifest is retained at [provenance/AeroClim_v3_SHA256SUMS.txt](provenance/AeroClim_v3_SHA256SUMS.txt). Its paths and hashes describe the original archive, not this reorganized repository. The original [VALIDATION.md](VALIDATION.md) is a historical record supplied with that package; current checks are recorded separately in [REPOSITORY_VALIDATION.md](REPOSITORY_VALIDATION.md).

Hardware library contributor metadata remains in the source files. No new license grant is made for the combined repository or third-party components.
