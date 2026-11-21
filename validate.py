"""
validate.py - sanity-checks weather.db and the forecast-vs-observation join.
Put it next to weather.db / analyze.py and run:  python validate.py
(or: python validate.py --db path/to/weather.db)

Column names are taken from analyze.py:
  observations: obs_time, temperature, humidity, rainfall, wind_speed
  forecasts:    issued_at, target_time, lead_hours, temperature, humidity,
                rainfall, wind_speed, rain_prob
"""
import argparse
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

VARS = ["temperature", "humidity", "rainfall", "wind_speed"]
RANGES = {"temperature": (18, 40), "humidity": (0, 100),
          "rainfall": (0, 100), "wind_speed": (0, 80)}   # plausible for Perak

results = []


def check(name, status, detail=""):
    results.append((status, name, detail))
    icon = {"PASS": "[ OK ]", "WARN": "[WARN]", "FAIL": "[FAIL]"}[status]
    print(f"{icon} {name}" + (f"  ->  {detail}" if detail else ""))


def self_test():
    """Hand-computed case: forecast [20,22] vs observed [21,20]."""
    fc, ob = np.array([20, 22]), np.array([21, 20])
    e = fc - ob
    assert abs(np.abs(e).mean() - 1.5) < 1e-9          # MAE
    assert abs(e.mean() - 0.5) < 1e-9                   # bias
    assert abs(np.sqrt((e ** 2).mean()) - np.sqrt(2.5)) < 1e-9   # RMSE
    check("metric formulas match hand calculation", "PASS")


