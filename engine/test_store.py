import tempfile
import copy
import unittest
from pathlib import Path
from unittest.mock import patch

import store


class StoreTests(unittest.TestCase):
    def test_playoff_progress_is_isolated_and_cleaned_up(self):
        data = {"season": 2024, "weeks": {"1": {"value": 1}}}
        class Schedule:
            def to_dicts(self):
                return []
        def build(*args, **kwargs):
            self.assertEqual(store.playoff_progress("job-a"), {"completed": 0, "total": 100_000})
            self.assertIsNone(store.playoff_progress("job-b"))
            kwargs["progress"](1000, 100_000)
            self.assertEqual(store.playoff_progress("job-a"), {"completed": 1000, "total": 100_000})
            return {"value": 1}
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(store, "DB_PATH", Path(directory) / "test.sqlite3"), \
                patch.object(store, "season_data", return_value=data), \
                patch.object(store.nfl, "load_schedules", return_value=Schedule()), \
                patch("playoffs.build_playoff_picture", side_effect=build):
            self.assertEqual(store.playoff_data(2024, 1, "job-a"), {"value": 1})
            self.assertIsNone(store.playoff_progress("job-a"))

    def test_failed_playoff_job_cleans_progress(self):
        data = {"season": 2024, "weeks": {"1": {"value": 1}}}
        class Schedule:
            def to_dicts(self):
                return []
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(store, "DB_PATH", Path(directory) / "test.sqlite3"), \
                patch.object(store, "season_data", return_value=data), \
                patch.object(store.nfl, "load_schedules", return_value=Schedule()), \
                patch("playoffs.build_playoff_picture", side_effect=ValueError("failed")):
            with self.assertRaisesRegex(ValueError, "failed"):
                store.playoff_data(2024, 1, "job-a")
            self.assertIsNone(store.playoff_progress("job-a"))

    def test_playoff_cache_reuses_results_and_invalidates_inputs(self):
        data = {"season": 2024, "weeks": {"1": {"combined": [{"id": "A", "epa": 0.1}]}}}
        games = [
            {"season": 2024, "game_type": "REG", "week": 1, "home_team": "A", "away_team": "B", "home_score": 21, "away_score": 14},
            {"season": 2024, "game_type": "REG", "week": 2, "home_team": "A", "away_team": "B", "home_score": None, "away_score": None},
        ]
        class Schedule:
            def to_dicts(self):
                return games
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(store, "DB_PATH", Path(directory) / "test.sqlite3"), \
                patch.object(store, "season_data", return_value=data), \
                patch.object(store.nfl, "load_schedules", return_value=Schedule()), \
                patch("playoffs.build_playoff_picture", return_value={"simulations": 100_000}) as build:
            self.assertEqual(store.playoff_data(2024, 1), {"simulations": 100_000})
            self.assertEqual(store.playoff_data(2024, 1), {"simulations": 100_000})
            self.assertEqual(build.call_count, 1)
            self.assertEqual(build.call_args.kwargs["simulations"], 100_000)
            games[1]["home_score"] = 10
            games[1]["away_score"] = 0
            store.playoff_data(2024, 1)
            self.assertEqual(build.call_count, 1)
            data["weeks"]["1"]["combined"][0]["epa"] = 0.2
            store.playoff_data(2024, 1)
            self.assertEqual(build.call_count, 2)
            games[1]["away_team"] = "C"
            store.playoff_data(2024, 1)
            self.assertEqual(build.call_count, 3)
            with patch.object(store, "PLAYOFF_MODEL_VERSION", "new-version"):
                store.playoff_data(2024, 1)
            self.assertEqual(build.call_count, 4)
            with patch.object(store, "PLAYOFF_SIMULATIONS", 5):
                store.playoff_data(2024, 1)
            self.assertEqual(build.call_count, 5)

    def test_failed_playoff_calculation_does_not_replace_cache(self):
        data = {"season": 2024, "weeks": {"1": {"value": 1}}}
        class Schedule:
            def to_dicts(self):
                return []
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(store, "DB_PATH", Path(directory) / "test.sqlite3"), \
                patch.object(store, "season_data", return_value=data), \
                patch.object(store.nfl, "load_schedules", return_value=Schedule()), \
                patch("playoffs.build_playoff_picture", return_value={"value": 1}) as build:
            store.playoff_data(2024, 1)
            data["weeks"]["1"]["value"] = 2
            build.side_effect = ValueError("calculation failed")
            with self.assertRaisesRegex(ValueError, "calculation failed"):
                store.playoff_data(2024, 1)
            with store.connect() as db:
                self.assertEqual(db.execute("SELECT payload FROM playoff_cache").fetchone()[0], '{"value": 1}')

    def test_playoff_retries_when_snapshot_changes_during_calculation(self):
        original = {"season": 2024, "weeks": {"1": {"value": 1}}}
        updated = copy.deepcopy(original)
        updated["weeks"]["1"]["value"] = 2
        class Schedule:
            def to_dicts(self):
                return []
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(store, "DB_PATH", Path(directory) / "test.sqlite3"), \
                patch.object(store, "season_data", side_effect=[original, updated, updated, updated]), \
                patch.object(store.nfl, "load_schedules", return_value=Schedule()), \
                patch("playoffs.build_playoff_picture", side_effect=[{"value": 1}, {"value": 2}]) as build:
            self.assertEqual(store.playoff_data(2024, 1), {"value": 2})
            self.assertEqual(build.call_count, 2)

    def test_atomic_save_week_entry_and_failed_refresh(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(store, "DB_PATH", Path(directory) / "test.sqlite3"):
            first = {"season": 2024, "gameDetailsVersion": 4, "combinedEpaVersion": 1, "weeks": {"1": {}}}
            with store.connect() as db:
                store.save_season(db, first, "first")
                db.execute("UPDATE sync_status SET latest_season=2024,last_success='first' WHERE id=1")
            with store.connect() as db:
                store.save_season(db, {"season": 2024, "gameDetailsVersion": 4, "combinedEpaVersion": 1, "weeks": {"1": {}, "2": {}}}, "second")
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
        legacy = {"season": 2024, "gameDetailsVersion": 2, "combinedEpaVersion": 1, "weeks": {"1": {
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
        legacy = {"season": 2024, "gameDetailsVersion": 3, "combinedEpaVersion": 1, "weeks": {"1": {
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
        legacy = {"season": 2024, "gameDetailsVersion": 2, "combinedEpaVersion": 1, "weeks": {"1": {"offense": [{"id": "A"}]}}}
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
        legacy = {"season": 2024, "gameDetailsVersion": 2, "combinedEpaVersion": 1, "weeks": {"1": {
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

    def test_old_combined_calculation_rebuilds_once_and_preserves_entry_dates(self):
        legacy = {"season": 2024, "gameDetailsVersion": 4, "weeks": {"1": {}}}
        rebuilt = {"season": 2024, "gameDetailsVersion": 4, "combinedEpaVersion": 1, "weeks": {"1": {}, "2": {}}}
        with tempfile.TemporaryDirectory() as directory, patch.object(store, "DB_PATH", Path(directory) / "test.sqlite3"):
            with store.connect() as db:
                store.save_season(db, legacy, "original")
            with patch.object(store, "load_season", return_value=rebuilt) as load:
                self.assertEqual(store.season_data(2024), rebuilt)
                self.assertEqual(store.season_data(2024), rebuilt)
                load.assert_called_once_with(2024)
            with store.connect() as db:
                self.assertEqual(db.execute("SELECT entered_at FROM entered_weeks WHERE week=1").fetchone()[0], "original")
                self.assertEqual(db.execute("SELECT count(*) FROM entered_weeks").fetchone()[0], 2)

    def test_failed_combined_rebuild_keeps_previous_snapshot(self):
        legacy = {"season": 2024, "gameDetailsVersion": 4, "weeks": {"1": {}}}
        with tempfile.TemporaryDirectory() as directory, patch.object(store, "DB_PATH", Path(directory) / "test.sqlite3"):
            with store.connect() as db:
                store.save_season(db, legacy, "original")
                original = db.execute("SELECT payload, updated_at FROM seasons").fetchone()
            with patch.object(store, "load_season", side_effect=RuntimeError("offline")):
                with self.assertRaisesRegex(RuntimeError, "offline"):
                    store.season_data(2024)
            with store.connect() as db:
                self.assertEqual(db.execute("SELECT payload, updated_at FROM seasons").fetchone(), original)
                self.assertEqual(db.execute("SELECT entered_at FROM entered_weeks").fetchone()[0], "original")
