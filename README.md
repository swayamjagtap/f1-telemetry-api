# F1 Telemetry API

Backend service for the F1 Telemetry Dashboard.

## Architecture

The project is designed around a dataset-driven architecture:

- FastAPI — API and WebSocket backend
- FastF1 — Formula 1 data acquisition
- GitHub — source control
- Render — backend hosting
- GitHub Pages — frontend hosting

## Dataset Structure

```text
data/
└── YYYY/
    └── event_name/
        ├── qualifying/
        ├── race/
        ├── practice_1/
        ├── practice_2/
        ├── practice_3/
        ├── sprint/
        └── sprint_qualifying/