def main(db):
    self_test()
    con = sqlite3.connect(db)
    obs = pd.read_sql("SELECT * FROM observations", con, parse_dates=["obs_time"])
    fc = pd.read_sql("SELECT * FROM forecasts", con,
                     parse_dates=["issued_at", "target_time"])
    con.close()
    print(f"\n{len(obs)} observations, {len(fc)} forecast rows\n")

    # ---------- 1. DATA QUALITY ----------
    # coverage
    span_h = (obs.obs_time.max() - obs.obs_time.min()).total_seconds() / 3600
    check("observation span >= 72h (3 days)", "PASS" if span_h >= 72 else "FAIL",
          f"{span_h:.1f} h from {obs.obs_time.min()} to {obs.obs_time.max()}")

    # duplicates
    d_obs = obs.duplicated("obs_time").sum()
    check("no duplicate obs_time", "PASS" if d_obs == 0 else "FAIL",
          f"{d_obs} duplicates (these inflate n in the merge)")
    d_fc = fc.duplicated(["issued_at", "target_time"]).sum()
    check("no duplicate (issued_at, target_time)", "PASS" if d_fc == 0 else "FAIL",
          f"{d_fc} duplicates")

    # gaps in hourly observations
    t = obs.obs_time.drop_duplicates().sort_values()
    gaps = t.diff().dropna()
    big = gaps[gaps > pd.Timedelta(minutes=90)]
    check("no gaps > 90 min in observations", "PASS" if big.empty else "WARN",
          f"{len(big)} gaps, largest {gaps.max()}" if len(gaps) else "")

    # nulls
    for v in VARS:
        pct = obs[v].isna().mean() * 100
        check(f"observations.{v} nulls < 5%", "PASS" if pct < 5 else "WARN", f"{pct:.1f}% null")

    # ranges
    for v, (lo, hi) in RANGES.items():
        for name, df in (("obs", obs), ("fc", fc)):
            bad = ((df[v] < lo) | (df[v] > hi)).sum()
            check(f"{name}.{v} within [{lo},{hi}]", "PASS" if bad == 0 else "FAIL",
                  f"{bad} out-of-range rows")
    if "rain_prob" in fc:
        bad = ((fc.rain_prob < 0) | (fc.rain_prob > 100)).sum()
        check("fc.rain_prob within [0,100]", "PASS" if bad == 0 else "FAIL", f"{bad} bad rows")

    # stuck values (sensor/API frozen)
    for v in VARS:
        if v != "rainfall" and obs[v].nunique() <= 2:
            check(f"obs.{v} not constant", "FAIL", f"only {obs[v].nunique()} distinct values")

    # diurnal sanity: tropical afternoon temperature peak (local time ~13-16h)
    o = obs.dropna(subset=["temperature"]).copy()
    if len(o) > 24:
        peak_hour = o.groupby(o.obs_time.dt.hour).temperature.mean().idxmax()
        ok = 11 <= peak_hour <= 17
        check("temperature peaks 11:00-17:00 (timezone sanity)", "PASS" if ok else "FAIL",
              f"peak at hour {peak_hour}; if ~5-9 your timestamps are probably UTC, not UTC+8")

    # ---------- 2. FORECAST TABLE INTEGRITY ----------
    lead_calc = (fc.target_time - fc.issued_at).dt.total_seconds() / 3600
    mism = (lead_calc.round() - fc.lead_hours).abs() > 1
    check("lead_hours == target_time - issued_at", "PASS" if mism.sum() == 0 else "FAIL",
          f"{mism.sum()} rows disagree")
    check("no forecast issued after its target (leakage)",
          "PASS" if (fc.lead_hours >= 0).all() else "FAIL",
          f"{(fc.lead_hours < 0).sum()} rows with negative lead")
    n_runs = fc.issued_at.nunique()
    check("multiple forecast runs stored (not overwritten)", "PASS" if n_runs >= 24 else "WARN",
          f"{n_runs} distinct issued_at values; need many runs to evaluate by lead time")

    # ---------- 3. JOIN QUALITY ----------
    df = fc.merge(obs, left_on="target_time", right_on="obs_time", suffixes=("_fc", "_obs"))
    past = fc[fc.target_time <= obs.obs_time.max()]
    rate = len(df) / max(len(past), 1) * 100
    check("forecasts whose target hour has an observation", "PASS" if rate > 90 else "WARN",
          f"{len(df)} matched of {len(past)} eligible ({rate:.0f}%); low = minute offsets, e.g. 14:07 vs 14:00")
    off = (fc.target_time.dt.minute != 0).mean() * 100
    check("target_time on the hour", "PASS" if off < 1 else "WARN", f"{off:.0f}% not on the hour")
    off2 = (fc.issued_at.dt.minute != 0).mean() * 100
    check("issued_at on the hour (needed by analyze.py persistence baseline)",
          "PASS" if off2 < 1 else "WARN",
          f"{off2:.0f}% not on the hour" + (" -> persistence baseline in analyze.py may be empty" if off2 >= 1 else ""))
    if df.empty:
        print("\nNo matched pairs; accuracy checks skipped.")
        return summary()

    # ---------- 4. ACCURACY ----------
    base = obs.drop_duplicates("obs_time").set_index("obs_time")
    print("\nAccuracy by variable (all leads):")
    for v in VARS:
        ok = df[f"{v}_fc"].notna() & df[f"{v}_obs"].notna()
        e = (df.loc[ok, f"{v}_fc"] - df.loc[ok, f"{v}_obs"])
        if e.empty:
            continue
        mae, bias = e.abs().mean(), e.mean()
        pers = df.loc[ok, "issued_at"].map(base[v])
        pe = (pers - df.loc[ok, f"{v}_obs"]).abs()
        skill = 1 - mae / pe.mean() if pe.notna().any() and pe.mean() > 0 else np.nan
        print(f"   {v:12s} n={len(e):5d}  MAE={mae:6.2f}  RMSE={np.sqrt((e**2).mean()):6.2f}  "
              f"bias={bias:+6.2f}  skill vs persistence={skill:+.2f}")
        if v == "temperature":
            check("temperature MAE < 2.5 degC", "PASS" if mae < 2.5 else "WARN", f"{mae:.2f}")
            check("temperature |bias| < 1.5 degC", "PASS" if abs(bias) < 1.5 else "WARN", f"{bias:+.2f}")
        if v == "humidity":
            check("humidity MAE < 12 %", "PASS" if mae < 12 else "WARN", f"{mae:.2f}")
        if not np.isnan(skill):
            check(f"{v}: beats persistence (skill > 0)", "PASS" if skill > 0 else "WARN", f"{skill:+.2f}")

    # error should grow (or at least not shrink) with lead time
    t = df.dropna(subset=["temperature_fc", "temperature_obs"]).copy()
    t["ae"] = (t.temperature_fc - t.temperature_obs).abs()
    short, long_ = t[t.lead_hours <= 6].ae.mean(), t[t.lead_hours >= 24].ae.mean()
    if not (np.isnan(short) or np.isnan(long_)):
        check("temp error at 24h+ lead >= error at <=6h lead", "PASS" if long_ >= short else "WARN",
              f"{short:.2f} (<=6h) vs {long_:.2f} (>=24h); if reversed, check the lead/target logic")

    # rain
    r = df.dropna(subset=["rain_prob", "rainfall_obs"])
    if len(r):
        o = r.rainfall_obs >= 0.1
        p = r.rain_prob >= 50
        hit, miss, fa = (o & p).sum(), (o & ~p).sum(), (~o & p).sum()
        csi = hit / (hit + miss + fa) if (hit + miss + fa) else np.nan
        base_rate = o.mean() * 100
        print(f"\nRain: observed rain in {base_rate:.1f}% of hours, hits={hit}, misses={miss}, "
              f"false alarms={fa}, CSI={csi:.2f}")
        check("rain sample has at least 10 rainy hours", "PASS" if o.sum() >= 10 else "WARN",
              f"{o.sum()} rainy hours; too few means rain scores are unreliable")
        check("rain is not accuracy-only (base rate < 50%)", "PASS" if base_rate < 50 else "WARN",
              "if base rate is low, quote CSI/POD/Brier, not accuracy")
    summary()


def summary():
    n = {s: sum(1 for r in results if r[0] == s) for s in ("PASS", "WARN", "FAIL")}
    print(f"\nSUMMARY: {n['PASS']} passed, {n['WARN']} warnings, {n['FAIL']} failed")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(Path(__file__).with_name("weather.db")))
    main(ap.parse_args().db)
