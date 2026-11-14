import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import store


class StoreTests(unittest.TestCase):
    def test_atomic_save_week_entry_and_failed_refresh(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(store, "DB_PATH", Path(directory) / "test.sqlite3"):
            first = {"season": 2024, "gameDetailsVersion": 4, "weeks": {"1": {}}}
            with store.connect() as db:
                store.save_season(db, first, "first")
                db.execute("UPDATE sync_status SET latest_season=2024,last_success='first' WHERE id=1")
            with store.connect() as db:
                store.save_season(db, {"season": 2024, "gameDetailsVersion": 4, "weeks": {"1": {}, "2": {}}}, "second")
            self.assertEqual(store.status()["latestWeekEnteredAt"], "second")
            with store.connect() as db:
                self.assertEqual(db.execute("SELECT entered_at FROM entered_weeks WHERE week=1").fetchone()[0], "first")
            with patch.object(store.nfl, "load_schedules", side_effect=RuntimeError("offline")):
                with self.assertRaisesRegex(RuntimeError, "offline"):
                    store.refresh()
            self.assertEqual(store.status()["lastSuccessfulRefresh"], "first")
            self.assertEqual(store.status()["refreshError"], "offline")
            self.assertEqual(list(store.season_data(2024)["weeks"]), ["1", "2"])

    def test_failed_transaction_does_not_publish_partial_data(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(store, "DB_PATH", Path(directory) / "test.sqlite3"):
            with self.assertRaises(RuntimeError):
                with store.connect() as db:
                    store.save_season(db, {"season": 2024, "weeks": {"1": {}}}, "first")
                    raise RuntimeError("rollback")
            with store.connect() as db:
                self.assertEqual(db.execute("SELECT count(*) FROM seasons").fetchone()[0], 0)
                self.assertEqual(db.execute("SELECT count(*) FROM entered_weeks").fetchone()[0], 0)

    def test_existing_snapshot_migrates_without_changing_entry_dates(self):
        legacy = {"season": 2024, "gameDetailsVersion": 2, "weeks": {"1": {
            "offense": [{"id": "A", "epa": 0.2}, {"id": "B", "epa": 0.1}],
            "defense": [{"id": "A", "epa": -0.1}, {"id": "B", "epa": 0.05}],
        }}}
        games = [{"season": 2024, "week": 1, "game_type": "REG", "home_team": "A",
                  "away_team": "B", "home_score": 21, "away_score": 14}]
        class Schedule:
            def to_dicts(self):
                return games
        with tempfile.TemporaryDirectory() as directory, patch.object(store, "DB_PATH", Path(directory) / "test.sqlite3"):
            with store.connect() as db:
                store.save_season(db, legacy, "original")
            with patch.object(store.nfl, "load_schedules", return_value=Schedule()) as load:
                updated = store.season_data(2024)
                self.assertEqual(updated["gameDetailsVersion"], 4)
                self.assertEqual(updated["weeks"]["1"]["offense"][0]["games"]["current"]["opponent"], "B")
                self.assertEqual(updated["weeks"]["1"]["offense"][0]["points"], {"for": 21, "allowed": 14, "net": 7})
                self.assertAlmostEqual(updated["weeks"]["1"]["offense"][0]["strengthOfSchedule"], 0.05)
                self.assertEqual(updated["weeks"]["1"]["offense"][0]["strengthOfScheduleRank"], 2)
                store.season_data(2024)
                load.assert_called_once_with(2024)
            with store.connect() as db:
                self.assertEqual(db.execute("SELECT entered_at FROM entered_weeks").fetchone()[0], "original")

    def test_version_three_snapshot_migrates_sos_ranks(self):
        legacy = {"season": 2024, "gameDetailsVersion": 3, "weeks": {"1": {
            "offense": [{"id": "A", "epa": 0.2}, {"id": "B", "epa": 0.1}],
            "defense": [{"id": "A", "epa": -0.1}, {"id": "B", "epa": 0.05}],
        }}}
        class Schedule:
            def to_dicts(self):
                return [{"season": 2024, "week": 1, "game_type": "REG", "home_team": "A",
                         "away_team": "B", "home_score": 21, "away_score": 14}]
        with tempfile.TemporaryDirectory() as directory, patch.object(store, "DB_PATH", Path(directory) / "test.sqlite3"):
            with store.connect() as db:
                store.save_season(db, legacy, "original")
            with patch.object(store.nfl, "load_schedules", return_value=Schedule()) as load:
                result = store.season_data(2024)
                self.assertEqual([row["strengthOfScheduleRank"] for row in result["weeks"]["1"]["offense"]], [2, 1])
                self.assertEqual(store.season_data(2024), result)
                load.assert_called_once_with(2024)
            with store.connect() as db:
                self.assertEqual(db.execute("SELECT entered_at FROM entered_weeks").fetchone()[0], "original")

    def test_failed_migration_keeps_original_snapshot(self):
        legacy = {"season": 2024, "gameDetailsVersion": 2, "weeks": {"1": {"offense": [{"id": "A"}]}}}
        with tempfile.TemporaryDirectory() as directory, patch.object(store, "DB_PATH", Path(directory) / "test.sqlite3"):
            with store.connect() as db:
                store.save_season(db, legacy, "original")
            with patch.object(store.nfl, "load_schedules", side_effect=RuntimeError("offline")):
                with self.assertRaisesRegex(RuntimeError, "offline"):
                    store.season_data(2024)
            with store.connect() as db:
                self.assertEqual(db.execute("SELECT entered_at FROM entered_weeks").fetchone()[0], "original")
                self.assertIn('"gameDetailsVersion": 2', db.execute("SELECT payload FROM seasons").fetchone()[0])

    def test_invalid_schedule_during_migration_preserves_snapshot_and_timestamp(self):
        legacy = {"season": 2024, "gameDetailsVersion": 2, "weeks": {"1": {
            "offense": [{"id": "A", "epa": 0.2}], "defense": [{"id": "A", "epa": 0.1}]
        }}}
        class Schedule:
            def to_dicts(self):
                return [{"season": 2024, "week": 1, "game_type": "REG", "home_score": None, "away_score": None}]
        with tempfile.TemporaryDirectory() as directory, patch.object(store, "DB_PATH", Path(directory) / "test.sqlite3"):
            with store.connect() as db:
                store.save_season(db, legacy, "original")
                original = db.execute("SELECT payload, updated_at FROM seasons").fetchone()
            with patch.object(store.nfl, "load_schedules", return_value=Schedule()):
                with self.assertRaisesRegex(ValueError, "Missing score"):
                    store.season_data(2024)
            with store.connect() as db:
                self.assertEqual(db.execute("SELECT payload, updated_at FROM seasons").fetchone(), original)
                self.assertEqual(db.execute("SELECT entered_at FROM entered_weeks").fetchone()[0], "original")
