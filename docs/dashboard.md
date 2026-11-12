# Weather dashboard

The dashboard reads the latest observation and forecast from `weather.db` and
displays forecast verification values from `docs/results.json`.
Its animated background uses the latest collected cloud cover and rain data:
clear skies use `CLEAR.gif`, cloud cover of 50% or more uses `CLOUDY.gif`, and
rain uses `RAIN.gif`. The collector adds the cloud-cover columns to existing
databases automatically; run it once to collect the new values.

Install the analysis dependencies once from the project directory:

```powershell
python -m pip install -r requirements.txt
```

If using the project `.venv`, activate it first with
`.venv\Scripts\Activate.ps1`. Install packages with the same Python
interpreter you use to run `analyze.py`.

1. Run `python collector.py --loop` in one terminal to keep collecting weather
   data. To fetch once instead, run `python collector.py`.
2. Run `python analyze.py` after data has been collected to refresh the
   verification results.
3. Run `python dashboard_server.py` from the project directory.
4. Open `http://127.0.0.1:8000/` in a browser. Use **Refresh** to reload the
   latest database values.

The server uses Python's standard library and serves the dashboard locally.
