import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import nflreadpy as nfl
from nflreadpy.config import update_config

from engine import MIN_SEASON, add_game_details, build_season


DB_PATH = Path(os.environ.get("POWERINDEX_DB", Path(__file__).resolve().parent.parent / "data" / "rankings.sqlite3"))
_lock = threading.RLock()
update_config(cache_mode="off", verbose=False)


@contextmanager
def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=30)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("CREATE TABLE IF NOT EXISTS seasons (season INTEGER PRIMARY KEY, payload TEXT NOT NULL, updated_at TEXT NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS entered_weeks (season INTEGER NOT NULL, week INTEGER NOT NULL, entered_at TEXT NOT NULL, PRIMARY KEY (season, week))")
    db.execute("CREATE TABLE IF NOT EXISTS sync_status (id INTEGER PRIMARY KEY CHECK (id = 1), last_success TEXT, last_error TEXT, latest_season INTEGER)")
    db.execute("INSERT OR IGNORE INTO sync_status (id) VALUES (1)")
    db.commit()
    try:
        with db:
            yield db
    finally:
        db.close()


def now():
    return datetime.now(timezone.utc).isoformat()


def load_season(season, schedules=None, teams=None):
    schedules = schedules if schedules is not None else nfl.load_schedules(season).to_dicts()
    teams = teams if teams is not None else nfl.load_teams().to_dicts()
    plays = nfl.load_pbp(season).select(
        "game_id", "season_type", "week", "play_type", "epa", "posteam", "defteam",
        "qb_kneel", "qb_spike", "play_deleted",
    ).to_dicts()
    return build_season(season, teams, schedules, plays)


def save_season(db, result, timestamp):
    season = result["season"]
    db.execute("INSERT OR REPLACE INTO seasons VALUES (?, ?, ?)", (season, json.dumps(result, allow_nan=False), timestamp))
    for week in result["weeks"]:
        db.execute("INSERT OR IGNORE INTO entered_weeks VALUES (?, ?, ?)", (season, int(week), timestamp))


def refresh():
    with _lock:
        try:
            schedules = nfl.load_schedules(True).to_dicts()
            grouped = {}
            for row in schedules:
                if row["season"] >= MIN_SEASON and row["game_type"] == "REG":
                    grouped.setdefault((row["season"], row["week"]), []).append(row)
            available = sorted({
                season for (season, _), games in grouped.items()
                if all(game["home_score"] is not None and game["away_score"] is not None for game in games)
            }, reverse=True)
            if not available:
                raise ValueError("No seasons with completed games are available.")
            latest = available[0]
            result = load_season(latest, schedules, nfl.load_teams().to_dicts())
            timestamp = now()
            with connect() as db:
                save_season(db, result, timestamp)
                db.execute("UPDATE sync_status SET last_success=?, last_error=NULL, latest_season=? WHERE id=1", (timestamp, latest))
            return available
        except Exception as error:
            with connect() as db:
                db.execute("UPDATE sync_status SET last_error=? WHERE id=1", (str(error),))
            raise


def status():
    with connect() as db:
        row = db.execute("SELECT last_success, last_error, latest_season FROM sync_status WHERE id=1").fetchone()
        payload = db.execute("SELECT payload FROM seasons WHERE season=?", (row[2],)).fetchone()
        week = max(map(int, json.loads(payload[0])["weeks"])) if payload else None
        latest_week = db.execute(
            "SELECT week, entered_at FROM entered_weeks WHERE season=? AND week=?", (row[2], week)
        ).fetchone()
    return {
        "lastSuccessfulRefresh": row[0], "refreshError": row[1],
        "latestSeason": row[2], "latestWeek": latest_week[0] if latest_week else None,
        "latestWeekEnteredAt": latest_week[1] if latest_week else None,
    }


def seasons():
    state = status()
    if state["latestSeason"] is None:
        raise RuntimeError("Initial data refresh has not succeeded.")
    return {"seasons": list(range(state["latestSeason"], MIN_SEASON - 1, -1))}


def season_data(season):
    with connect() as db:
        row = db.execute("SELECT payload FROM seasons WHERE season=?", (season,)).fetchone()
    if row and json.loads(row[0]).get("gameDetailsVersion") == 4:
        return json.loads(row[0])
    with _lock:
        with connect() as db:
            row = db.execute("SELECT payload FROM seasons WHERE season=?", (season,)).fetchone()
        if row:
            result = json.loads(row[0])
            if result.get("gameDetailsVersion") == 4:
                return result
            result = add_game_details(result, nfl.load_schedules(season).to_dicts())
            with connect() as db:
                save_season(db, result, now())
            return result
        result = load_season(season)
        with connect() as db:
            save_season(db, result, now())
        return result
