"""Serve the weather dashboard and expose data collected in weather.db."""
import argparse
import json
import sqlite3
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
DEFAULT_DB = HERE / "weather.db"
DASHBOARD_DIR = HERE / "DASHBOARD"
RESULTS_FILE = HERE / "docs" / "results.json"


def load_weather(db_path):
    if not db_path.is_file():
        raise FileNotFoundError(f"Weather database not found: {db_path}")

    with sqlite3.connect(db_path) as con:
        con.row_factory = sqlite3.Row
        observation_columns = {
            row["name"] for row in con.execute("PRAGMA table_info(observations)")
        }
        forecast_columns = {
            row["name"] for row in con.execute("PRAGMA table_info(forecasts)")
        }
        observation_cloud_cover = (
            "cloud_cover" if "cloud_cover" in observation_columns else "NULL AS cloud_cover"
        )
        forecast_cloud_cover = (
            "cloud_cover" if "cloud_cover" in forecast_columns else "NULL AS cloud_cover"
        )
        forecast_weather_code = (
            "weather_code" if "weather_code" in forecast_columns else "NULL AS weather_code"
        )
        observation = con.execute(
            f"""SELECT obs_time AS time, temperature, humidity, rainfall, wind_speed,
                       {observation_cloud_cover}
                FROM observations ORDER BY obs_time DESC LIMIT 1"""
        ).fetchone()
        latest_issue = con.execute(
            "SELECT MAX(issued_at) FROM forecasts"
        ).fetchone()[0]
        forecasts = []
        if latest_issue is not None:
            forecasts = [
                dict(row)
                for row in con.execute(
                    f"""SELECT target_time AS time, lead_hours AS lead, temperature,
                               humidity, rainfall, wind_speed, rain_prob,
                               {forecast_cloud_cover}, {forecast_weather_code}
                        FROM forecasts WHERE issued_at = ?
                        ORDER BY target_time""",
                    (latest_issue,),
                )
            ]

    analysis = None
    if RESULTS_FILE.is_file():
        with RESULTS_FILE.open(encoding="utf-8") as results_file:
            results = json.load(results_file)
        analysis = {
            "generated_at": results.get("generated_at"),
            "matched_pairs": results.get("matched_pairs", 0),
            "overall": results.get("overall", {}),
        }

    return {
        "location": "Seri Iskandar, Perak",
        "updated_at": latest_issue or (observation["time"] if observation else None),
        "observation": dict(observation) if observation else None,
        "forecasts": forecasts,
        "analysis": analysis,
    }


class DashboardHandler(SimpleHTTPRequestHandler):
    db_path = DEFAULT_DB

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DASHBOARD_DIR), **kwargs)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            self.path = "/Dashboard/SIWeatherDashboard.html"
            return super().do_GET()
        if path not in ("/api/weather", "/Dashboard/weather-data.json"):
            return super().do_GET()

        try:
            payload = json.dumps(load_weather(self.db_path), allow_nan=False).encode("utf-8")
        except (FileNotFoundError, sqlite3.Error, json.JSONDecodeError, OSError, TypeError, ValueError) as error:
            self.log_error("Unable to load dashboard data: %s", error)
            payload = json.dumps({"error": "Unable to load weather data"}).encode("utf-8")
            self.send_response(500)
        else:
            self.send_response(200)

        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1", help="interface to listen on")
    parser.add_argument("--port", type=int, default=8000, help="HTTP port")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="weather SQLite database")
    args = parser.parse_args()

    DashboardHandler.db_path = args.db
    server = ThreadingHTTPServer((args.host, args.port), DashboardHandler)
    print(f"Dashboard: http://{args.host}:{args.port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping dashboard server.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
