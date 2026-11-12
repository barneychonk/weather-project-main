"""Build a static GitHub Pages site with the latest collected weather snapshot."""
import argparse
import json
import shutil
from pathlib import Path

from dashboard_server import DASHBOARD_DIR, DEFAULT_DB, load_weather


def build(output_dir, db_path):
    output_dir.mkdir(parents=True, exist_ok=True)

    shutil.copytree(
        DASHBOARD_DIR / "Dashboard",
        output_dir / "Dashboard",
        dirs_exist_ok=True,
    )
    shutil.copytree(DASHBOARD_DIR / "ASSET", output_dir / "ASSET", dirs_exist_ok=True)

    data = load_weather(db_path)
    if not data["observation"] and not data["forecasts"]:
        raise RuntimeError("No weather observations or forecasts are available to publish.")

    (output_dir / "Dashboard" / "weather-data.json").write_text(
        json.dumps(data, ensure_ascii=False, allow_nan=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "index.html").write_text(
        '<!doctype html>\n'
        '<html lang="en">\n'
        '<meta charset="utf-8">\n'
        '<meta http-equiv="refresh" content="0; url=Dashboard/SIWeatherDashboard.html">\n'
        '<title>Seri Iskandar Weather Dashboard</title>\n'
        '<body><a href="Dashboard/SIWeatherDashboard.html">Open the weather dashboard</a></body>\n'
        '</html>\n',
        encoding="utf-8",
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--output-dir", type=Path, default=Path("_site"))
    args = parser.parse_args()
    build(args.output_dir, args.db)
    print(f"Built GitHub Pages site in {args.output_dir}")


if __name__ == "__main__":
    main()
