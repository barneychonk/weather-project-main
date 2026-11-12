# Weather dashboard

The dashboard reads the latest observation and forecast from `weather.db` and
displays forecast verification values from `docs/results.json`.
Its animated background uses the latest collected cloud cover and rain data:
clear skies use `CLEAR.gif`, cloud cover of 50% or more uses `CLOUDY.gif`, and
rain uses `RAIN.gif`. The collector adds the cloud-cover columns to existing
databases automatically; run it once to collect the new values.

## GitHub Pages

The hourly `collect-weather` workflow collects Open-Meteo data, refreshes the
forecast analysis, builds a static snapshot, and deploys the dashboard to
GitHub Pages. The browser re-fetches that snapshot every five minutes, while
new source data is collected and published hourly; this is periodic data, not a
continuous real-time feed. The site does not need a server or API secret.

The workflow deploys on pushes to `main`, on its hourly schedule, and when
manually started. GitHub Pages must allow GitHub Actions as its build and
deployment source in the repository's **Settings → Pages**.

To build the static site locally, run:

```powershell
python build_pages.py --output-dir _site
```

The generated site contains a root redirect, the original `Dashboard/` and
`ASSET/` directories, and a `Dashboard/weather-data.json` snapshot. `_site` is
a build output and should not be committed.

## Local server

Install the analysis dependencies once from the project directory:

```powershell
python -m pip install -r requirements.txt
```

If using the project `.venv`, activate it first with
`.venv\Scripts\Activate.ps1`. Install packages with the same Python
interpreter you use to run `analyze.py`.

1. Run `python collector.py --loop` in one terminal to keep collecting weather
   data hourly. To fetch once instead, run `python collector.py`.
2. Run `python analyze.py` after data has been collected to refresh the
   verification results.
3. Run `python dashboard_server.py` from the project directory.
4. Open `http://127.0.0.1:8000/` in a browser. Use **Refresh** to reload the
   latest database values.

The server uses Python's standard library and serves the dashboard locally.
