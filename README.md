# Seri Iskandar Weather Dashboard

A Python and SQLite project that collects weather data for Seri Iskandar,
Perak, evaluates forecast accuracy, and displays current observations alongside
a seven-day forecast.

## Data and status

The collector retrieves hourly observations and forecasts from Open-Meteo and
stores them in `weather.db`. The dashboard uses the latest stored observation
for its current status; forecast data is displayed separately and does not
determine that status. **RAINY** means precipitation was recorded in the
preceding hour. This project has no local weather sensor, so collected values
are not ground-truth sensor readings.

The GitHub Actions workflow collects data, updates forecast analysis, and
deploys the static dashboard hourly. The browser refreshes the published
snapshot every five minutes; this is not a continuous real-time feed.

## Requirements

- Python 3
- Packages listed in `requirements.txt` (`numpy` and `pandas`)
- Internet access to retrieve Open-Meteo data

Install dependencies from the repository root:

```powershell
python -m pip install -r requirements.txt
```

## Run locally

Collect data once, refresh analysis, and start the dashboard server:

```powershell
python collector.py
python analyze.py
python dashboard_server.py
```

Open <http://127.0.0.1:8000/>. To keep collecting hourly, run
`python collector.py --loop` in a separate terminal. On Windows,
`run-weather-project.bat` starts the collector and dashboard for you.

## Validate and build

Run the data-quality and forecast-accuracy checks:

```powershell
python validate.py
```

Build the static site locally:

```powershell
python build_pages.py --output-dir _site
```

See [`docs/dashboard.md`](docs/dashboard.md) for dashboard behavior, GitHub
Pages deployment, and additional operating details.

## Repository layout

- `collector.py`, `schema.sql`, `weather.db` — data collection and storage
- `analyze.py`, `validate.py`, `docs/results.json` — forecast analysis and
  validation
- `dashboard_server.py`, `build_pages.py` — local server and static-site build
- `DASHBOARD/` — dashboard source and assets
- `.github/workflows/collect-weather.yml` — scheduled collection and Pages
  deployment
